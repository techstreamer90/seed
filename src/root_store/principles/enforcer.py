"""Principle Enforcer - runs checks and handles violations."""

from __future__ import annotations
from datetime import datetime
from typing import Optional, Callable
from pathlib import Path
import json

from .core import (
    Principle, PrincipleViolation, PrincipleCheck,
    PrincipleSeverity, ViolationType,
)
from .builtin import INVIOLABLE_PRINCIPLES


class PrincipleEnforcer:
    """Enforces principles on all actions.

    The enforcer is the gatekeeper. Before any significant action,
    it must pass through the enforcer. The enforcer:

    1. Checks all applicable principles
    2. Records any violations
    3. Blocks inviolable principle violations
    4. Escalates to appropriate authorities
    5. Maintains violation history

    Principles can be loaded from:
    - Built-in hardcoded principles (fallback)
    - External file (golden reference on desktop)
    - Future: Online democratic voting system

    Usage:
        enforcer = PrincipleEnforcer(...)
        check = enforcer.check_action("delete_node", {"node_id": "x", "actor": "y"})
        if not check.allowed:
            # Handle violation
    """

    def __init__(
        self,
        violations_dir: Path,
        on_violation: Callable[[PrincipleViolation], None] = None,
        additional_principles: list[Principle] = None,
        principles_path: Path = None,
        use_external_principles: bool = True,
    ):
        """Initialize the enforcer.

        Args:
            violations_dir: Where to store violation records
            on_violation: Callback when violation occurs (for escalation)
            additional_principles: Extra principles beyond loaded ones
            principles_path: Path to external principles file (golden reference)
            use_external_principles: Whether to load from external file
        """
        self.violations_dir = violations_dir
        self.violations_dir.mkdir(parents=True, exist_ok=True)

        self.on_violation = on_violation
        self.principles_path = principles_path

        # Load principles from external source or fallback to built-in
        if use_external_principles:
            from .external import get_principles
            base_principles = get_principles(local_path=principles_path)
        else:
            base_principles = INVIOLABLE_PRINCIPLES

        self._principles: dict[str, Principle] = {
            p.id: p for p in base_principles
        }

        # Add any additional principles
        if additional_principles:
            for p in additional_principles:
                if p.id not in self._principles:
                    self._principles[p.id] = p

        # Load violation history
        self._violations: list[PrincipleViolation] = []
        self._load_violations()

    def _load_violations(self) -> None:
        """Load violation history from storage."""
        violations_file = self.violations_dir / "violations.json"
        if violations_file.exists():
            try:
                data = json.loads(violations_file.read_text(encoding="utf-8"))
                self._violations = [
                    PrincipleViolation.from_dict(v)
                    for v in data.get("violations", [])
                ]
            except Exception:
                pass

    def _save_violations(self) -> None:
        """Persist violation history."""
        violations_file = self.violations_dir / "violations.json"
        data = {
            "violations": [v.to_dict() for v in self._violations[-1000:]],  # Keep last 1000
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }
        violations_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def check_action(
        self,
        action: str,
        context: dict,
        actor: str = "unknown",
    ) -> PrincipleCheck:
        """Check if an action violates any principles.

        This is the main entry point. Call this before any significant action.
        """
        result = PrincipleCheck(action=action, actor=actor)

        for principle in self._principles.values():
            if not principle.active:
                continue

            violated, reason = principle.evaluate(action, context)

            if violated:
                violation = PrincipleViolation(
                    principle_id=principle.id,
                    principle_name=principle.name,
                    severity=principle.severity,
                    violation_type=ViolationType.ATTEMPTED,
                    action=action,
                    actor=actor,
                    reason=reason,
                    context=context,
                )

                result.violations.append(violation)
                self._violations.append(violation)

                # Determine if this blocks the action
                if principle.severity == PrincipleSeverity.INVIOLABLE:
                    result.allowed = False
                    result.can_override = False
                elif principle.severity == PrincipleSeverity.REQUIRED:
                    result.allowed = False
                    result.can_override = True
                    result.override_requires = "consensus"
                else:  # ADVISORY
                    result.warnings.append(f"{principle.name}: {reason}")

                # Trigger violation callback
                if self.on_violation:
                    self.on_violation(violation)

        if result.violations:
            self._save_violations()

        return result

    def require(
        self,
        action: str,
        context: dict,
        actor: str = "unknown",
    ) -> None:
        """Check action and raise if violated.

        Use this as a decorator or guard:
            enforcer.require("delete_node", {"node_id": x}, actor=user_id)
            # Only reaches here if allowed
        """
        check = self.check_action(action, context, actor)

        if not check.allowed:
            violations_str = "; ".join(
                f"{v.principle_name}: {v.reason}"
                for v in check.violations
            )
            raise PrincipleViolationError(
                f"Action '{action}' blocked by principles: {violations_str}",
                check=check,
            )

    def add_principle(self, principle: Principle) -> bool:
        """Add a new principle (if not built-in)."""
        if principle.id in self._principles:
            existing = self._principles[principle.id]
            # Cannot modify inviolable principles
            if existing.severity == PrincipleSeverity.INVIOLABLE:
                return False

        self._principles[principle.id] = principle
        return True

    def get_principle(self, principle_id: str) -> Optional[Principle]:
        """Get a principle by ID."""
        return self._principles.get(principle_id)

    def list_principles(self, include_inactive: bool = False) -> list[Principle]:
        """List all principles."""
        if include_inactive:
            return list(self._principles.values())
        return [p for p in self._principles.values() if p.active]

    def get_violations(
        self,
        actor: str = None,
        principle_id: str = None,
        unresolved_only: bool = False,
        limit: int = 100,
    ) -> list[PrincipleViolation]:
        """Get violation history with optional filters."""
        violations = self._violations

        if actor:
            violations = [v for v in violations if v.actor == actor]

        if principle_id:
            violations = [v for v in violations if v.principle_id == principle_id]

        if unresolved_only:
            violations = [v for v in violations if not v.resolved]

        return violations[-limit:]

    def resolve_violation(
        self,
        violation_id: str,
        resolution: str,
        resolved_by: str,
    ) -> bool:
        """Mark a violation as resolved."""
        for violation in self._violations:
            if violation.id == violation_id:
                violation.resolved = True
                violation.resolution = resolution
                violation.resolved_by = resolved_by
                violation.resolved_at = datetime.utcnow()
                self._save_violations()
                return True
        return False

    def get_stats(self) -> dict:
        """Get enforcement statistics."""
        total = len(self._violations)
        by_severity = {
            "inviolable": 0,
            "required": 0,
            "advisory": 0,
        }
        unresolved = 0

        for v in self._violations:
            by_severity[v.severity.value] = by_severity.get(v.severity.value, 0) + 1
            if not v.resolved:
                unresolved += 1

        return {
            "total_violations": total,
            "unresolved": unresolved,
            "by_severity": by_severity,
            "principles_count": len(self._principles),
            "inviolable_count": sum(
                1 for p in self._principles.values()
                if p.severity == PrincipleSeverity.INVIOLABLE
            ),
        }


class PrincipleViolationError(Exception):
    """Raised when an action violates principles."""

    def __init__(self, message: str, check: PrincipleCheck):
        super().__init__(message)
        self.check = check
