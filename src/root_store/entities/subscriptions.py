"""Subscription System - who wants to know about what.

Entities can subscribe to events they care about:
- Guardians subscribe to principle_violation, authority_override
- Humans subscribe to consensus_required, escalation
- Nodes subscribe to changes affecting them

When an event occurs, all subscribers are notified through the MessageBus.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional
from pathlib import Path
import json
import fnmatch

from .registry import EntityRegistry, EntityType
from .delivery import MessageBus, Message


@dataclass
class Subscription:
    """A subscription to events."""

    entity_id: str                    # Who is subscribing
    event_patterns: list[str]         # What events (supports wildcards)
    priority: str = "normal"          # Message priority for notifications
    requires_ack: bool = False        # Must subscriber acknowledge?
    active: bool = True               # Is this subscription active?
    created_at: datetime = field(default_factory=datetime.utcnow)

    def matches(self, event_type: str) -> bool:
        """Check if this subscription matches an event type."""
        for pattern in self.event_patterns:
            if fnmatch.fnmatch(event_type, pattern):
                return True
        return False

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "event_patterns": self.event_patterns,
            "priority": self.priority,
            "requires_ack": self.requires_ack,
            "active": self.active,
            "created_at": self.created_at.isoformat() + "Z",
        }

    @classmethod
    def from_dict(cls, data: dict) -> Subscription:
        return cls(
            entity_id=data["entity_id"],
            event_patterns=data["event_patterns"],
            priority=data.get("priority", "normal"),
            requires_ack=data.get("requires_ack", False),
            active=data.get("active", True),
            created_at=datetime.fromisoformat(data["created_at"].rstrip("Z")) if data.get("created_at") else datetime.utcnow(),
        )


@dataclass
class Event:
    """An event that occurred in the system."""

    type: str                         # Event type (e.g., "node.modified")
    source: str                       # Who/what caused it
    subject: Optional[str] = None     # What it's about (e.g., node ID)
    data: Any = None                  # Event payload
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "source": self.source,
            "subject": self.subject,
            "data": self.data,
            "timestamp": self.timestamp.isoformat() + "Z",
        }


# Standard event types
class EventTypes:
    """Standard event types in the system."""

    # Principle events (highest priority)
    PRINCIPLE_VIOLATION = "principle.violation"
    PRINCIPLE_VIOLATION_ATTEMPT = "principle.violation_attempt"

    # Authority events
    AUTHORITY_OVERRIDE = "authority.override"
    CONSENSUS_REQUIRED = "authority.consensus_required"
    CONSENSUS_REACHED = "authority.consensus_reached"

    # Node events
    NODE_CREATED = "node.created"
    NODE_MODIFIED = "node.modified"
    NODE_DELETED = "node.deleted"
    NODE_MESSAGE = "node.message"

    # Entity events
    ENTITY_REGISTERED = "entity.registered"
    ENTITY_ACTIVATED = "entity.activated"
    ENTITY_DEACTIVATED = "entity.deactivated"
    ENTITY_UNREACHABLE = "entity.unreachable"

    # Workspace events
    WORKSPACE_CREATED = "workspace.created"
    WORKSPACE_COMMITTED = "workspace.committed"
    WORKSPACE_DISCARDED = "workspace.discarded"

    # System events
    ESCALATION = "system.escalation"
    GUARDIAN_ALERT = "system.guardian_alert"
    INTEGRITY_CHECK = "system.integrity_check"


class SubscriptionManager:
    """Manages event subscriptions and dispatches events."""

    def __init__(
        self,
        registry: EntityRegistry,
        message_bus: MessageBus,
        storage_path: Optional[Path] = None,
    ):
        self.registry = registry
        self.message_bus = message_bus
        self.storage_path = storage_path
        self._subscriptions: list[Subscription] = []
        self._load()

        # Set up default subscriptions for guardians
        self._setup_default_subscriptions()

    def _load(self):
        """Load subscriptions from storage."""
        if self.storage_path and self.storage_path.exists():
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
            self._subscriptions = [
                Subscription.from_dict(s) for s in data.get("subscriptions", [])
            ]

    def _save(self):
        """Persist subscriptions to storage."""
        if self.storage_path:
            data = {
                "subscriptions": [s.to_dict() for s in self._subscriptions],
                "updated_at": datetime.utcnow().isoformat() + "Z",
            }
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _setup_default_subscriptions(self):
        """Set up default subscriptions that should always exist."""
        # All guardians should receive principle violations and escalations
        for guardian in self.registry.find_guardians():
            self.subscribe(
                entity_id=guardian.id,
                event_patterns=[
                    "principle.*",
                    "authority.*",
                    "system.escalation",
                    "system.guardian_alert",
                ],
                priority="emergency",
                requires_ack=True,
            )

        # All humans should receive consensus requests and escalations
        for human in self.registry.find_humans():
            self.subscribe(
                entity_id=human.id,
                event_patterns=[
                    "authority.consensus_required",
                    "system.escalation",
                    "principle.violation",
                ],
                priority="urgent",
                requires_ack=True,
            )

    def subscribe(
        self,
        entity_id: str,
        event_patterns: list[str],
        priority: str = "normal",
        requires_ack: bool = False,
    ) -> Subscription:
        """Create a new subscription."""
        # Check if subscription already exists
        for sub in self._subscriptions:
            if sub.entity_id == entity_id and set(sub.event_patterns) == set(event_patterns):
                return sub

        subscription = Subscription(
            entity_id=entity_id,
            event_patterns=event_patterns,
            priority=priority,
            requires_ack=requires_ack,
        )
        self._subscriptions.append(subscription)
        self._save()
        return subscription

    def unsubscribe(self, entity_id: str, event_patterns: list[str] = None) -> None:
        """Remove subscriptions for an entity.

        If event_patterns is None, removes all subscriptions for the entity.
        """
        if event_patterns is None:
            self._subscriptions = [
                s for s in self._subscriptions if s.entity_id != entity_id
            ]
        else:
            pattern_set = set(event_patterns)
            self._subscriptions = [
                s for s in self._subscriptions
                if not (s.entity_id == entity_id and set(s.event_patterns) == pattern_set)
            ]
        self._save()

    def get_subscriptions(self, entity_id: str) -> list[Subscription]:
        """Get all subscriptions for an entity."""
        return [s for s in self._subscriptions if s.entity_id == entity_id and s.active]

    def emit(self, event: Event) -> list[str]:
        """Emit an event and notify all subscribers.

        Returns list of entity IDs that were notified.
        """
        notified = []

        for subscription in self._subscriptions:
            if not subscription.active:
                continue

            if subscription.matches(event.type):
                # Send notification
                msg = Message(
                    to=subscription.entity_id,
                    subject=f"[EVENT] {event.type}",
                    body=event.to_dict(),
                    from_entity=event.source,
                    priority=subscription.priority,
                    requires_ack=subscription.requires_ack,
                )

                result = self.message_bus.send(msg)
                if result.success:
                    notified.append(subscription.entity_id)

        return notified

    def emit_principle_violation(
        self,
        principle: str,
        violator: str,
        action: str,
        evidence: Any = None,
    ) -> list[str]:
        """Emit a principle violation event (highest priority)."""
        event = Event(
            type=EventTypes.PRINCIPLE_VIOLATION,
            source="system:integrity",
            subject=principle,
            data={
                "principle": principle,
                "violator": violator,
                "action": action,
                "evidence": evidence,
            },
        )
        return self.emit(event)

    def emit_consensus_required(
        self,
        action: str,
        requester: str,
        affected_entities: list[str],
        reason: str,
    ) -> list[str]:
        """Emit a consensus required event."""
        event = Event(
            type=EventTypes.CONSENSUS_REQUIRED,
            source=requester,
            subject=action,
            data={
                "action": action,
                "requester": requester,
                "affected_entities": affected_entities,
                "reason": reason,
            },
        )
        return self.emit(event)

    def emit_node_modified(
        self,
        node_id: str,
        modifier: str,
        changes: dict,
    ) -> list[str]:
        """Emit a node modification event."""
        event = Event(
            type=EventTypes.NODE_MODIFIED,
            source=modifier,
            subject=node_id,
            data={
                "node_id": node_id,
                "modifier": modifier,
                "changes": changes,
            },
        )
        return self.emit(event)
