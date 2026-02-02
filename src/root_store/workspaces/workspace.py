"""Workspace - an isolated environment for agent work.

Each workspace has:
- An owner (the agent working in it)
- A set of pulled nodes (copied from canonical)
- Local modifications (changes not yet committed)
- A session history (what happened here)

Workspaces are temporary. They exist while work is being done
and are cleaned up after commit or rollback.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pathlib import Path
import json
import uuid
import copy


class WorkspaceStatus(Enum):
    """Status of a workspace."""
    ACTIVE = "active"       # Work in progress
    COMMITTED = "committed" # Changes pushed to canonical
    DISCARDED = "discarded" # Changes thrown away
    CONFLICTED = "conflicted" # Merge conflict detected


@dataclass
class NodeSnapshot:
    """A snapshot of a node at a point in time."""

    node_id: str
    data: dict                          # Full node data
    pulled_at: datetime = field(default_factory=datetime.utcnow)
    pulled_version: Optional[str] = None  # Version/hash when pulled
    modified: bool = False
    modifications: list[dict] = field(default_factory=list)  # Change history

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "data": self.data,
            "pulled_at": self.pulled_at.isoformat() + "Z",
            "pulled_version": self.pulled_version,
            "modified": self.modified,
            "modifications": self.modifications,
        }

    @classmethod
    def from_dict(cls, data: dict) -> NodeSnapshot:
        return cls(
            node_id=data["node_id"],
            data=data["data"],
            pulled_at=datetime.fromisoformat(data["pulled_at"].rstrip("Z")),
            pulled_version=data.get("pulled_version"),
            modified=data.get("modified", False),
            modifications=data.get("modifications", []),
        )


@dataclass
class Workspace:
    """An isolated workspace for an agent."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    owner_id: str = ""                  # Entity that owns this workspace
    purpose: str = ""                   # What is this workspace for?
    status: WorkspaceStatus = WorkspaceStatus.ACTIVE

    # Pulled nodes
    nodes: dict[str, NodeSnapshot] = field(default_factory=dict)

    # New nodes created in this workspace (not yet in canonical)
    new_nodes: dict[str, dict] = field(default_factory=dict)

    # Deleted nodes (marked for deletion on commit)
    deleted_nodes: set[str] = field(default_factory=set)

    # Session tracking
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    activity_log: list[dict] = field(default_factory=list)

    # Parent workspace (for nested workspaces)
    parent_id: Optional[str] = None

    def pull_node(self, node_id: str, node_data: dict, version: str = None) -> NodeSnapshot:
        """Pull a node from canonical store into this workspace."""
        # Deep copy to ensure isolation
        snapshot = NodeSnapshot(
            node_id=node_id,
            data=copy.deepcopy(node_data),
            pulled_version=version,
        )
        self.nodes[node_id] = snapshot
        self._log_activity("pull", {"node_id": node_id, "version": version})
        return snapshot

    def get_node(self, node_id: str) -> Optional[dict]:
        """Get a node's current data in this workspace."""
        # Check new nodes first
        if node_id in self.new_nodes:
            return self.new_nodes[node_id]

        # Then pulled nodes
        if node_id in self.nodes:
            return self.nodes[node_id].data

        return None

    def modify_node(self, node_id: str, changes: dict, modifier: str = None) -> bool:
        """Apply changes to a node in this workspace."""
        if node_id in self.deleted_nodes:
            return False

        # Handle new nodes
        if node_id in self.new_nodes:
            self._apply_changes(self.new_nodes[node_id], changes)
            self._log_activity("modify", {
                "node_id": node_id,
                "changes": changes,
                "modifier": modifier,
            })
            return True

        # Handle pulled nodes
        if node_id in self.nodes:
            snapshot = self.nodes[node_id]
            self._apply_changes(snapshot.data, changes)
            snapshot.modified = True
            snapshot.modifications.append({
                "changes": changes,
                "modifier": modifier,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })
            self._log_activity("modify", {
                "node_id": node_id,
                "changes": changes,
                "modifier": modifier,
            })
            return True

        return False

    def _apply_changes(self, data: dict, changes: dict) -> None:
        """Apply changes to a data dict."""
        for key, value in changes.items():
            if value is None:
                # None means delete the key
                data.pop(key, None)
            elif isinstance(value, dict) and isinstance(data.get(key), dict):
                # Nested dict - merge recursively
                self._apply_changes(data[key], value)
            else:
                data[key] = value

    def create_node(self, node_id: str, node_data: dict) -> bool:
        """Create a new node in this workspace."""
        if node_id in self.nodes or node_id in self.new_nodes:
            return False  # Already exists

        self.new_nodes[node_id] = copy.deepcopy(node_data)
        self._log_activity("create", {"node_id": node_id})
        return True

    def delete_node(self, node_id: str) -> bool:
        """Mark a node for deletion."""
        if node_id in self.new_nodes:
            # Just remove from new_nodes
            del self.new_nodes[node_id]
            self._log_activity("delete_new", {"node_id": node_id})
            return True

        if node_id in self.nodes:
            self.deleted_nodes.add(node_id)
            self._log_activity("delete", {"node_id": node_id})
            return True

        return False

    def get_changes(self) -> dict:
        """Get a summary of all changes in this workspace."""
        modified = []
        for node_id, snapshot in self.nodes.items():
            if snapshot.modified and node_id not in self.deleted_nodes:
                modified.append({
                    "node_id": node_id,
                    "original_version": snapshot.pulled_version,
                    "modifications": snapshot.modifications,
                })

        return {
            "workspace_id": self.id,
            "owner": self.owner_id,
            "created": list(self.new_nodes.keys()),
            "modified": modified,
            "deleted": list(self.deleted_nodes),
        }

    def has_changes(self) -> bool:
        """Check if workspace has any uncommitted changes."""
        if self.new_nodes or self.deleted_nodes:
            return True
        for snapshot in self.nodes.values():
            if snapshot.modified:
                return True
        return False

    def _log_activity(self, action: str, details: dict) -> None:
        """Log an activity in the workspace."""
        self.last_activity = datetime.utcnow()
        self.activity_log.append({
            "action": action,
            "details": details,
            "timestamp": self.last_activity.isoformat() + "Z",
        })

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "purpose": self.purpose,
            "status": self.status.value,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "new_nodes": self.new_nodes,
            "deleted_nodes": list(self.deleted_nodes),
            "created_at": self.created_at.isoformat() + "Z",
            "last_activity": self.last_activity.isoformat() + "Z",
            "activity_log": self.activity_log,
            "parent_id": self.parent_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Workspace:
        ws = cls(
            id=data["id"],
            owner_id=data["owner_id"],
            purpose=data.get("purpose", ""),
            status=WorkspaceStatus(data["status"]),
            parent_id=data.get("parent_id"),
        )
        ws.nodes = {k: NodeSnapshot.from_dict(v) for k, v in data.get("nodes", {}).items()}
        ws.new_nodes = data.get("new_nodes", {})
        ws.deleted_nodes = set(data.get("deleted_nodes", []))
        ws.created_at = datetime.fromisoformat(data["created_at"].rstrip("Z"))
        ws.last_activity = datetime.fromisoformat(data["last_activity"].rstrip("Z"))
        ws.activity_log = data.get("activity_log", [])
        return ws
