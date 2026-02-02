#!/usr/bin/env python3
"""
Spawnie Views - Custom visualizations for the reality-spawnie node.

Shows Spawnie's spawn queue, active sessions, and capabilities.

Usage:
    from src.ui.spawnie_views import (
        show_spawnie_dashboard,
        show_spawn_queue,
        show_active_sessions,
        show_capabilities
    )

    # Show complete dashboard
    show_spawnie_dashboard()

    # Show individual views
    show_spawn_queue()
    show_active_sessions()
    show_capabilities()
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.ui.agent_view import AgentView

MODEL_PATH = Path(__file__).parent.parent.parent / "model" / "sketch.json"


def _read_model() -> Dict[str, Any]:
    """Read the model file."""
    with open(MODEL_PATH, encoding="utf-8") as f:
        return json.load(f)


def _find_spawnie_node(model: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Find the reality-spawnie node."""
    for node in model.get("nodes", []):
        if node.get("id") == "reality-spawnie":
            return node
    return None


def show_spawnie_dashboard(view_name: str = "spawnie-dashboard") -> str:
    """
    Show complete Spawnie dashboard with queue, sessions, and capabilities.

    Args:
        view_name: Name for the dashboard view

    Returns:
        Status message
    """
    model = _read_model()
    spawnie = _find_spawnie_node(model)

    if not spawnie:
        return "Error: reality-spawnie node not found"

    view = AgentView(view_name)
    view.clear()
    view.set_size(1400, 900)

    # Title
    view.add_text(
        "title",
        "Spawnie Workflow Orchestrator - Dashboard",
        x=700, y=30,
        fill="#58a6ff",
        font="18px sans-serif bold"
    )

    # Get data
    state = spawnie.get("state", {})
    capabilities = spawnie.get("capabilities", {})
    agent_context = spawnie.get("agent_context", {})
    modes = agent_context.get("mode_based_spawning", {})

    active_sessions = state.get("active_sessions", [])
    spawn_queue = state.get("spawn_queue", [])  # If exists in future

    # Section 1: Capabilities (left column)
    _add_capabilities_section(view, capabilities, modes, x=50, y=70)

    # Section 2: Active Sessions (center)
    _add_sessions_section(view, active_sessions, x=500, y=70)

    # Section 3: Spawn Queue (right column)
    _add_queue_section(view, spawn_queue, x=950, y=70)

    # Status bar at bottom
    last_updated = state.get("last_updated", "never")
    view.add_text(
        "status",
        f"Last updated: {last_updated} | Sessions: {len(active_sessions)} | Queue: {len(spawn_queue)}",
        x=50, y=860,
        fill="#8b949e",
        font="12px monospace"
    )

    view.render()
    return f"Spawnie dashboard created: {view.get_element_count()} elements"


def _add_capabilities_section(
    view: AgentView,
    capabilities: Dict[str, str],
    modes: Dict[str, Any],
    x: float,
    y: float
) -> None:
    """Add capabilities section to view."""
    # Header
    view.add_rect(
        "cap-header",
        x=x, y=y, w=400, h=40,
        fill="#238636",
        stroke="#ffffff",
        label="Capabilities"
    )

    y_offset = y + 60

    # List capabilities
    for i, (cap_name, cap_desc) in enumerate(capabilities.items()):
        # Capability box
        view.add_rect(
            f"cap-{i}",
            x=x, y=y_offset, w=400, h=60,
            fill="#21262d",
            stroke="#30363d"
        )

        # Capability name
        view.add_text(
            f"cap-name-{i}",
            cap_name.replace("_", " ").title(),
            x=x + 10, y=y_offset + 20,
            fill="#58a6ff",
            font="14px sans-serif bold"
        )

        # Capability description
        desc_text = cap_desc[:50] + "..." if len(cap_desc) > 50 else cap_desc
        view.add_text(
            f"cap-desc-{i}",
            desc_text,
            x=x + 10, y=y_offset + 40,
            fill="#8b949e",
            font="12px sans-serif"
        )

        y_offset += 75

    # Modes section
    if modes and modes.get("available_modes"):
        view.add_text(
            "modes-header",
            "Available Modes:",
            x=x + 10, y=y_offset + 10,
            fill="#a371f7",
            font="14px sans-serif bold"
        )

        y_offset += 30
        available_modes = modes.get("available_modes", [])
        for i, mode in enumerate(available_modes[:6]):  # Show first 6
            view.add_text(
                f"mode-{i}",
                f"• {mode}",
                x=x + 20, y=y_offset,
                fill="#8b949e",
                font="12px monospace"
            )
            y_offset += 25


