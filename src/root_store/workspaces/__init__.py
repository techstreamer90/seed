"""Workspace System - isolated environments for agents.

Workspaces provide:
- Isolation: Each agent works in their own space
- Pull: Bring nodes from canonical store into workspace
- Modify: Make changes without affecting others
- Commit: Push changes back when ready
- Rollback: Discard changes if needed

Think of it like git branches but for the model.

Node activation provides:
- Dormant to Active transition
- Context loading for agents
- Agent spawning coordination
"""

from .workspace import Workspace, WorkspaceStatus
from .manager import WorkspaceManager
from .activation import NodeActivator, ActivationLevel, ActivationState

