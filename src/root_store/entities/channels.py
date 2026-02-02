"""Communication Channels - how entities are reached.

Channels are the pathways through which messages flow:
- ModelChannel: Messages stored in the model (for nodes, persistent)
- WorkspaceChannel: Direct delivery to active workspace
- ExternalChannel: Outside the model (email, webhook, etc.)

Each channel has different guarantees and characteristics.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
from pathlib import Path
import json
import uuid


@dataclass
class ChannelMessage:
    """A message sent through a channel."""

    id: str
    from_entity: str
    to_entity: str
    subject: str
    body: Any  # Can be string, dict, etc.
    priority: str = "normal"  # normal, urgent, emergency
    requires_ack: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    # Delivery tracking
    delivered: bool = False
    delivered_at: Optional[datetime] = None
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "from_entity": self.from_entity,
            "to_entity": self.to_entity,
            "subject": self.subject,
            "body": self.body,
            "priority": self.priority,
            "requires_ack": self.requires_ack,
            "created_at": self.created_at.isoformat() + "Z",
            "expires_at": self.expires_at.isoformat() + "Z" if self.expires_at else None,
            "delivered": self.delivered,
            "delivered_at": self.delivered_at.isoformat() + "Z" if self.delivered_at else None,
            "acknowledged": self.acknowledged,
            "acknowledged_at": self.acknowledged_at.isoformat() + "Z" if self.acknowledged_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ChannelMessage:
        return cls(
            id=data["id"],
            from_entity=data["from_entity"],
            to_entity=data["to_entity"],
            subject=data["subject"],
            body=data["body"],
            priority=data.get("priority", "normal"),
            requires_ack=data.get("requires_ack", False),
            created_at=datetime.fromisoformat(data["created_at"].rstrip("Z")),
            expires_at=datetime.fromisoformat(data["expires_at"].rstrip("Z")) if data.get("expires_at") else None,
            delivered=data.get("delivered", False),
            delivered_at=datetime.fromisoformat(data["delivered_at"].rstrip("Z")) if data.get("delivered_at") else None,
            acknowledged=data.get("acknowledged", False),
            acknowledged_at=datetime.fromisoformat(data["acknowledged_at"].rstrip("Z")) if data.get("acknowledged_at") else None,
        )


class Channel(ABC):
    """Abstract base for communication channels."""

    name: str

    @abstractmethod
    def send(self, message: ChannelMessage) -> bool:
        """Send a message through this channel.

        Returns True if delivery was successful.
        """
        pass

    @abstractmethod
    def receive(self, entity_id: str) -> list[ChannelMessage]:
        """Receive pending messages for an entity."""
        pass

    @abstractmethod
    def acknowledge(self, message_id: str) -> bool:
        """Acknowledge receipt of a message."""
        pass


class ModelChannel(Channel):
    """Channel that stores messages in the model/filesystem.

    Messages are persisted as JSON files in a messages directory.
    This is the primary channel for node-to-node communication.
    Guarantees: persistent, survives restarts, auditable.
    """

    name = "model"

    def __init__(self, messages_dir: Path):
        self.messages_dir = messages_dir
        self.messages_dir.mkdir(parents=True, exist_ok=True)

    def _inbox_path(self, entity_id: str) -> Path:
        """Get the inbox directory for an entity."""
        # Sanitize entity_id for filesystem
        safe_id = entity_id.replace(":", "_").replace("/", "_")
        inbox = self.messages_dir / safe_id
        inbox.mkdir(parents=True, exist_ok=True)
        return inbox

    def send(self, message: ChannelMessage) -> bool:
        """Store message in recipient's inbox."""
        try:
            inbox = self._inbox_path(message.to_entity)
            msg_file = inbox / f"{message.id}.json"
            msg_file.write_text(json.dumps(message.to_dict(), indent=2), encoding="utf-8")

            # Mark as delivered
            message.delivered = True
            message.delivered_at = datetime.utcnow()

            # Update the file with delivery status
            msg_file.write_text(json.dumps(message.to_dict(), indent=2), encoding="utf-8")
            return True
        except Exception:
            return False

    def receive(self, entity_id: str) -> list[ChannelMessage]:
        """Get all unacknowledged messages for an entity."""
        inbox = self._inbox_path(entity_id)
        messages = []

        for msg_file in inbox.glob("*.json"):
            try:
                data = json.loads(msg_file.read_text(encoding="utf-8"))
                msg = ChannelMessage.from_dict(data)

                # Only return unacknowledged messages that haven't expired
                if not msg.acknowledged:
                    if msg.expires_at is None or msg.expires_at > datetime.utcnow():
                        messages.append(msg)
            except Exception:
                continue

        # Sort by priority (emergency first) then by time
        priority_order = {"emergency": 0, "urgent": 1, "normal": 2}
        messages.sort(key=lambda m: (priority_order.get(m.priority, 2), m.created_at))

        return messages

    def acknowledge(self, message_id: str, entity_id: str) -> bool:
        """Mark a message as acknowledged."""
        inbox = self._inbox_path(entity_id)
        msg_file = inbox / f"{message_id}.json"

        if not msg_file.exists():
            return False

        try:
            data = json.loads(msg_file.read_text(encoding="utf-8"))
            data["acknowledged"] = True
            data["acknowledged_at"] = datetime.utcnow().isoformat() + "Z"
            msg_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return True
        except Exception:
            return False

    def get_message(self, message_id: str, entity_id: str) -> Optional[ChannelMessage]:
        """Get a specific message."""
        inbox = self._inbox_path(entity_id)
        msg_file = inbox / f"{message_id}.json"

        if not msg_file.exists():
            return None

        try:
            data = json.loads(msg_file.read_text(encoding="utf-8"))
            return ChannelMessage.from_dict(data)
        except Exception:
            return None


