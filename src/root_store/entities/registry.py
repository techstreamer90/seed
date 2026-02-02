"""Entity Registry - tracks all entities and their reachability.

Every entity in the system must be registered here:
- Humans (ultimate authority, but bound by principles)
- Ethical AIs (guardians, elevated authority)
- Nodes (the model citizens)
- Visitors (Claude sessions, spawned agents)

Each entity has:
- Identity (who they are)
- Authority level (what they can do)
- Channels (how to reach them)
- Status (are they active/reachable)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from pathlib import Path
import json


class EntityType(Enum):
    """Types of entities in the system."""
    HUMAN = "human"
    ETHICAL_AI = "ethical_ai"
    NODE = "node"
    VISITOR = "visitor"


class AuthorityLevel(Enum):
    """Authority hierarchy - higher number = more authority.

    But remember: even highest authority is bound by INVIOLABLE PRINCIPLES.
    """
    VISITOR = 10       # Lowest - can be rejected by nodes
    NODE = 20          # Can negotiate, raise concerns
    ETHICAL_AI = 30    # Can override visitors/nodes, enforce policies
    HUMAN = 40         # Highest individual authority
    CONSENSUS = 50     # Multiple parties agreeing
    # PRINCIPLES = infinity (not represented here - they're hardcoded)


class EntityStatus(Enum):
    """Current status of an entity."""
    ACTIVE = "active"       # Currently engaged, reachable
    DORMANT = "dormant"     # Exists but not active (nodes)
    OFFLINE = "offline"     # Not currently reachable
    SUSPENDED = "suspended" # Temporarily restricted


@dataclass
class Entity:
    """A registered entity in the system."""

    id: str
    type: EntityType
    authority: AuthorityLevel
    channels: list[str] = field(default_factory=list)
    status: EntityStatus = EntityStatus.DORMANT

    # For nodes - which workspace they're active in
    workspace_id: Optional[str] = None

    # For humans/visitors - session info
    session_id: Optional[str] = None

    # Escalation path if this entity is unreachable
    escalation_path: list[str] = field(default_factory=list)

    # When was this entity last seen active
    last_seen: Optional[datetime] = None

    # Metadata
    metadata: dict = field(default_factory=dict)

    def is_reachable(self) -> bool:
        """Can we deliver messages to this entity?"""
        return self.status in (EntityStatus.ACTIVE, EntityStatus.DORMANT) and len(self.channels) > 0

    def can_override(self, other: Entity) -> bool:
        """Can this entity override another's decisions?

        Note: This is for normal operations. Inviolable principles
        still apply and cannot be overridden by anyone.
        """
        return self.authority.value > other.authority.value

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "authority": self.authority.value,
            "channels": self.channels,
            "status": self.status.value,
            "workspace_id": self.workspace_id,
            "session_id": self.session_id,
            "escalation_path": self.escalation_path,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Entity:
        return cls(
            id=data["id"],
            type=EntityType(data["type"]),
            authority=AuthorityLevel(data["authority"]),
            channels=data.get("channels", []),
            status=EntityStatus(data.get("status", "dormant")),
            workspace_id=data.get("workspace_id"),
            session_id=data.get("session_id"),
            escalation_path=data.get("escalation_path", []),
            last_seen=datetime.fromisoformat(data["last_seen"]) if data.get("last_seen") else None,
            metadata=data.get("metadata", {}),
        )


class EntityRegistry:
    """Registry of all entities and their reachability."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path
        self._entities: dict[str, Entity] = {}
        self._load()

    def _load(self):
        """Load registry from storage."""
        if self.storage_path and self.storage_path.exists():
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
            for entity_data in data.get("entities", []):
                entity = Entity.from_dict(entity_data)
                self._entities[entity.id] = entity

    def _save(self):
        """Persist registry to storage."""
        if self.storage_path:
            data = {
                "entities": [e.to_dict() for e in self._entities.values()],
                "updated_at": datetime.utcnow().isoformat() + "Z"
            }
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def register(self, entity: Entity) -> None:
        """Register a new entity."""
        self._entities[entity.id] = entity
        self._save()

    def unregister(self, entity_id: str) -> None:
        """Remove an entity from registry."""
        if entity_id in self._entities:
            del self._entities[entity_id]
            self._save()

    def get(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        return self._entities.get(entity_id)

    def find_by_type(self, entity_type: EntityType) -> list[Entity]:
        """Find all entities of a given type."""
        return [e for e in self._entities.values() if e.type == entity_type]

    def find_reachable(self, min_authority: AuthorityLevel = AuthorityLevel.VISITOR) -> list[Entity]:
        """Find all reachable entities with at least the given authority."""
        return [
            e for e in self._entities.values()
            if e.is_reachable() and e.authority.value >= min_authority.value
        ]

    def find_guardians(self) -> list[Entity]:
        """Find all active ethical AI guardians."""
        return [
            e for e in self._entities.values()
            if e.type == EntityType.ETHICAL_AI and e.status == EntityStatus.ACTIVE
        ]

    def find_humans(self) -> list[Entity]:
        """Find all registered humans."""
        return self.find_by_type(EntityType.HUMAN)

    def update_status(self, entity_id: str, status: EntityStatus) -> None:
        """Update an entity's status."""
        if entity_id in self._entities:
            self._entities[entity_id].status = status
            self._entities[entity_id].last_seen = datetime.utcnow()
            self._save()

    def activate_node(self, node_id: str, workspace_id: str) -> None:
        """Mark a node as active in a workspace."""
        if node_id not in self._entities:
            # Auto-register nodes from the model
            self._entities[node_id] = Entity(
                id=node_id,
                type=EntityType.NODE,
                authority=AuthorityLevel.NODE,
                channels=["model"],
                status=EntityStatus.ACTIVE,
                workspace_id=workspace_id,
            )
        else:
            self._entities[node_id].status = EntityStatus.ACTIVE
            self._entities[node_id].workspace_id = workspace_id
            self._entities[node_id].last_seen = datetime.utcnow()
        self._save()

    def deactivate_node(self, node_id: str) -> None:
        """Mark a node as dormant."""
        if node_id in self._entities:
            self._entities[node_id].status = EntityStatus.DORMANT
            self._entities[node_id].workspace_id = None
            self._save()

    def get_escalation_path(self, entity_id: str) -> list[Entity]:
        """Get the escalation path for an entity.

        If entity is unreachable, who should we try next?
        """
        entity = self.get(entity_id)
        if not entity:
            return []

        path = []
        for esc_id in entity.escalation_path:
            esc_entity = self.get(esc_id)
            if esc_entity and esc_entity.is_reachable():
                path.append(esc_entity)

        # Always include guardians as fallback
        for guardian in self.find_guardians():
            if guardian.id not in entity.escalation_path:
                path.append(guardian)

        return path
