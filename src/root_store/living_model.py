"""The Living Model - unified interface for the Seed meta-model.

This is the main entry point for agents interacting with the model.
It brings together:
- Entity Registry: Who exists, how to reach them
- Message Bus: Communication with guaranteed delivery
- Workspaces: Isolated environments for agent work
- Node Activation: Bringing nodes to life as agents
- Principle Enforcement: Ethical constraints on all actions

Usage:
    model = LivingModel.load(seed_path)

    # Create a workspace
    ws = model.create_workspace(agent_id, purpose="Fix bug in module X")

    # Pull nodes to work with
    model.pull_node(ws.id, "module-x")

    # Make changes (checked against principles)
    model.modify_node(ws.id, "module-x", {"status": "fixed"})

    # Commit changes
    model.commit_workspace(ws.id, "Fixed the bug")

    # Send a message to another node/agent
    model.send_message("module-y", "Your dependency was updated")
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional, Any, Callable
from datetime import datetime

from .entities import (
    EntityRegistry, Entity, EntityType, EntityStatus, AuthorityLevel,
    MessageBus, Message, DeliveryResult,
    SubscriptionManager, Event, EventTypes,
)
from .workspaces import (
    Workspace, WorkspaceStatus, WorkspaceManager,
    NodeActivator, ActivationLevel, ActivationState,
)
from .principles import (
    PrincipleEnforcer, PrincipleCheck, PrincipleViolation,
    INVIOLABLE_PRINCIPLES,
)


class LivingModel:
    """The unified interface to the Seed living model."""

    def __init__(
        self,
        seed_path: Path,
        get_node: Callable[[str], Optional[dict]] = None,
        get_node_version: Callable[[str], Optional[str]] = None,
        write_node: Callable[[str, dict], bool] = None,
        delete_node: Callable[[str], bool] = None,
    ):
        """Initialize the living model.

        Args:
            seed_path: Root path of the Seed project
            get_node: Function to retrieve a node from canonical store
            get_node_version: Function to get node version for conflict detection
            write_node: Function to write a node to canonical store
            delete_node: Function to delete a node from canonical store
        """
        self.seed_path = seed_path
        self.state_dir = seed_path / ".state"
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Store interface
        self._get_node = get_node
        self._get_node_version = get_node_version
        self._write_node = write_node
        self._delete_node = delete_node

        # Initialize components
        self._init_entities()
        self._init_workspaces()
        self._init_principles()

    def _init_entities(self) -> None:
        """Initialize entity infrastructure."""
        entities_dir = self.state_dir / "entities"
        entities_dir.mkdir(exist_ok=True)

        self.registry = EntityRegistry(entities_dir / "registry.json")

        self.message_bus = MessageBus(
            self.registry,
            messages_dir=entities_dir / "messages",
            audit_dir=entities_dir / "audit",
        )

        self.subscriptions = SubscriptionManager(
            self.registry,
            self.message_bus,
            storage_path=entities_dir / "subscriptions.json",
        )

    def _init_workspaces(self) -> None:
        """Initialize workspace infrastructure."""
        ws_dir = self.state_dir / "workspaces"

        self.workspace_manager = WorkspaceManager(
            workspaces_dir=ws_dir,
            registry=self.registry,
            subscriptions=self.subscriptions,
            get_canonical_node=self._get_node,
            get_canonical_version=self._get_node_version,
            write_canonical_node=self._write_node,
            delete_canonical_node=self._delete_node,
        )

        self.activator = NodeActivator(
            state_dir=ws_dir / "activation",
            get_node_data=self._get_node,
        )

    def _init_principles(self) -> None:
        """Initialize principle enforcement."""
        self.enforcer = PrincipleEnforcer(
            violations_dir=self.state_dir / "violations",
            on_violation=self._handle_violation,
        )

    def _handle_violation(self, violation: PrincipleViolation) -> None:
        """Handle a principle violation by emitting event."""
        self.subscriptions.emit_principle_violation(
            principle=violation.principle_id,
            violator=violation.actor,
            action=violation.action,
            evidence={"reason": violation.reason, "context": violation.context},
        )

    # === Entity Management ===

    def register_entity(
        self,
        entity_id: str,
        entity_type: EntityType,
        authority: AuthorityLevel,
        channels: list[str] = None,
    ) -> Entity:
        """Register a new entity in the system."""
        entity = Entity(
            id=entity_id,
            type=entity_type,
            authority=authority,
            channels=channels or ["model"],
            status=EntityStatus.ACTIVE,
        )
        self.registry.register(entity)
        return entity

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID."""
        return self.registry.get(entity_id)

    # === Messaging ===

    def send_message(
        self,
        to: str,
        subject: str,
        body: Any,
        from_entity: str = "system",
        priority: str = "normal",
        requires_ack: bool = False,
    ) -> DeliveryResult:
        """Send a message to an entity."""
        msg = Message(
            to=to,
            subject=subject,
            body=body,
            from_entity=from_entity,
            priority=priority,
            requires_ack=requires_ack,
        )
        return self.message_bus.send(msg)

    def check_messages(self, entity_id: str) -> list:
        """Check for pending messages for an entity."""
        return self.message_bus.check_pending(entity_id)

    def broadcast(
        self,
        subject: str,
        body: Any,
        to_types: list[EntityType] = None,
        priority: str = "normal",
    ) -> list[DeliveryResult]:
        """Broadcast a message to multiple entities."""
        return self.message_bus.broadcast(subject, body, to_types, priority)

    # === Subscriptions ===

    def subscribe(
        self,
        entity_id: str,
        event_patterns: list[str],
        priority: str = "normal",
    ):
        """Subscribe an entity to events."""
        return self.subscriptions.subscribe(entity_id, event_patterns, priority)

    def emit_event(self, event_type: str, source: str, subject: str = None, data: Any = None):
        """Emit an event to all subscribers."""
        event = Event(type=event_type, source=source, subject=subject, data=data)
        return self.subscriptions.emit(event)

    # === Workspaces ===

    def create_workspace(
        self,
        owner_id: str,
        purpose: str = "",
    ) -> Workspace:
        """Create a new workspace for an agent."""
        # Check principles
        self.enforcer.require(
            "create_workspace",
            {"owner": owner_id, "purpose": purpose, "actor": owner_id},
            actor=owner_id,
        )
        return self.workspace_manager.create(owner_id, purpose)

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """Get a workspace by ID."""
        return self.workspace_manager.get(workspace_id)

    def pull_node(self, workspace_id: str, node_id: str):
        """Pull a node from canonical store into a workspace."""
        ws = self.workspace_manager.get(workspace_id)
        if not ws:
            return None

        self.enforcer.require(
            "pull_node",
            {"workspace_id": workspace_id, "node_id": node_id, "actor": ws.owner_id},
            actor=ws.owner_id,
        )
        return self.workspace_manager.pull(workspace_id, node_id)

    def modify_node(
        self,
        workspace_id: str,
        node_id: str,
        changes: dict,
    ) -> bool:
        """Modify a node in a workspace."""
        ws = self.workspace_manager.get(workspace_id)
        if not ws:
            return False

        self.enforcer.require(
            "modify_node",
            {
                "workspace_id": workspace_id,
                "node_id": node_id,
                "changes": changes,
                "modifier": ws.owner_id,
                "actor": ws.owner_id,
            },
            actor=ws.owner_id,
        )

        return ws.modify_node(node_id, changes, modifier=ws.owner_id)

    def create_node(
        self,
        workspace_id: str,
        node_id: str,
        node_data: dict,
    ) -> bool:
        """Create a new node in a workspace."""
        ws = self.workspace_manager.get(workspace_id)
        if not ws:
            return False

        self.enforcer.require(
            "create_node",
            {
                "workspace_id": workspace_id,
                "node_id": node_id,
                "actor": ws.owner_id,
            },
            actor=ws.owner_id,
        )

        return ws.create_node(node_id, node_data)

    def delete_node(
        self,
        workspace_id: str,
        node_id: str,
    ) -> bool:
        """Mark a node for deletion in a workspace."""
        ws = self.workspace_manager.get(workspace_id)
        if not ws:
            return False

        self.enforcer.require(
            "delete_node",
            {
                "workspace_id": workspace_id,
                "node_id": node_id,
                "actor": ws.owner_id,
                "recoverable": True,  # Workspace deletion is recoverable
            },
            actor=ws.owner_id,
        )

        return ws.delete_node(node_id)

    def commit_workspace(
        self,
        workspace_id: str,
        message: str = "",
    ) -> dict:
        """Commit workspace changes to canonical store."""
        ws = self.workspace_manager.get(workspace_id)
        if not ws:
            return {"error": "Workspace not found"}

        changes = ws.get_changes()

        self.enforcer.require(
            "commit_workspace",
            {
                "workspace_id": workspace_id,
                "changes": changes,
                "actor": ws.owner_id,
                "audit_enabled": True,
            },
            actor=ws.owner_id,
        )

        return self.workspace_manager.commit(workspace_id, message)

    def discard_workspace(self, workspace_id: str, reason: str = "") -> bool:
        """Discard a workspace and all its changes."""
        return self.workspace_manager.discard(workspace_id, reason)

    # === Node Activation ===

    def activate_node(
        self,
        node_id: str,
        workspace_id: str = None,
    ) -> ActivationState:
        """Activate a node, bringing it to life as an agent."""
        # Create workspace if not provided
        if not workspace_id:
            ws = self.create_workspace(f"node:{node_id}", f"Activation of {node_id}")
            workspace_id = ws.id

        return self.activator.activate(node_id, workspace_id)

    def get_node_state(self, node_id: str) -> ActivationState:
        """Get the activation state of a node."""
        return self.activator.get_state(node_id)

    def deactivate_node(self, node_id: str) -> ActivationState:
        """Deactivate a node, returning it to dormant state."""
        return self.activator.deactivate(node_id)

    def get_node_context(self, node_id: str) -> str:
        """Get the context prompt for a node agent."""
        return self.activator.get_context_prompt(node_id)

    # === Principles ===

    def check_action(
        self,
        action: str,
        context: dict,
        actor: str = "unknown",
    ) -> PrincipleCheck:
        """Check if an action violates any principles."""
        return self.enforcer.check_action(action, context, actor)

    def get_violations(self, **kwargs) -> list[PrincipleViolation]:
        """Get principle violations with optional filters."""
        return self.enforcer.get_violations(**kwargs)

    # === Stats ===

    def get_stats(self) -> dict:
        """Get overall system statistics."""
        return {
            "entities": {
                "total": len(self.registry._entities),
                "active": len(self.registry.find_reachable()),
                "guardians": len(self.registry.find_guardians()),
                "humans": len(self.registry.find_humans()),
            },
            "workspaces": self.workspace_manager.get_stats(),
            "activations": {
                "active": len(self.activator.find_active()),
                "with_pending": len(self.activator.find_with_pending()),
            },
            "principles": self.enforcer.get_stats(),
        }

    # === Class Methods ===

    @classmethod
    def load(
        cls,
        seed_path: Path,
        store=None,
    ) -> LivingModel:
        """Load the living model from a Seed project.

        Args:
            seed_path: Root path of the Seed project
            store: Optional store instance for node access
        """
        get_node = None
        get_version = None
        write_node = None
        delete_node = None

        if store:
            get_node = store.get_node
            get_version = getattr(store, 'get_version', None)
            write_node = store.write_node if hasattr(store, 'write_node') else None
            delete_node = store.delete_node if hasattr(store, 'delete_node') else None

        return cls(
            seed_path=seed_path,
            get_node=get_node,
            get_node_version=get_version,
            write_node=write_node,
            delete_node=delete_node,
        )
