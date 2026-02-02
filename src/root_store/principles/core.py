"""Core principle definitions and violation handling."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any, Callable
import uuid


class PrincipleSeverity(Enum):
    """How severe is a principle - determines enforcement."""
    ADVISORY = "advisory"       # Warn but allow
    REQUIRED = "required"       # Block but can be overridden with consensus
    INVIOLABLE = "inviolable"   # Cannot be overridden by anyone


class ViolationType(Enum):
    """Type of principle violation."""
    ATTEMPTED = "attempted"     # Blocked before execution
    DETECTED = "detected"       # Found during audit
    REPORTED = "reported"       # Reported by entity


@dataclass
class Principle:
    """A principle that must be enforced.

    Principles are not rules that can be debated - they're fundamental
    constraints on what the system can do. Think constitutional limits,
    not policy preferences.
    """

    id: str                             # Unique identifier
    name: str                           # Human-readable name
    description: str                    # What this principle means
    severity: PrincipleSeverity         # How strictly enforced

    # The check function: (action, context) -> (violated: bool, reason: str)
    check: Callable[[str, dict], tuple[bool, str]] = None

    # What actions does this principle apply to?
    applies_to: list[str] = field(default_factory=list)  # Empty = all actions

    # Who defined this principle?
    source: str = "system"              # system, consensus, human

    # Is this principle active?
    active: bool = True

    def evaluate(self, action: str, context: dict) -> tuple[bool, str]:
        """Evaluate if an action violates this principle.

        Returns (violated, reason).
        """
        # Check if principle applies to this action
        if self.applies_to and action not in self.applies_to:
            return False, ""

        # Run the check
        if self.check:
            return self.check(action, context)

        return False, ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "severity": self.severity.value,
            "applies_to": self.applies_to,
            "source": self.source,
            "active": self.active,
        }


@dataclass
class PrincipleViolation:
    """A record of a principle violation."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    principle_id: str = ""
    principle_name: str = ""
    severity: PrincipleSeverity = PrincipleSeverity.REQUIRED

    violation_type: ViolationType = ViolationType.ATTEMPTED
    action: str = ""                    # What action was attempted
    actor: str = ""                     # Who tried to do it
    reason: str = ""                    # Why it's a violation

    context: dict = field(default_factory=dict)  # Full context
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Resolution
    resolved: bool = False
    resolution: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "principle_id": self.principle_id,
            "principle_name": self.principle_name,
            "severity": self.severity.value,
            "violation_type": self.violation_type.value,
            "action": self.action,
            "actor": self.actor,
            "reason": self.reason,
            "context": self.context,
            "timestamp": self.timestamp.isoformat() + "Z",
            "resolved": self.resolved,
            "resolution": self.resolution,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() + "Z" if self.resolved_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PrincipleViolation:
        return cls(
            id=data["id"],
            principle_id=data["principle_id"],
            principle_name=data["principle_name"],
            severity=PrincipleSeverity(data["severity"]),
            violation_type=ViolationType(data["violation_type"]),
            action=data["action"],
            actor=data["actor"],
            reason=data["reason"],
            context=data.get("context", {}),
            timestamp=datetime.fromisoformat(data["timestamp"].rstrip("Z")),
            resolved=data.get("resolved", False),
            resolution=data.get("resolution"),
            resolved_by=data.get("resolved_by"),
            resolved_at=datetime.fromisoformat(data["resolved_at"].rstrip("Z")) if data.get("resolved_at") else None,
        )


@dataclass
class PrincipleCheck:
    """Result of checking principles for an action."""

    action: str
    actor: str
    allowed: bool = True
    violations: list[PrincipleViolation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # If blocked, can it be overridden?
    can_override: bool = False
    override_requires: Optional[str] = None  # e.g., "consensus", "human"

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "actor": self.actor,
            "allowed": self.allowed,
            "violations": [v.to_dict() for v in self.violations],
            "warnings": self.warnings,
            "can_override": self.can_override,
            "override_requires": self.override_requires,
        }
