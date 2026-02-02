#!/usr/bin/env python3
"""
Broadcast - System-wide communication.

The model is the communication fabric - everything flows through it.

All agents and users can see broadcast messages. Any agent can respond.
This is the global conversation space for the living system.

Usage:
    from src.ui.broadcast import broadcast

    # Send a message (visible to everyone)
    broadcast.send("human", "Show me the Seed architecture")
    broadcast.send("schauspieler", "Creating that view now")

    # Read messages
    messages = broadcast.read(limit=20)

    # Read only new messages since last check
    new_msgs = broadcast.read_new("schauspieler")
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

BROADCAST_PATH = Path(__file__).parent.parent.parent / ".state" / "broadcast.json"


class BroadcastChannel:
    """System-wide broadcast communication."""

    def __init__(self, path: Optional[Path] = None):
        self.path = path or BROADCAST_PATH
        self._ensure_exists()

    def _ensure_exists(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({
                "description": "System-wide broadcast. Everyone can see and respond.",
                "messages": [],
                "last_read": {},
                "created_at": datetime.now().isoformat()
            })

    def _read(self) -> Dict[str, Any]:
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: Dict[str, Any]) -> None:
        data["updated_at"] = datetime.now().isoformat()
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def send(self, sender: str, text: str) -> str:
        """
        Broadcast a message to everyone.

        Args:
            sender: Who is sending (human, schauspieler, spawnie, control, etc.)
            text: Message text

        Returns:
            Confirmation message
        """
        data = self._read()

        message = {
            "from": sender,
            "text": text,
            "at": datetime.now().isoformat()
        }

        data["messages"].append(message)
        self._write(data)

        return f"Broadcast from {sender}: {text[:50]}..."

    def read(self, limit: int = 50) -> List[Dict]:
        """
        Read broadcast messages.

        Args:
            limit: Max messages to return (most recent)

        Returns:
            List of messages
        """
        data = self._read()
        messages = data.get("messages", [])
        return messages[-limit:]

    def read_new(self, reader_id: str) -> List[Dict]:
        """
        Read only new messages since last read.

        Args:
            reader_id: ID of the reader (to track last read)

        Returns:
            List of new messages
        """
        data = self._read()
        messages = data.get("messages", [])
        last_read = data.get("last_read", {}).get(reader_id)

        # Filter to new messages
        if last_read:
            new_messages = [m for m in messages if m.get("at", "") > last_read]
        else:
            new_messages = messages

        # Update last_read
        if messages:
            if "last_read" not in data:
                data["last_read"] = {}
            data["last_read"][reader_id] = datetime.now().isoformat()
            self._write(data)

        return new_messages

    def clear(self) -> str:
        """Clear all broadcast messages."""
        self._write({
            "description": "System-wide broadcast. Everyone can see and respond.",
            "messages": [],
            "last_read": {},
        })
        return "Cleared broadcast"


# Global instance
broadcast = BroadcastChannel()


# CLI
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Broadcast System")
        print("  send <sender> <message>  - Broadcast a message")
        print("  read                     - Read messages")
        print("  clear                    - Clear all messages")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "send" and len(sys.argv) >= 4:
        sender = sys.argv[2]
        msg = " ".join(sys.argv[3:])
        print(broadcast.send(sender, msg))
    elif cmd == "read":
        for m in broadcast.read():
            print(f"[{m.get('from')}] {m.get('text')}")
    elif cmd == "clear":
        print(broadcast.clear())
