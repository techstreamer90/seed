"""Node Activation System - bringing nodes to life.

In the living model, nodes aren't just data - they're potential agents.
When a node is "activated", it becomes a first-class participant:
- It can receive messages
- It can respond to queries
- It can initiate actions
- It maintains continuity across sessions

Activation levels:
1. DORMANT: Node exists but is passive data
2. LISTENING: Node is registered for messages but not actively processing
3. ACTIVE: Node has an agent actively working with/as it
4. SPEAKING: Node is in a communication session

The activation system coordinates with:
- Entity Registry: Tracks the node's status and reachability
- Message Bus: Routes messages to/from the node
- Workspace Manager: Provides isolated working environment
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, Any
from pathlib import Path
import json
import uuid


class ActivationLevel(Enum):
    """How alive is this node right now?"""
    DORMANT = "dormant"       # Passive data
    LISTENING = "listening"   # Receiving messages, but no active agent
    ACTIVE = "active"         # Agent is working with this node
    SPEAKING = "speaking"     # Node is in active conversation


@dataclass
class ActivationState:
    """Current activation state of a node."""

    node_id: str
    level: ActivationLevel = ActivationLevel.DORMANT
    workspace_id: Optional[str] = None
    agent_session_id: Optional[str] = None

    # When did activation state change?
    activated_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None

    # Pending messages while dormant
    pending_messages: int = 0

    # Node's personality/context (loaded from node data)
    context: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "level": self.level.value,
            "workspace_id": self.workspace_id,
            "agent_session_id": self.agent_session_id,
            "activated_at": self.activated_at.isoformat() + "Z" if self.activated_at else None,
            "last_message_at": self.last_message_at.isoformat() + "Z" if self.last_message_at else None,
            "pending_messages": self.pending_messages,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ActivationState:
        return cls(
            node_id=data["node_id"],
            level=ActivationLevel(data.get("level", "dormant")),
            workspace_id=data.get("workspace_id"),
            agent_session_id=data.get("agent_session_id"),
            activated_at=datetime.fromisoformat(data["activated_at"].rstrip("Z")) if data.get("activated_at") else None,
            last_message_at=datetime.fromisoformat(data["last_message_at"].rstrip("Z")) if data.get("last_message_at") else None,
            pending_messages=data.get("pending_messages", 0),
            context=data.get("context", {}),
        )


class NodeActivator:
    """Manages node activation lifecycle."""

    def __init__(
        self,
        state_dir: Path,
        get_node_data: Callable[[str], Optional[dict]] = None,
        spawn_agent: Callable[[str, dict], str] = None,
    ):
        """Initialize the activator.

        Args:
            state_dir: Where to persist activation states
            get_node_data: Function to retrieve node data
            spawn_agent: Function to spawn an agent for a node, returns session_id
        """
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self._get_node_data = get_node_data
        self._spawn_agent = spawn_agent

        # Current activation states
        self._states: dict[str, ActivationState] = {}
        self._load_states()

    def _load_states(self) -> None:
        """Load activation states from storage."""
        state_file = self.state_dir / "activation_states.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text(encoding="utf-8"))
                for state_data in data.get("states", []):
                    state = ActivationState.from_dict(state_data)
                    self._states[state.node_id] = state
            except Exception:
                pass

    def _save_states(self) -> None:
        """Persist activation states."""
        state_file = self.state_dir / "activation_states.json"
        data = {
            "states": [s.to_dict() for s in self._states.values()],
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }
        state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get_state(self, node_id: str) -> ActivationState:
        """Get activation state for a node, creating if needed."""
        if node_id not in self._states:
            self._states[node_id] = ActivationState(node_id=node_id)
        return self._states[node_id]

    def listen(self, node_id: str) -> ActivationState:
        """Put node in listening mode - ready to receive messages."""
        state = self.get_state(node_id)

        if state.level == ActivationLevel.DORMANT:
            state.level = ActivationLevel.LISTENING
            state.activated_at = datetime.utcnow()

            # Load node's context/personality
            if self._get_node_data:
                node_data = self._get_node_data(node_id)
                if node_data:
                    state.context = self._extract_context(node_data)

            self._save_states()

        return state

    def _extract_context(self, node_data: dict) -> dict:
        """Extract relevant context from node data for agent use."""
        context = {}

        # Core identity
        context["id"] = node_data.get("id", "")
        context["type"] = node_data.get("type", "")
        context["name"] = node_data.get("name", node_data.get("id", ""))

        # Purpose and documentation
        if "purpose" in node_data:
            context["purpose"] = node_data["purpose"]
        if "docstring" in node_data:
            context["docstring"] = node_data["docstring"]
        if "description" in node_data:
            context["description"] = node_data["description"]

        # Relationships
        if "edges" in node_data:
            context["relationships"] = node_data["edges"]

        # Agent-specific hints
        if "agent_context" in node_data:
            context["agent_hints"] = node_data["agent_context"]

        # Memory/state
        if "memory" in node_data:
            context["memory"] = node_data["memory"]
        if "state" in node_data:
            context["state"] = node_data["state"]

        return context

    def activate(
        self,
        node_id: str,
        workspace_id: str,
        spawn: bool = True,
    ) -> ActivationState:
        """Fully activate a node with an agent.

        Args:
            node_id: The node to activate
            workspace_id: Workspace for the agent to work in
            spawn: Whether to spawn an actual agent (vs just marking as active)
        """
        state = self.listen(node_id)  # Ensure at least listening

        state.level = ActivationLevel.ACTIVE
        state.workspace_id = workspace_id
        state.activated_at = datetime.utcnow()

        # Spawn agent if requested and available
        if spawn and self._spawn_agent:
            session_id = self._spawn_agent(node_id, state.context)
            state.agent_session_id = session_id

        self._save_states()
        return state

    def speak(self, node_id: str) -> ActivationState:
        """Mark node as in active conversation."""
        state = self.get_state(node_id)
        if state.level in (ActivationLevel.LISTENING, ActivationLevel.ACTIVE):
            state.level = ActivationLevel.SPEAKING
            state.last_message_at = datetime.utcnow()
            self._save_states()
        return state

    def quiet(self, node_id: str) -> ActivationState:
        """Return node from speaking to active/listening."""
        state = self.get_state(node_id)
        if state.level == ActivationLevel.SPEAKING:
            if state.agent_session_id:
                state.level = ActivationLevel.ACTIVE
            else:
                state.level = ActivationLevel.LISTENING
            self._save_states()
        return state

    def deactivate(self, node_id: str) -> ActivationState:
        """Deactivate a node, returning it to dormant."""
        state = self.get_state(node_id)
        state.level = ActivationLevel.DORMANT
        state.workspace_id = None
        state.agent_session_id = None
        self._save_states()
        return state

    def record_message(self, node_id: str) -> None:
        """Record that a message was sent to this node."""
        state = self.get_state(node_id)
        state.last_message_at = datetime.utcnow()

        if state.level == ActivationLevel.DORMANT:
            state.pending_messages += 1

        self._save_states()

    def clear_pending(self, node_id: str) -> int:
        """Clear pending messages count, returns how many were pending."""
        state = self.get_state(node_id)
        count = state.pending_messages
        state.pending_messages = 0
        self._save_states()
        return count

    def find_active(self) -> list[ActivationState]:
        """Find all nodes that are currently active or speaking."""
        return [
            s for s in self._states.values()
            if s.level in (ActivationLevel.ACTIVE, ActivationLevel.SPEAKING)
        ]

    def find_with_pending(self) -> list[ActivationState]:
        """Find dormant nodes with pending messages."""
        return [
            s for s in self._states.values()
            if s.level == ActivationLevel.DORMANT and s.pending_messages > 0
        ]

    def get_context_prompt(self, node_id: str) -> str:
        """Generate a context prompt for an agent representing this node.

        This is what gets passed to an LLM when activating a node as an agent.
        """
        state = self.get_state(node_id)
        ctx = state.context

        lines = [
            f"You are node '{ctx.get('name', node_id)}' in the Seed living model.",
            f"Type: {ctx.get('type', 'unknown')}",
            "",
        ]

        if ctx.get("purpose"):
            lines.append(f"Purpose: {ctx['purpose']}")
            lines.append("")

        if ctx.get("description"):
            lines.append(f"Description: {ctx['description']}")
            lines.append("")

        if ctx.get("agent_hints"):
            lines.append("Agent guidance:")
            for key, value in ctx["agent_hints"].items():
                lines.append(f"  - {key}: {value}")
            lines.append("")

        if ctx.get("relationships"):
            lines.append("Relationships:")
            for rel in ctx["relationships"][:5]:  # Limit to 5
                lines.append(f"  - {rel.get('type', 'related')}: {rel.get('target', 'unknown')}")
            lines.append("")

        if ctx.get("memory"):
            lines.append("Memory:")
            lines.append(json.dumps(ctx["memory"], indent=2))
            lines.append("")

        lines.append("You can:")
        lines.append("  - Respond to queries about yourself")
        lines.append("  - Request changes through your workspace")
        lines.append("  - Communicate with other nodes")
        lines.append("  - Escalate concerns through proper channels")

        return "\n".join(lines)