def _add_sessions_section(
    view: AgentView,
    active_sessions: List[Dict[str, Any]],
    x: float,
    y: float
) -> None:
    """Add active sessions section to view."""
    # Header
    count = len(active_sessions)
    header_color = "#238636" if count > 0 else "#6e7681"

    view.add_rect(
        "sessions-header",
        x=x, y=y, w=400, h=40,
        fill=header_color,
        stroke="#ffffff",
        label=f"Active Sessions ({count})"
    )

    y_offset = y + 60

    if not active_sessions:
        # No sessions message
        view.add_rect(
            "no-sessions",
            x=x, y=y_offset, w=400, h=80,
            fill="#21262d",
            stroke="#30363d"
        )
        view.add_text(
            "no-sessions-text",
            "No active sessions",
            x=x + 150, y=y_offset + 40,
            fill="#6e7681",
            font="14px sans-serif italic"
        )
    else:
        # List sessions
        for i, session in enumerate(active_sessions[:8]):  # Show first 8
            session_id = session.get("id", f"session-{i}")
            node_id = session.get("node_id", "unknown")
            status = session.get("status", "running")
            started = session.get("started_at", "")

            # Session box
            status_color = {
                "running": "#238636",
                "waiting": "#d29922",
                "error": "#f85149",
            }.get(status, "#6e7681")

            view.add_rect(
                f"session-{i}",
                x=x, y=y_offset, w=400, h=80,
                fill="#21262d",
                stroke=status_color
            )

            # Session ID
            view.add_text(
                f"session-id-{i}",
                f"ID: {session_id[:20]}...",
                x=x + 10, y=y_offset + 20,
                fill="#58a6ff",
                font="13px monospace bold"
            )

            # Node ID
            view.add_text(
                f"session-node-{i}",
                f"Node: {node_id}",
                x=x + 10, y=y_offset + 40,
                fill="#c9d1d9",
                font="12px sans-serif"
            )

            # Status and time
            view.add_text(
                f"session-status-{i}",
                f"Status: {status} | {started}",
                x=x + 10, y=y_offset + 60,
                fill="#8b949e",
                font="11px monospace"
            )

            # Status indicator dot
            view.add_rect(
                f"status-dot-{i}",
                x=x + 380, y=y_offset + 10, w=10, h=10,
                fill=status_color,
                stroke=status_color
            )

            y_offset += 95


def _add_queue_section(
    view: AgentView,
    spawn_queue: List[Dict[str, Any]],
    x: float,
    y: float
) -> None:
    """Add spawn queue section to view."""
    # Header
    count = len(spawn_queue)
    header_color = "#d29922" if count > 0 else "#6e7681"

    view.add_rect(
        "queue-header",
        x=x, y=y, w=400, h=40,
        fill=header_color,
        stroke="#ffffff",
        label=f"Spawn Queue ({count})"
    )

    y_offset = y + 60

    if not spawn_queue:
        # Empty queue message
        view.add_rect(
            "empty-queue",
            x=x, y=y_offset, w=400, h=80,
            fill="#21262d",
            stroke="#30363d"
        )
        view.add_text(
            "empty-queue-text",
            "Queue is empty",
            x=x + 150, y=y_offset + 40,
            fill="#6e7681",
            font="14px sans-serif italic"
        )
    else:
        # List queued items
        for i, item in enumerate(spawn_queue[:8]):  # Show first 8
            task = item.get("task", "unknown task")
            node_id = item.get("node_id", "")
            mode = item.get("mode", "")
            priority = item.get("priority", "normal")
            queued_at = item.get("queued_at", "")

            # Queue item box
            priority_color = {
                "high": "#f85149",
                "normal": "#58a6ff",
                "low": "#6e7681",
            }.get(priority, "#6e7681")

            view.add_rect(
                f"queue-{i}",
                x=x, y=y_offset, w=400, h=80,
                fill="#21262d",
                stroke=priority_color
            )

            # Task description
            task_short = task[:40] + "..." if len(task) > 40 else task
            view.add_text(
                f"queue-task-{i}",
                task_short,
                x=x + 10, y=y_offset + 20,
                fill="#c9d1d9",
                font="13px sans-serif bold"
            )

            # Node and mode
            if node_id or mode:
                detail = f"Node: {node_id}" if node_id else ""
                if mode:
                    detail += f" | Mode: {mode}" if detail else f"Mode: {mode}"
                view.add_text(
                    f"queue-detail-{i}",
                    detail,
                    x=x + 10, y=y_offset + 40,
                    fill="#8b949e",
                    font="11px sans-serif"
                )

            # Priority and time
            view.add_text(
                f"queue-info-{i}",
                f"Priority: {priority} | Queued: {queued_at}",
                x=x + 10, y=y_offset + 60,
                fill="#8b949e",
                font="11px monospace"
            )

            # Priority indicator
            view.add_rect(
                f"priority-{i}",
                x=x + 380, y=y_offset + 10, w=10, h=10,
                fill=priority_color,
                stroke=priority_color
            )

            y_offset += 95