class WorkspaceChannel(Channel):
    """Channel for direct delivery to active workspaces.

    This is for real-time communication with active agents.
    Messages are held in memory and delivered when polled.
    Guarantees: fast, real-time, but not persistent.
    """

    name = "workspace"

    def __init__(self):
        # In-memory message queues per workspace
        self._queues: dict[str, list[ChannelMessage]] = {}

    def send(self, message: ChannelMessage, workspace_id: str = None) -> bool:
        """Queue message for workspace delivery."""
        # Use workspace_id from message metadata or parameter
        ws_id = workspace_id or message.to_entity

        if ws_id not in self._queues:
            self._queues[ws_id] = []

        message.delivered = True
        message.delivered_at = datetime.utcnow()
        self._queues[ws_id].append(message)
        return True

    def receive(self, workspace_id: str) -> list[ChannelMessage]:
        """Get and clear pending messages for a workspace."""
        messages = self._queues.get(workspace_id, [])
        self._queues[workspace_id] = []
        return messages

    def acknowledge(self, message_id: str) -> bool:
        """Workspace messages are auto-acknowledged on receive."""
        return True


class ExternalChannel(Channel):
    """Channel for external notifications (email, webhook, etc.).

    Used for reaching humans and systems outside the model.
    Guarantees: best-effort, may have delays.
    """

    name = "external"

    def __init__(self, config: dict = None):
        self.config = config or {}
        # Store pending external messages for manual processing
        self._pending: list[ChannelMessage] = []

    def send(self, message: ChannelMessage) -> bool:
        """Queue message for external delivery.

        In a full implementation, this would:
        - Send email via SMTP
        - POST to webhook
        - Send to Slack/Discord
        - etc.

        For now, we just queue it for manual inspection.
        """
        self._pending.append(message)

        # Log for visibility
        print(f"[EXTERNAL] Message queued for {message.to_entity}: {message.subject}")

        # TODO: Implement actual external delivery
        # if self.config.get("email"):
        #     self._send_email(message)
        # if self.config.get("webhook"):
        #     self._send_webhook(message)

        return True

    def receive(self, entity_id: str) -> list[ChannelMessage]:
        """External channels are push-only, no receive."""
        return []

    def acknowledge(self, message_id: str) -> bool:
        """Mark external message as acknowledged."""
        for msg in self._pending:
            if msg.id == message_id:
                msg.acknowledged = True
                msg.acknowledged_at = datetime.utcnow()
                return True
        return False

    def get_pending(self) -> list[ChannelMessage]:
        """Get all pending external messages (for debugging/admin)."""
        return [m for m in self._pending if not m.acknowledged]
