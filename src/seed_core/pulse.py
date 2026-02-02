"""
Pulse - Health monitoring mechanism for realities.

The Pulse component provides health checking for all realities tracked in the
seed meta-model. It verifies model integrity, detects drift, and monitors
activity status.

Key Features:
- Reality health checks (green/yellow/red status)
- Hash-based drift detection
- Activity monitoring (idle/busy/error)
- Batch pulse operations across all realities
- Quick hash-only verification mode
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, Dict, List, Optional, Any

from .registry import Reality
from .verification import verify_model, HashCheck


logger = logging.getLogger(__name__)


@dataclass
class PulseResult:
    """Result of a pulse health check on a reality.

    Attributes:
        reality_id: Unique identifier for the reality
        status: Health status - green (healthy), yellow (warnings), red (errors)
        activity: Activity state - idle (no work), busy (active), error (problems)
        hash_verified: Whether hash verification passed
        last_checked: Timestamp of this pulse check
        details: Additional diagnostic information
    """
    reality_id: str
    status: Literal['green', 'yellow', 'red']
    activity: Literal['idle', 'busy', 'error']
    hash_verified: bool
    last_checked: datetime
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_healthy(self) -> bool:
        """Return True if status is green."""
        return self.status == 'green'

    @property
    def has_issues(self) -> bool:
        """Return True if status is yellow or red."""
        return self.status in ('yellow', 'red')

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'reality_id': self.reality_id,
            'status': self.status,
            'activity': self.activity,
            'hash_verified': self.hash_verified,
            'last_checked': self.last_checked.isoformat(),
            'details': self.details,
        }


class Pulse:
    """Health monitoring system for realities.

    Provides comprehensive health checking including:
    - Model file existence and readability
    - Hash verification for drift detection
    - Activity status assessment
    - Batch operations across multiple realities

    Attributes:
        model_path: Path to the seed meta-model (sketch.json)
    """

    def __init__(self, model_path: Path):
        """Initialize pulse checker.

        Args:
            model_path: Path to the seed model file

        Raises:
            FileNotFoundError: If model file doesn't exist
            json.JSONDecodeError: If model file is invalid JSON
        """
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Seed model not found: {self.model_path}")

        self._model_data: Optional[Dict[str, Any]] = None
        self._load_model()

    def _load_model(self) -> None:
        """Load the seed model from disk."""
        try:
            with open(self.model_path, 'r', encoding='utf-8') as f:
                self._model_data = json.load(f)
            logger.debug(f"Loaded seed model from {self.model_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse seed model: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load seed model: {e}")
            raise

    def get_realities(self) -> List[Reality]:
        """Extract all Reality nodes from the seed model.

        Returns:
            List of Reality objects found in the model
        """
        if not self._model_data:
            return []

        realities = []
        for node in self._model_data.get('nodes', []):
            if node.get('type') == 'Reality':
                source = node.get('source', {})
                model_info = node.get('model', {})

                reality = Reality(
                    id=node['id'],
                    label=node['label'],
                    description=node.get('description', ''),
                    path=source.get('path'),
                    model_path=source.get('model_path'),
                    status=node.get('status'),
                    model_summary=model_info.get('_summary')
                )
                realities.append(reality)

        logger.debug(f"Found {len(realities)} realities in model")
        return realities

    def check_reality(self, reality: Reality) -> PulseResult:
        """Perform comprehensive health check on a reality.

        Args:
            reality: Reality object to check

        Returns:
            PulseResult with health status and details
        """
        now = datetime.now()
        details: Dict[str, Any] = {
            'label': reality.label,
            'path': reality.path,
            'has_path': reality.path is not None,
            'has_model': reality.has_model,
        }

        # Start with optimistic defaults
        status: Literal['green', 'yellow', 'red'] = 'green'
        activity: Literal['idle', 'busy', 'error'] = 'idle'
        hash_verified = False

        try:
            # Check 1: Does reality have a path?
            if not reality.path:
                status = 'yellow'
                activity = 'idle'
                details['warnings'] = details.get('warnings', [])
                details['warnings'].append('No path specified')
                logger.warning(f"Reality {reality.id} has no path")

            # Check 2: Does reality have a model?
            if reality.model_path and not reality.has_model:
                status = 'red'
                activity = 'error'
                details['errors'] = details.get('errors', [])
                details['errors'].append(f'Model file not found: {reality.full_model_path}')
                logger.error(f"Reality {reality.id} model not found: {reality.full_model_path}")

            # Check 3: Can we read the model?
            if reality.has_model:
                try:
                    with open(reality.full_model_path, 'r', encoding='utf-8') as f:
                        model_data = json.load(f)
                    details['model_readable'] = True
                    details['model_schema_version'] = model_data.get('schema_version')

                    # Check for todos in the model (indicates work pending)
                    todos = [n for n in model_data.get('nodes', []) if n.get('type') == 'Todo']
                    pending_todos = [t for t in todos if t.get('status') == 'pending']

                    if pending_todos:
                        details['pending_todos'] = len(pending_todos)
                        if activity == 'idle':
                            activity = 'busy'
                        logger.debug(f"Reality {reality.id} has {len(pending_todos)} pending todos")

                except json.JSONDecodeError as e:
                    status = 'red'
                    activity = 'error'
                    details['model_readable'] = False
                    details['errors'] = details.get('errors', [])
                    details['errors'].append(f'Invalid JSON in model: {str(e)}')
                    logger.error(f"Reality {reality.id} has invalid JSON: {e}")
                except Exception as e:
                    status = 'red'
                    activity = 'error'
                    details['model_readable'] = False
                    details['errors'] = details.get('errors', [])
                    details['errors'].append(f'Failed to read model: {str(e)}')
                    logger.error(f"Reality {reality.id} model read error: {e}")

            # Check 4: Hash verification (drift detection)
            if reality.has_model:
                try:
                    hash_checks = verify_model(reality.full_model_path)

                    if hash_checks:
                        total_checks = len(hash_checks)
                        ok_checks = sum(1 for c in hash_checks if c.status == 'ok')
                        mismatch_checks = sum(1 for c in hash_checks if c.status == 'mismatch')
                        missing_checks = sum(1 for c in hash_checks if c.status == 'missing')
                        error_checks = sum(1 for c in hash_checks if c.status == 'error')

                        details['hash_checks'] = {
                            'total': total_checks,
                            'ok': ok_checks,
                            'mismatch': mismatch_checks,
                            'missing': missing_checks,
                            'errors': error_checks,
                        }

                        # All checks passed
                        if ok_checks == total_checks:
                            hash_verified = True
                        else:
                            hash_verified = False

                            # Mismatches = drift detected = red status
                            if mismatch_checks > 0:
                                status = 'red'
                                if activity != 'error':
                                    activity = 'busy'  # Files being modified
                                details['warnings'] = details.get('warnings', [])
                                details['warnings'].append(f'{mismatch_checks} hash mismatch(es) - drift detected')
                                logger.warning(f"Reality {reality.id} has {mismatch_checks} hash mismatches")

                            # Missing files = yellow status
                            if missing_checks > 0 and status != 'red':
                                status = 'yellow'
                                details['warnings'] = details.get('warnings', [])
                                details['warnings'].append(f'{missing_checks} missing file(s)')
                                logger.warning(f"Reality {reality.id} has {missing_checks} missing files")

                            # Errors reading files = red status
                            if error_checks > 0:
                                status = 'red'
                                activity = 'error'
                                details['errors'] = details.get('errors', [])
                                details['errors'].append(f'{error_checks} hash verification error(s)')
                                logger.error(f"Reality {reality.id} has {error_checks} hash verification errors")
                    else:
                        # No hash checks = nothing to verify = green
                        hash_verified = True
                        details['hash_checks'] = {'total': 0}

                except Exception as e:
                    status = 'red'
                    activity = 'error'
                    details['errors'] = details.get('errors', [])
                    details['errors'].append(f'Hash verification failed: {str(e)}')
                    logger.error(f"Reality {reality.id} hash verification failed: {e}")

            # Check 5: Check for running spawnie tasks (if this is spawnie)
            # This is a placeholder - actual implementation would check process status
            if reality.id == 'reality-spawnie' and reality.path:
                # TODO: Integrate with spawnie's session tracking when available
                details['note'] = 'Process monitoring not yet implemented'
                pass

        except Exception as e:
            # Catch-all for unexpected errors
            status = 'red'
            activity = 'error'
            details['errors'] = details.get('errors', [])
            details['errors'].append(f'Unexpected error: {str(e)}')
            logger.exception(f"Unexpected error checking reality {reality.id}")

        return PulseResult(
            reality_id=reality.id,
            status=status,
            activity=activity,
            hash_verified=hash_verified,
            last_checked=now,
            details=details,
        )

    def pulse_all(self) -> List[PulseResult]:
        """Run health checks on all realities.

        Returns:
            List of PulseResult for each reality in the model
        """
        logger.info("Starting pulse check on all realities")
        realities = self.get_realities()
        results = []

        for reality in realities:
            try:
                result = self.check_reality(reality)
                results.append(result)
                logger.debug(f"Pulse {reality.id}: {result.status} / {result.activity}")
            except Exception as e:
                # Create error result for this reality
                logger.exception(f"Failed to pulse reality {reality.id}")
                results.append(PulseResult(
                    reality_id=reality.id,
                    status='red',
                    activity='error',
                    hash_verified=False,
                    last_checked=datetime.now(),
                    details={
                        'label': reality.label,
                        'errors': [f'Pulse check failed: {str(e)}']
                    }
                ))

        logger.info(f"Pulse check complete: {len(results)} realities checked")
        return results

    def quick_verify(self, reality: Reality) -> bool:
        """Quick hash-only verification check.

        This is a lightweight check that only verifies source hashes without
        performing full health diagnostics.

        Args:
            reality: Reality object to verify

        Returns:
            True if all hashes match, False otherwise
        """
        if not reality.has_model:
            logger.debug(f"Quick verify {reality.id}: no model")
            return False

        try:
            hash_checks = verify_model(reality.full_model_path)

            if not hash_checks:
                # No hashes to verify = OK
                return True

            # All checks must be 'ok'
            result = all(check.status == 'ok' for check in hash_checks)
            logger.debug(f"Quick verify {reality.id}: {result}")
            return result

        except Exception as e:
            logger.error(f"Quick verify {reality.id} failed: {e}")
            return False

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics from the last pulse_all() call.

        Returns:
            Dictionary with summary statistics
        """
        results = self.pulse_all()

        total = len(results)
        green = sum(1 for r in results if r.status == 'green')
        yellow = sum(1 for r in results if r.status == 'yellow')
        red = sum(1 for r in results if r.status == 'red')

        idle = sum(1 for r in results if r.activity == 'idle')
        busy = sum(1 for r in results if r.activity == 'busy')
        error = sum(1 for r in results if r.activity == 'error')

        verified = sum(1 for r in results if r.hash_verified)

        return {
            'total': total,
            'status': {
                'green': green,
                'yellow': yellow,
                'red': red,
            },
            'activity': {
                'idle': idle,
                'busy': busy,
                'error': error,
            },
            'hash_verified': verified,
            'timestamp': datetime.now().isoformat(),
        }