def show_spawn_queue(view_name: str = "spawnie-queue") -> str:
    """
    Show only the spawn queue.

    Args:
        view_name: Name for the queue view

    Returns:
        Status message
    """
    model = _read_model()
    spawnie = _find_spawnie_node(model)

    if not spawnie:
        return "Error: reality-spawnie node not found"

    view = AgentView(view_name)
    view.clear()
    view.set_size(500, 800)

    # Title
    view.add_text(
        "title",
        "Spawnie - Spawn Queue",
        x=250, y=30,
        fill="#d29922",
        font="16px sans-serif bold"
    )

    spawn_queue = spawnie.get("state", {}).get("spawn_queue", [])
    _add_queue_section(view, spawn_queue, x=50, y=70)

    view.render()
    return f"Spawn queue view: {len(spawn_queue)} items"


def show_active_sessions(view_name: str = "spawnie-sessions") -> str:
    """
    Show only active sessions.

    Args:
        view_name: Name for the sessions view

    Returns:
        Status message
    """
    model = _read_model()
    spawnie = _find_spawnie_node(model)

    if not spawnie:
        return "Error: reality-spawnie node not found"

    view = AgentView(view_name)
    view.clear()
    view.set_size(500, 800)

    # Title
    view.add_text(
        "title",
        "Spawnie - Active Sessions",
        x=250, y=30,
        fill="#238636",
        font="16px sans-serif bold"
    )

    active_sessions = spawnie.get("state", {}).get("active_sessions", [])
    _add_sessions_section(view, active_sessions, x=50, y=70)

    view.render()
    return f"Active sessions view: {len(active_sessions)} sessions"


def show_capabilities(view_name: str = "spawnie-capabilities") -> str:
    """
    Show Spawnie capabilities and modes.

    Args:
        view_name: Name for the capabilities view

    Returns:
        Status message
    """
    model = _read_model()
    spawnie = _find_spawnie_node(model)

    if not spawnie:
        return "Error: reality-spawnie node not found"

    view = AgentView(view_name)
    view.clear()
    view.set_size(500, 800)

    # Title
    view.add_text(
        "title",
        "Spawnie - Capabilities",
        x=250, y=30,
        fill="#238636",
        font="16px sans-serif bold"
    )

    capabilities = spawnie.get("capabilities", {})
    modes = spawnie.get("agent_context", {}).get("mode_based_spawning", {})

    _add_capabilities_section(view, capabilities, modes, x=50, y=70)

    view.render()
    return f"Capabilities view: {len(capabilities)} capabilities"


# === CLI ===

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Spawnie Views - Custom visualizations for reality-spawnie")
        print()
        print("Commands:")
        print("  dashboard    - Show complete dashboard")
        print("  queue        - Show spawn queue")
        print("  sessions     - Show active sessions")
        print("  capabilities - Show capabilities and modes")
        print()
        print("Examples:")
        print("  python spawnie_views.py dashboard")
        print("  python spawnie_views.py sessions")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "dashboard":
        print(show_spawnie_dashboard())
    elif cmd == "queue":
        print(show_spawn_queue())
    elif cmd == "sessions":
        print(show_active_sessions())
    elif cmd == "capabilities":
        print(show_capabilities())
    else:
        print(f"Unknown command: {cmd}")
        print("Use: dashboard, queue, sessions, or capabilities")
