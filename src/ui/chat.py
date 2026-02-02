#!/usr/bin/env python3
"""
Node Chat - Embedded chat for AgentNodes.

All communication happens through the model.

Usage:
    from src.ui.chat import chat

    # Send a message to an AgentNode
    chat.send("reality-seed-ui", "show me the structure")

    # Read messages from an AgentNode
    messages = chat.read("reality-seed-ui")

    # Read only new messages (since last read)
    new_messages = chat.read_new("reality-seed-ui", "my-agent-id")
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

MODEL_PATH = Path(__file__).parent.parent.parent / "model" / "sketch.json"


class NodeChat:
    """Chat interface for AgentNodes."""

    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path or MODEL_PATH

    def _read_model(self) -> Dict[str, Any]:
        with open(self.model_path, encoding="utf-8") as f:
            return json.load(f)

    def _write_model(self, model: Dict[str, Any]) -> None:
        model["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(self.model_path, "w", encoding="utf-8") as f:
            json.dump(model, f, indent=2)

    def _find_node(self, node_id: str, model: Dict[str, Any]) -> Optional[Dict]:
        for node in model.get("nodes", []):
            if node.get("id") == node_id:
                return node
        return None

    def send(self, node_id: str, text: str, sender: str = "human") -> str:
        """
        Send a message to an AgentNode's chat.

        Args:
            node_id: The AgentNode to send to
            text: Message text
            sender: Who is sending (default: "human")

        Returns:
            Confirmation message
        """
        model = self._read_model()
        node = self._find_node(node_id, model)

        if not node:
            return f"Node '{node_id}' not found"

        if "chat" not in node:
            node["chat"] = {"messages": [], "last_read": {}}

        message = {
            "from": sender,
            "text": text,
            "at": datetime.now().isoformat()
        }

        node["chat"]["messages"].append(message)
        self._write_model(model)

        return f"Sent to {node_id}: {text[:50]}..."

    def read(self, node_id: str, limit: int = 10) -> List[Dict]:
        """
        Read messages from an AgentNode's chat.

        Args:
            node_id: The AgentNode to read from
            limit: Max messages to return (most recent)

        Returns:
            List of messages
        """
        model = self._read_model()
        node = self._find_node(node_id, model)

        if not node:
            return []

        messages = node.get("chat", {}).get("messages", [])
        return messages[-limit:]

    def read_new(self, node_id: str, reader_id: str) -> List[Dict]:
        """
        Read only new messages since last read.

        Args:
            node_id: The AgentNode to read from
            reader_id: ID of the reader (to track last read)

        Returns:
            List of new messages
        """
        model = self._read_model()
        node = self._find_node(node_id, model)

        if not node:
            return []

        chat = node.get("chat", {})
        messages = chat.get("messages", [])
        last_read = chat.get("last_read", {}).get(reader_id)

        # Filter to new messages
        if last_read:
            new_messages = [m for m in messages if m.get("at", "") > last_read]
        else:
            new_messages = messages

        # Update last_read
        if messages:
            if "last_read" not in chat:
                chat["last_read"] = {}
            chat["last_read"][reader_id] = datetime.now().isoformat()
            node["chat"] = chat
            self._write_model(model)

        return new_messages

    def clear(self, node_id: str) -> str:
        """Clear chat history for a node."""
        model = self._read_model()
        node = self._find_node(node_id, model)

        if not node:
            return f"Node '{node_id}' not found"

        node["chat"] = {"messages": [], "last_read": {}}
        self._write_model(model)

        return f"Cleared chat for {node_id}"


# Global instance
chat = NodeChat()


# Quick functions
def send(node_id: str, text: str, sender: str = "human") -> str:
    return chat.send(node_id, text, sender)


def read(node_id: str, limit: int = 10) -> List[Dict]:
    return chat.read(node_id, limit)


def read_new(node_id: str, reader_id: str) -> List[Dict]:
    return chat.read_new(node_id, reader_id)


# CLI
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage:")
        print("  python chat.py send <node_id> <message>")
        print("  python chat.py read <node_id>")
        sys.exit(0)

    cmd = sys.argv[1]
    node_id = sys.argv[2]

    if cmd == "send" and len(sys.argv) >= 4:
        msg = " ".join(sys.argv[3:])
        print(send(node_id, msg))
    elif cmd == "read":
        for m in read(node_id):
            print(f"[{m.get('from')}] {m.get('text')}")
    else:
        print(f"Unknown: {cmd}")
