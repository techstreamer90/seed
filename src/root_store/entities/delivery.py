"""Message Delivery System - guaranteed delivery with escalation.

The MessageBus ensures messages reach their intended recipients:
1. Try primary channel
2. If failed/unacknowledged, try backup channels
3. If all channels fail, escalate to escalation path
4. If escalation fails, alert guardians
5. Log everything for audit

No message should be silently lost.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Any
from pathlib import Path
import uuid
import json

from .registry import EntityRegistry, Entity, EntityStatus, EntityType
from .channels import Channel, ChannelMessage, ModelChannel, WorkspaceChannel, ExternalChannel


@dataclass
class Message:
    """A message to be delivered through the system."""

    to: str                          # Target entity ID
    subject: str                     # What this is about
    body: Any                        # The content
    from_entity: str = "system"      # Sender
    priority: str = "normal"         # normal, urgent, emergency
    requires_ack: bool = False       # Must recipient acknowledge?
    ttl: timedelta = None            # Time to live
    escalate_on_failure: bool = True # Should we escalate if undeliverable?

    # Set by delivery system
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DeliveryResult:
    """Result of attempting to deliver a message."""

    message_id: str
    success: bool
    delivered_to: Optional[str] = None
    delivered_via: Optional[str] = None
    acknowledged: bool = False
    escalated_to: Optional[list[str]] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "success": self.success,
            "delivered_to": self.delivered_to,
            "delivered_via": self.delivered_via,
            "acknowledged": self.acknowledged,
            "escalated_to": self.escalated_to,
            "error": self.error,
        }


class MessageBus:
    """Central message delivery system with guaranteed delivery."""

    def __init__(
        self,
        registry: EntityRegistry,
        messages_dir: Path,
        audit_dir: Path = None,
    ):
        self.registry = registry
        self.audit_dir = audit_dir or messages_dir / "audit"
        self.audit_dir.mkdir(parents=True, exist_ok=True)

        # Initialize channels
        self.channels: dict[str, Channel] = {
            "model": ModelChannel(messages_dir / "inboxes"),
            "workspace": WorkspaceChannel(),
            "external": ExternalChannel(),
        }

    def send(self, message: Message) -> DeliveryResult:
        """Send a message with delivery guarantees.

        1. Look up recipient
        2. Try each channel in order
        3. Escalate on failure if requested
        4. Log everything
        """
        result = DeliveryResult(message_id=message.id, success=False)

        # Look up recipient
        entity = self.registry.get(message.to)
        if not entity:
            result.error = f"Entity not found: {message.to}"
            self._audit_delivery(message, result)
            return result

        # Check if entity is reachable
        if not entity.is_reachable():
            if message.escalate_on_failure:
                return self._escalate(message, entity, f"Entity unreachable: {message.to}")
            else:
                result.error = f"Entity unreachable: {message.to}"
                self._audit_delivery(message, result)
                return result

        # Create channel message
        expires_at = None
        if message.ttl:
            expires_at = message.created_at + message.ttl

        channel_msg = ChannelMessage(
            id=message.id,
            from_entity=message.from_entity,
            to_entity=message.to,
            subject=message.subject,
            body=message.body,
            priority=message.priority,
            requires_ack=message.requires_ack,
            created_at=message.created_at,
            expires_at=expires_at,
        )

        # Try each channel the entity supports
        for channel_name in entity.channels:
            channel = self.channels.get(channel_name)
            if not channel:
                continue

            try:
                if channel.send(channel_msg):
                    result.success = True
                    result.delivered_to = message.to
                    result.delivered_via = channel_name
                    self._audit_delivery(message, result)
                    return result
            except Exception as e:
                continue  # Try next channel

        # All channels failed
        if message.escalate_on_failure:
            return self._escalate(message, entity, "All channels failed")
        else:
            result.error = "All channels failed"
            self._audit_delivery(message, result)
            return result

    def _escalate(self, message: Message, original_entity: Entity, reason: str) -> DeliveryResult:
        """Escalate message delivery to backup entities."""
        result = DeliveryResult(message_id=message.id, success=False)
        result.escalated_to = []

        # Get escalation path
        escalation_path = self.registry.get_escalation_path(original_entity.id)

        for backup_entity in escalation_path:
            # Create escalation message
            escalation_msg = Message(
                to=backup_entity.id,
                subject=f"[ESCALATED] {message.subject}",
                body={
                    "original_message": message.body,
                    "original_recipient": original_entity.id,
                    "escalation_reason": reason,
                    "original_sender": message.from_entity,
                },
                from_entity="system:escalation",
                priority="urgent" if message.priority == "normal" else message.priority,
                requires_ack=True,
                escalate_on_failure=False,  # Don't recursively escalate
            )

            backup_result = self.send(escalation_msg)
            result.escalated_to.append(backup_entity.id)

            if backup_result.success:
                result.success = True
                result.delivered_to = backup_entity.id
                result.delivered_via = backup_result.delivered_via
                self._audit_delivery(message, result, escalated=True)
                return result

        # All escalation attempts failed - this is serious
        result.error = f"Delivery failed and all escalation attempts failed: {reason}"
        self._alert_guardians(message, result)
        self._audit_delivery(message, result, escalated=True)
        return result

    def _alert_guardians(self, message: Message, result: DeliveryResult) -> None:
        """Last resort: alert all guardians about delivery failure."""
        guardians = self.registry.find_guardians()

        for guardian in guardians:
            alert = Message(
                to=guardian.id,
                subject=f"[GUARDIAN ALERT] Message delivery failed",
                body={
                    "failed_message_id": message.id,
                    "original_recipient": message.to,
                    "original_subject": message.subject,
                    "failure_reason": result.error,
                    "escalation_attempts": result.escalated_to,
                },
                from_entity="system:guardian-alert",
                priority="emergency",
                requires_ack=True,
                escalate_on_failure=False,
            )

            # Try to reach guardian directly
            guardian_channel = self.channels.get("model")
            if guardian_channel:
                channel_msg = ChannelMessage(
                    id=alert.id,
                    from_entity=alert.from_entity,
                    to_entity=alert.to,
                    subject=alert.subject,
                    body=alert.body,
                    priority=alert.priority,
                    requires_ack=True,
                )
                guardian_channel.send(channel_msg)

    def _audit_delivery(
        self,
        message: Message,
        result: DeliveryResult,
        escalated: bool = False,
    ) -> None:
        """Log delivery attempt for audit trail."""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "message_id": message.id,
            "from": message.from_entity,
            "to": message.to,
            "subject": message.subject,
            "priority": message.priority,
            "result": result.to_dict(),
            "escalated": escalated,
        }

        # Write to audit log
        audit_file = self.audit_dir / f"{message.id}.json"
        audit_file.write_text(json.dumps(audit_entry, indent=2), encoding="utf-8")

    def check_pending(self, entity_id: str) -> list[ChannelMessage]:
        """Check for pending messages for an entity across all channels."""
        all_messages = []

        for channel in self.channels.values():
            try:
                messages = channel.receive(entity_id)
                all_messages.extend(messages)
            except Exception:
                continue

        return all_messages

    def acknowledge(self, message_id: str, entity_id: str, channel_name: str = "model") -> bool:
        """Acknowledge receipt of a message."""
        channel = self.channels.get(channel_name)
        if channel and hasattr(channel, 'acknowledge'):
            # ModelChannel needs entity_id
            if isinstance(channel, ModelChannel):
                return channel.acknowledge(message_id, entity_id)
            else:
                return channel.acknowledge(message_id)
        return False

    def broadcast(
        self,
        subject: str,
        body: Any,
        to_types: list[EntityType] = None,
        priority: str = "normal",
        from_entity: str = "system",
    ) -> list[DeliveryResult]:
        """Broadcast a message to multiple entities.

        Args:
            to_types: If specified, only send to entities of these types.
                      If None, send to all reachable entities.
        """
        results = []

        entities = self.registry.find_reachable()
        if to_types:
            entities = [e for e in entities if e.type in to_types]

        for entity in entities:
            msg = Message(
                to=entity.id,
                subject=subject,
                body=body,
                from_entity=from_entity,
                priority=priority,
            )
            results.append(self.send(msg))

        return results

    def emergency_broadcast(self, subject: str, body: Any, from_entity: str = "system") -> list[DeliveryResult]:
        """Emergency broadcast to all guardians and humans."""
        return self.broadcast(
            subject=f"[EMERGENCY] {subject}",
            body=body,
            to_types=[EntityType.HUMAN, EntityType.ETHICAL_AI],
            priority="emergency",
            from_entity=from_entity,
        )
