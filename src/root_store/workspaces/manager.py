"""Workspace Manager - coordinates workspaces and canonical store.

The manager handles:
- Creating/destroying workspaces
- Coordinating commits (with conflict detection)
- Emitting events for workspace lifecycle
- Enforcing workspace policies
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional, Callable, Any
from pathlib import Path
import json
import hashlib

from .workspace import Workspace, WorkspaceStatus, NodeSnapshot
from ..entities import EntityRegistry, SubscriptionManager, EventTypes, Event


class ConflictError(Exception):
    """Raised when a commit would conflict with canonical store."""

    def __init__(self, node_id: str, workspace_version: str, canonical_version: str):
        self.node_id = node_id
        self.workspace_version = workspace_version
        self.canonical_version = canonical_version
        super().__init__(
            f"Conflict on node {node_id}: workspace has {workspace_version}, "
            f"canonical has {canonical_version}"
        )


class WorkspaceManager:
    """Manages workspaces and their interaction with the canonical store."""

    def __init__(
        self,
        workspaces_dir: Path,
        registry: EntityRegistry,
        subscriptions: SubscriptionManager = None,
        get_canonical_node: Callable[[str], Optional[dict]] = None,
        get_canonical_version: Callable[[str], Optional[str]] = None,
        write_canonical_node: Callable[[str, dict], bool] = None,
        delete_canonical_node: Callable[[str], bool] = None,
    ):
        """Initialize the workspace manager.

        Args:
            workspaces_dir: Where to store workspace state
            registry: Entity registry for tracking active workspaces
            subscriptions: For emitting workspace events
            get_canonical_node: Function to retrieve a node from canonical store
            get_canonical_version: Function to get node version/hash from canonical
            write_canonical_node: Function to write a node to canonical store
            delete_canonical_node: Function to delete a node from canonical store
        """
        self.workspaces_dir = workspaces_dir
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)
        self.registry = registry
        self.subscriptions = subscriptions

        # Canonical store interface (to be connected to actual store)
        self._get_canonical_node = get_canonical_node
        self._get_canonical_version = get_canonical_version
        self._write_canonical_node = write_canonical_node
        self._delete_canonical_node = delete_canonical_node

        # Active workspaces
        self._workspaces: dict[str, Workspace] = {}
        self._load_workspaces()

    def _load_workspaces(self) -> None:
        """Load active workspaces from storage."""
        for ws_file in self.workspaces_dir.glob("*.json"):
            try:
                data = json.loads(ws_file.read_text(encoding="utf-8"))
                ws = Workspace.from_dict(data)
                if ws.status == WorkspaceStatus.ACTIVE:
                    self._workspaces[ws.id] = ws
            except Exception:
                continue

    def _save_workspace(self, workspace: Workspace) -> None:
        """Persist workspace to storage."""
        ws_file = self.workspaces_dir / f"{workspace.id}.json"
        ws_file.write_text(json.dumps(workspace.to_dict(), indent=2), encoding="utf-8")

    def create(
        self,
        owner_id: str,
        purpose: str = "",
        parent_id: str = None,
    ) -> Workspace:
        """Create a new workspace for an agent."""
        workspace = Workspace(
            owner_id=owner_id,
            purpose=purpose,
            parent_id=parent_id,
        )

        self._workspaces[workspace.id] = workspace
        self._save_workspace(workspace)

        # Update entity registry
        self.registry.activate_node(owner_id, workspace.id)

        # Emit event
        if self.subscriptions:
            self.subscriptions.emit(Event(
                type=EventTypes.WORKSPACE_CREATED,
                source=owner_id,
                subject=workspace.id,
                data={"purpose": purpose, "parent_id": parent_id},
            ))

        return workspace

    def get(self, workspace_id: str) -> Optional[Workspace]:
        """Get a workspace by ID."""
        return self._workspaces.get(workspace_id)

    def get_for_owner(self, owner_id: str) -> list[Workspace]:
        """Get all active workspaces for an owner."""
        return [
            ws for ws in self._workspaces.values()
            if ws.owner_id == owner_id and ws.status == WorkspaceStatus.ACTIVE
        ]

    def pull(self, workspace_id: str, node_id: str) -> Optional[NodeSnapshot]:
        """Pull a node from canonical store into a workspace."""
        workspace = self.get(workspace_id)
        if not workspace or workspace.status != WorkspaceStatus.ACTIVE:
            return None

        # Get from canonical
        if not self._get_canonical_node:
            return None

        node_data = self._get_canonical_node(node_id)
        if node_data is None:
            return None

        version = None
        if self._get_canonical_version:
            version = self._get_canonical_version(node_id)

        snapshot = workspace.pull_node(node_id, node_data, version)
        self._save_workspace(workspace)
        return snapshot

    def commit(
        self,
        workspace_id: str,
        message: str = "",
        committer: str = None,
    ) -> dict:
        """Commit workspace changes to canonical store.

        Returns a summary of what was committed.
        Raises ConflictError if there are conflicts.
        """
        workspace = self.get(workspace_id)
        if not workspace or workspace.status != WorkspaceStatus.ACTIVE:
            return {"error": "Workspace not active"}

        if not workspace.has_changes():
            return {"error": "No changes to commit"}

        committer = committer or workspace.owner_id
        result = {
            "workspace_id": workspace_id,
            "committer": committer,
            "message": message,
            "committed_at": datetime.utcnow().isoformat() + "Z",
            "created": [],
            "modified": [],
            "deleted": [],
            "conflicts": [],
        }

        # Check for conflicts first
        if self._get_canonical_version:
            for node_id, snapshot in workspace.nodes.items():
                if snapshot.modified and node_id not in workspace.deleted_nodes:
                    current_version = self._get_canonical_version(node_id)
                    if current_version and current_version != snapshot.pulled_version:
                        result["conflicts"].append({
                            "node_id": node_id,
                            "workspace_version": snapshot.pulled_version,
                            "canonical_version": current_version,
                        })

        if result["conflicts"]:
            workspace.status = WorkspaceStatus.CONFLICTED
            self._save_workspace(workspace)
            return result

        # Apply changes to canonical
        if self._write_canonical_node:
            # New nodes
            for node_id, node_data in workspace.new_nodes.items():
                if self._write_canonical_node(node_id, node_data):
                    result["created"].append(node_id)

            # Modified nodes
            for node_id, snapshot in workspace.nodes.items():
                if snapshot.modified and node_id not in workspace.deleted_nodes:
                    if self._write_canonical_node(node_id, snapshot.data):
                        result["modified"].append(node_id)

        # Delete nodes
        if self._delete_canonical_node:
            for node_id in workspace.deleted_nodes:
                if self._delete_canonical_node(node_id):
                    result["deleted"].append(node_id)

        # Mark workspace as committed
        workspace.status = WorkspaceStatus.COMMITTED
        workspace._log_activity("commit", {
            "message": message,
            "committer": committer,
            "result": result,
        })
        self._save_workspace(workspace)

        # Remove from active workspaces
        del self._workspaces[workspace_id]

        # Emit events
        if self.subscriptions:
            self.subscriptions.emit(Event(
                type=EventTypes.WORKSPACE_COMMITTED,
                source=committer,
                subject=workspace_id,
                data=result,
            ))

            # Emit node modified events for each changed node
            for node_id in result["modified"]:
                self.subscriptions.emit_node_modified(
                    node_id=node_id,
                    modifier=committer,
                    changes={"committed_from": workspace_id},
                )

        return result

    def discard(self, workspace_id: str, reason: str = "") -> bool:
        """Discard a workspace and all its changes."""
        workspace = self.get(workspace_id)
        if not workspace:
            return False

        workspace.status = WorkspaceStatus.DISCARDED
        workspace._log_activity("discard", {"reason": reason})
        self._save_workspace(workspace)

        del self._workspaces[workspace_id]

        # Emit event
        if self.subscriptions:
            self.subscriptions.emit(Event(
                type=EventTypes.WORKSPACE_DISCARDED,
                source=workspace.owner_id,
                subject=workspace_id,
                data={"reason": reason},
            ))

        return True

    def fork(
        self,
        workspace_id: str,
        new_owner_id: str,
        purpose: str = "",
    ) -> Optional[Workspace]:
        """Create a child workspace from an existing one.

        Useful for trying out alternatives without losing work.
        """
        parent = self.get(workspace_id)
        if not parent or parent.status != WorkspaceStatus.ACTIVE:
            return None

        child = self.create(
            owner_id=new_owner_id,
            purpose=purpose or f"Fork of {parent.purpose}",
            parent_id=workspace_id,
        )

        # Copy all nodes to child
        for node_id, snapshot in parent.nodes.items():
            child.nodes[node_id] = NodeSnapshot(
                node_id=node_id,
                data=snapshot.data.copy(),
                pulled_at=snapshot.pulled_at,
                pulled_version=snapshot.pulled_version,
                modified=snapshot.modified,
                modifications=snapshot.modifications.copy(),
            )

        child.new_nodes = parent.new_nodes.copy()
        child.deleted_nodes = parent.deleted_nodes.copy()

        self._save_workspace(child)
        return child

    def list_active(self) -> list[Workspace]:
        """List all active workspaces."""
        return list(self._workspaces.values())

    def cleanup_stale(self, max_age: timedelta = timedelta(hours=24)) -> int:
        """Clean up stale workspaces that have been inactive too long."""
        cutoff = datetime.utcnow() - max_age
        cleaned = 0

        for ws_id, workspace in list(self._workspaces.items()):
            if workspace.last_activity < cutoff:
                self.discard(ws_id, reason="Stale workspace cleanup")
                cleaned += 1

        return cleaned

    def get_stats(self) -> dict:
        """Get statistics about workspaces."""
        total_nodes = sum(
            len(ws.nodes) + len(ws.new_nodes)
            for ws in self._workspaces.values()
        )
        total_changes = sum(
            1 for ws in self._workspaces.values()
            for s in ws.nodes.values() if s.modified
        )

        return {
            "active_workspaces": len(self._workspaces),
            "total_pulled_nodes": total_nodes,
            "total_modifications": total_changes,
            "workspaces": [
                {
                    "id": ws.id,
                    "owner": ws.owner_id,
                    "purpose": ws.purpose,
                    "nodes": len(ws.nodes),
                    "new_nodes": len(ws.new_nodes),
                    "modified": sum(1 for s in ws.nodes.values() if s.modified),
                    "last_activity": ws.last_activity.isoformat() + "Z",
                }
                for ws in self._workspaces.values()
            ],
        }
