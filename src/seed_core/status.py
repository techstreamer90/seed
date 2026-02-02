"""
Status - Aggregated status reporting for seed-core.

The Status component provides aggregated status information across all realities
in the seed meta-model, building on the Pulse health monitoring system.

Key Features:
- Reality-level status aggregation
- Overall seed status calculation
- Todo counting and drift detection
- Formatted summary and detailed reports
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, List, Optional

from .pulse import Pulse, PulseResult


logger = logging.getLogger(__name__)


@dataclass
class RealityStatus:
    """Status information for a single reality.

    Attributes:
        id: Unique identifier for the reality
        label: Human-readable name
        path: Path to the reality's directory
        status: Health status - green (healthy), yellow (warnings), red (errors)
        activity: Activity state - idle (no work), busy (active), error (problems)
        todos_pending: Number of pending todos in this reality
        last_pulse: Timestamp of the last pulse check
        drift_detected: Whether hash drift was detected
    """
    id: str
    label: str
    path: Optional[Path]
    status: Literal['green', 'yellow', 'red']
    activity: Literal['idle', 'busy', 'error']
    todos_pending: int
    last_pulse: datetime
    drift_detected: bool

    @property
    def is_healthy(self) -> bool:
        """Return True if status is green."""
        return self.status == 'green'

    @property
    def has_issues(self) -> bool:
        """Return True if status is yellow or red."""
        return self.status in ('yellow', 'red')

    @property
    def has_work(self) -> bool:
        """Return True if there are pending todos or activity."""
        return self.todos_pending > 0 or self.activity != 'idle'


@dataclass
class SeedStatus:
    """Aggregated status for the entire seed system.

    Attributes:
        overall_status: Aggregated health status across all realities
        realities: List of individual reality statuses
        total_todos: Total pending todos across all realities
        realities_with_drift: Count of realities with detected drift
        last_updated: Timestamp when this status was generated
    """
    overall_status: Literal['green', 'yellow', 'red']
    realities: List[RealityStatus]
    total_todos: int
    realities_with_drift: int
    last_updated: datetime

    @property
    def total_realities(self) -> int:
        """Total number of realities."""
        return len(self.realities)

    @property
    def healthy_realities(self) -> int:
        """Number of green realities."""
        return sum(1 for r in self.realities if r.status == 'green')

    @property
    def warning_realities(self) -> int:
        """Number of yellow realities."""
        return sum(1 for r in self.realities if r.status == 'yellow')

    @property
    def error_realities(self) -> int:
        """Number of red realities."""
        return sum(1 for r in self.realities if r.status == 'red')

    @property
    def is_healthy(self) -> bool:
        """Return True if overall status is green."""
        return self.overall_status == 'green'


class StatusAggregator:
    """Aggregates status information across all realities.

    Uses the Pulse component to perform health checks and aggregates
    the results into structured status reports.

    Attributes:
        pulse: Pulse instance for health monitoring
    """

    def __init__(self, pulse: Pulse):
        """Initialize status aggregator.

        Args:
            pulse: Pulse instance to use for health checks
        """
        self.pulse = pulse
        self._cached_status: Optional[SeedStatus] = None
        self._cache_time: Optional[datetime] = None

    def get_status(self, use_cache: bool = False) -> SeedStatus:
        """Get current aggregated status for all realities.

        Args:
            use_cache: If True, return cached status if available

        Returns:
            SeedStatus with aggregated information
        """
        # Check cache
        if use_cache and self._cached_status is not None:
            logger.debug("Returning cached status")
            return self._cached_status

        # Run pulse checks on all realities
        logger.info("Gathering status from all realities")
        pulse_results = self.pulse.pulse_all()

        # Convert pulse results to reality statuses
        reality_statuses = []
        for result in pulse_results:
            reality_status = self._convert_pulse_result(result)
            reality_statuses.append(reality_status)

        # Calculate aggregated metrics
        total_todos = sum(r.todos_pending for r in reality_statuses)
        realities_with_drift = sum(1 for r in reality_statuses if r.drift_detected)

        # Determine overall status using status rules
        overall_status = self._calculate_overall_status(reality_statuses)

        # Create seed status
        now = datetime.now()
        seed_status = SeedStatus(
            overall_status=overall_status,
            realities=reality_statuses,
            total_todos=total_todos,
            realities_with_drift=realities_with_drift,
            last_updated=now,
        )

        # Cache the result
        self._cached_status = seed_status
        self._cache_time = now

        logger.info(f"Status aggregation complete: {overall_status}")
        return seed_status

    def get_reality_status(self, reality_id: str) -> Optional[RealityStatus]:
        """Get status for a specific reality.

        Args:
            reality_id: ID of the reality to query

        Returns:
            RealityStatus if found, None otherwise
        """
        # Get all realities
        realities = self.pulse.get_realities()

        # Find matching reality
        reality = None
        for r in realities:
            if r.id == reality_id:
                reality = r
                break

        if not reality:
            logger.warning(f"Reality not found: {reality_id}")
            return None

        # Run pulse check on this reality
        pulse_result = self.pulse.check_reality(reality)

        # Convert to reality status
        return self._convert_pulse_result(pulse_result)

    def format_summary(self) -> str:
        """Format a brief summary of the overall status.

        Returns:
            Single-line summary string
        """
        status = self.get_status(use_cache=True)

        # Status indicator
        status_indicators = {
            'green': '✓',
            'yellow': '⚠',
            'red': '✗',
        }
        indicator = status_indicators.get(status.overall_status, '?')

        # Build summary
        parts = [
            f"{indicator} Seed Status: {status.overall_status.upper()}",
            f"{status.total_realities} realities",
            f"{status.healthy_realities} healthy",
        ]

        if status.warning_realities > 0:
            parts.append(f"{status.warning_realities} warnings")

        if status.error_realities > 0:
            parts.append(f"{status.error_realities} errors")

        if status.total_todos > 0:
            parts.append(f"{status.total_todos} todos")

        if status.realities_with_drift > 0:
            parts.append(f"{status.realities_with_drift} with drift")

        return " | ".join(parts)

    def format_detailed(self) -> str:
        """Format a detailed multi-line status report.

        Returns:
            Formatted detailed status report
        """
        status = self.get_status(use_cache=True)

        lines = []
        lines.append("=" * 70)
        lines.append("SEED STATUS REPORT")
        lines.append("=" * 70)
        lines.append(f"Generated: {status.last_updated.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Overall Status: {status.overall_status.upper()}")
        lines.append("")

        # Summary section
        lines.append("SUMMARY")
        lines.append("-" * 70)
        lines.append(f"  Total Realities: {status.total_realities}")
        lines.append(f"  Healthy (Green): {status.healthy_realities}")
        lines.append(f"  Warnings (Yellow): {status.warning_realities}")
        lines.append(f"  Errors (Red): {status.error_realities}")
        lines.append(f"  Total Pending Todos: {status.total_todos}")
        lines.append(f"  Realities with Drift: {status.realities_with_drift}")
        lines.append("")

        # Reality details
        lines.append("REALITY DETAILS")
        lines.append("-" * 70)

        for reality in status.realities:
            # Status symbol
            status_symbols = {
                'green': '✓',
                'yellow': '⚠',
                'red': '✗',
            }
            symbol = status_symbols.get(reality.status, '?')

            # Activity indicator
            activity_symbols = {
                'idle': '○',
                'busy': '◉',
                'error': '✗',
            }
            act_symbol = activity_symbols.get(reality.activity, '?')

            # Build reality line
            reality_line = f"{symbol} [{reality.status.upper()}] {reality.label}"
            lines.append(reality_line)

            # Details indented
            lines.append(f"    ID: {reality.id}")
            if reality.path:
                lines.append(f"    Path: {reality.path}")
            lines.append(f"    Activity: {act_symbol} {reality.activity}")

            if reality.todos_pending > 0:
                lines.append(f"    Pending Todos: {reality.todos_pending}")

            if reality.drift_detected:
                lines.append(f"    Drift: DETECTED")

            lines.append(f"    Last Check: {reality.last_pulse.strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)

    def _convert_pulse_result(self, pulse_result: PulseResult) -> RealityStatus:
        """Convert a PulseResult to a RealityStatus.

        Args:
            pulse_result: PulseResult from pulse check

        Returns:
            RealityStatus with extracted information
        """
        details = pulse_result.details

        # Extract path
        path = None
        if details.get('path'):
            path = Path(details['path'])

        # Extract pending todos
        todos_pending = details.get('pending_todos', 0)

        # Detect drift from hash checks
        drift_detected = False
        hash_checks = details.get('hash_checks', {})
        if hash_checks.get('mismatch', 0) > 0:
            drift_detected = True

        return RealityStatus(
            id=pulse_result.reality_id,
            label=details.get('label', pulse_result.reality_id),
            path=path,
            status=pulse_result.status,
            activity=pulse_result.activity,
            todos_pending=todos_pending,
            last_pulse=pulse_result.last_checked,
            drift_detected=drift_detected,
        )

    def _calculate_overall_status(
        self,
        reality_statuses: List[RealityStatus]
    ) -> Literal['green', 'yellow', 'red']:
        """Calculate overall status from individual reality statuses.

        Status rules:
        - Overall green: all realities green
        - Overall yellow: any reality yellow, none red
        - Overall red: any reality red

        Args:
            reality_statuses: List of reality statuses

        Returns:
            Overall status: green, yellow, or red
        """
        if not reality_statuses:
            return 'green'

        # Check for red (highest priority)
        has_red = any(r.status == 'red' for r in reality_statuses)
        if has_red:
            return 'red'

        # Check for yellow (second priority)
        has_yellow = any(r.status == 'yellow' for r in reality_statuses)
        if has_yellow:
            return 'yellow'

        # All green
        return 'green'
