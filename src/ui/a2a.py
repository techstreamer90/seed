#!/usr/bin/env python3
"""
A2A - Agent-to-Agent coordination.

Transient communication for spawn coordination, handshakes, etc.
NOT for meaningful discussions (use chat.py for that).

Usage:
    from src.ui.a2a import a2a

    # Spawnie adds agent to queue
    a2a.queue_agent("agent-001")

    # Spawnie wakes an agent for a task
    a2a.wake("agent-001", "reality-seed-ui", "Handle viz request")

    # Agent acknowledges
    a2a.ack("agent-001", ready=True)
    a2a.ack("agent-001", ready=False, question="What does X mean?")

    # Spawnie answers
    a2a.answer("agent-001", "X means Y")

    # Check handshake status
    status = a2a.handshake_status("agent-001")
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

A2A_PATH = Path(__file__).parent.parent.parent / ".state" / "a2a.json"


class A2ACoordinator:
    """Agent-to-Agent coordination for spawning."""

    def __init__(self, path: Optional[Path] = None):
        self.path = path or A2A_PATH
        self._ensure_exists()

    def _ensure_exists(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({
                "description": "Agent-to-Agent coordination. Transient.",
                "spawn_queue": [],
                "active_handshakes": {},
                "updated_at": datetime.now().isoformat()
            })

    def _read(self) -> Dict[str, Any]:
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: Dict[str, Any]) -> None:
        data["updated_at"] = datetime.now().isoformat()
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    # === Queue Management ===

    def queue_agent(self, agent_id: str) -> str:
        """Add an agent to the spawn queue (sleeping, ready to be woken)."""
        data = self._read()

        # Check not already queued
        for a in data["spawn_queue"]:
            if a["agent_id"] == agent_id:
                return f"{agent_id} already in queue"

        data["spawn_queue"].append({
            "agent_id": agent_id,
            "status": "sleeping",
            "queued_at": datetime.now().isoformat()
        })
        self._write(data)
        return f"Queued {agent_id}"

    def get_queue(self) -> List[Dict]:
        """Get the current spawn queue."""
        return self._read().get("spawn_queue", [])

    def next_available(self) -> Optional[str]:
        """Get next sleeping agent from queue."""
        for a in self._read().get("spawn_queue", []):
            if a["status"] == "sleeping":
                return a["agent_id"]
        return None

    # === Wake/Handshake ===

    def wake(self, agent_id: str, node_id: str, task: str) -> str:
        """
        Wake an agent and assign it to a node.

        Args:
            agent_id: Agent to wake
            node_id: Node to assign to
            task: What to do
        """
        data = self._read()

        # Update queue status
        for a in data["spawn_queue"]:
            if a["agent_id"] == agent_id:
                a["status"] = "waking"
                break

        # Create handshake
        data["active_handshakes"][agent_id] = {
            "node_id": node_id,
            "task": task,
            "status": "waiting_ack",
            "woken_at": datetime.now().isoformat(),
            "messages": [
                {
                    "from": "spawnie",
                    "text": f"Wake up! You're assigned to {node_id}. Task: {task}",
                    "at": datetime.now().isoformat()
                }
            ]
        }

        self._write(data)
        return f"Woke {agent_id} for {node_id}"

    def ack(self, agent_id: str, ready: bool = True, question: str = None) -> str:
        """
        Agent acknowledges wake-up.

        Args:
            agent_id: Agent responding
            ready: True if ready to work, False if has questions
            question: Optional question if not ready
        """
        data = self._read()

        if agent_id not in data["active_handshakes"]:
            return f"No active handshake for {agent_id}"

        hs = data["active_handshakes"][agent_id]

        if ready:
            hs["status"] = "ready"
            hs["messages"].append({
                "from": agent_id,
                "text": "Ready to work",
                "at": datetime.now().isoformat()
            })

            # Move from queue to active
            data["spawn_queue"] = [a for a in data["spawn_queue"] if a["agent_id"] != agent_id]

        else:
            hs["status"] = "questioning"
            hs["messages"].append({
                "from": agent_id,
                "text": question or "I have a question",
                "at": datetime.now().isoformat()
            })

        self._write(data)
        return f"{agent_id} {'ready' if ready else 'has questions'}"

    def answer(self, agent_id: str, answer: str) -> str:
        """Spawnie answers an agent's question."""
        data = self._read()

        if agent_id not in data["active_handshakes"]:
            return f"No active handshake for {agent_id}"

        hs = data["active_handshakes"][agent_id]
        hs["status"] = "waiting_ack"
        hs["messages"].append({
            "from": "spawnie",
            "text": answer,
            "at": datetime.now().isoformat()
        })

        self._write(data)
        return f"Answered {agent_id}"

    def handshake_status(self, agent_id: str) -> Optional[Dict]:
        """Get handshake status for an agent."""
        return self._read().get("active_handshakes", {}).get(agent_id)

    def complete_handshake(self, agent_id: str) -> str:
        """Mark handshake complete, agent is working."""
        data = self._read()

        if agent_id in data["active_handshakes"]:
            hs = data["active_handshakes"][agent_id]
            hs["status"] = "complete"
            hs["completed_at"] = datetime.now().isoformat()

        self._write(data)
        return f"Handshake complete for {agent_id}"

    def release(self, agent_id: str) -> str:
        """Release an agent back to queue (task done or cancelled)."""
        data = self._read()

        # Remove from handshakes
        if agent_id in data["active_handshakes"]:
            del data["active_handshakes"][agent_id]

        # Add back to queue as sleeping
        data["spawn_queue"].append({
            "agent_id": agent_id,
            "status": "sleeping",
            "queued_at": datetime.now().isoformat()
        })

        self._write(data)
        return f"Released {agent_id} back to queue"

    def clear(self) -> str:
        """Clear all state (for testing)."""
        self._write({
            "description": "Agent-to-Agent coordination. Transient.",
            "spawn_queue": [],
            "active_handshakes": {},
        })
        return "Cleared A2A state"


# Global instance
a2a = A2ACoordinator()


# CLI
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("A2A Coordinator")
        print("  queue <agent_id>     - Add to queue")
        print("  list                 - Show queue")
        print("  wake <agent> <node> <task> - Wake agent")
        print("  status <agent>       - Handshake status")
        print("  clear                - Clear all")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "queue" and len(sys.argv) >= 3:
        print(a2a.queue_agent(sys.argv[2]))
    elif cmd == "list":
        for a in a2a.get_queue():
            print(f"  {a['agent_id']}: {a['status']}")
    elif cmd == "wake" and len(sys.argv) >= 5:
        print(a2a.wake(sys.argv[2], sys.argv[3], " ".join(sys.argv[4:])))
    elif cmd == "status" and len(sys.argv) >= 3:
        s = a2a.handshake_status(sys.argv[2])
        print(json.dumps(s, indent=2) if s else "No handshake")
    elif cmd == "clear":
        print(a2a.clear())
