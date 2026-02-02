#!/usr/bin/env python3
"""
UI Tools - Common functions for agents to control views.

Import these tools in any agent to manipulate the visual layer.

Usage:
    from src.ui.tools import (
        create_view, show_hierarchy, focus_node, show_all,
        add_status_indicator, highlight_nodes, list_views,
        get_my_view, update_title
    )

    # Quick operations
    show_hierarchy("reality-spawnie", view="spawnie")
    focus_node("mod-pulse", view="debug")
    highlight_nodes(["mod-pulse", "mod-status"], color="#ff0000")

    # Full control
    view = get_my_view("my-agent")
    view.clear()
    view.add_node("custom", x=100, y=100, label="My Node")
    view.render()
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Literal

from src.ui.agent_view import AgentView, list_views as _list_views

MODEL_PATH = Path(__file__).parent.parent.parent / "model" / "sketch.json"


# === Quick View Operations ===

def create_view(view_name: str) -> AgentView:
    """
    Create a new view for an agent.

    Args:
        view_name: Unique name for this view

    Returns:
        AgentView instance ready to use
    """
    return AgentView(view_name)


def get_my_view(view_name: str) -> AgentView:
    """
    Get or create a view, loading existing state if present.

    Args:
        view_name: View name

    Returns:
        AgentView with existing state loaded
    """
    view = AgentView(view_name)
    try:
        view.load()
    except:
        pass
    return view


def show_hierarchy(
    root_id: str,
    view: str = None,
    depth: int = 3,
) -> str:
    """
    Show hierarchy from a node.

    Args:
        root_id: Root node ID (e.g., "reality-spawnie")
        view: View name (defaults to node name without prefix)
        depth: How deep to show

    Returns:
        Status message
    """
    if view is None:
        view = root_id.split("-", 1)[-1] if "-" in root_id else root_id

    v = AgentView(view)
    v.show_hierarchy(root_id, depth=depth)
    v.render()

    return f"View '{view}': {v.get_element_count()} elements from {root_id}"


def focus_node(
    node_id: str,
    view: str = "focus",
    show_related: bool = True,
) -> str:
    """
    Focus on a single node with context.

    Args:
        node_id: Node to focus on
        view: View name
        show_related: Whether to show connected nodes

    Returns:
        Status message
    """
    v = AgentView(view)
    v.focus(node_id, show_related=show_related)
    v.render()

    return f"View '{view}': focused on {node_id}"


def show_all(view: str = "main") -> str:
    """
    Show all nodes in a clean grid layout.

    Args:
        view: View name

    Returns:
        Status message
    """
    from src.ui.canvas import draw_clean_layout
    return draw_clean_layout(view)


def show_nodes(
    node_ids: List[str],
    view: str = "custom",
    layout: Literal["grid", "horizontal", "vertical"] = "grid",
) -> str:
    """
    Show specific nodes.

    Args:
        node_ids: List of node IDs to show
        view: View name
        layout: How to arrange them

    Returns:
        Status message
    """
    v = AgentView(view)
    v.show_nodes(node_ids, layout=layout)
    v.render()

    return f"View '{view}': {len(node_ids)} nodes"


def show_type(
    node_type: str,
    view: str = None,
) -> str:
    """
    Show all nodes of a type.

    Args:
        node_type: Type name (e.g., "Reality", "Aspiration")
        view: View name (defaults to type name lowercase)

    Returns:
        Status message
    """
    view = view or node_type.lower()
    v = AgentView(view)
    v.show_type(node_type)
    v.render()

    return f"View '{view}': all {node_type} nodes"


# === Visual Modifications ===

def highlight_nodes(
    node_ids: List[str],
    view: str = "main",
    color: str = "#58a6ff",
) -> str:
    """
    Highlight specific nodes in a view.

    Args:
        node_ids: Nodes to highlight
        view: View name
        color: Highlight color

    Returns:
        Status message
    """
    v = get_my_view(view)

    for elem in v.elements:
        if elem.get("type") == "rect":
            node_id = elem.get("data", {}).get("nodeId")
            if node_id in node_ids:
                elem["stroke"] = color
                elem["strokeWidth"] = 3

    v.render()
    return f"Highlighted {len(node_ids)} nodes in '{view}'"


def add_status_indicator(
    node_id: str,
    status: Literal["ok", "warning", "error", "info"],
    view: str = "main",
) -> str:
    """
    Add a status indicator to a node.

    Args:
        node_id: Node to mark
        status: Status type
        view: View name

    Returns:
        Status message
    """
    colors = {
        "ok": "#238636",
        "warning": "#d29922",
        "error": "#f85149",
        "info": "#58a6ff",
    }

    v = get_my_view(view)

    for elem in v.elements:
        if elem.get("data", {}).get("nodeId") == node_id:
            # Add a small indicator dot
            x = elem["x"] + elem["w"] - 8
            y = elem["y"] + 4
            v.add_rect(
                f"status-{node_id}",
                x=x, y=y, w=6, h=6,
                fill=colors.get(status, "#6e7681"),
                stroke=colors.get(status, "#6e7681"),
            )
            break

    v.render()
    return f"Added {status} indicator to {node_id}"


def update_title(
    view: str,
    title: str,
) -> str:
    """
    Add a title to a view.

    Args:
        view: View name
        title: Title text

    Returns:
        Status message
    """
    v = get_my_view(view)

    # Remove old title if exists
    v.elements = [e for e in v.elements if e.get("id") != "view-title"]

    # Add new title
    v.add_text(
        "view-title",
        title,
        x=v.canvas["width"] // 2,
        y=25,
        fill="#c9d1d9",
        font="16px sans-serif",
    )

    v.render()
    return f"Updated title in '{view}'"


# === View Management ===

def list_views() -> List[str]:
    """List all available views."""
    return _list_views()


def delete_view(view_name: str) -> str:
    """
    Delete a view.

    Args:
        view_name: View to delete

    Returns:
        Status message
    """
    import json

    with open(MODEL_PATH, encoding="utf-8") as f:
        model = json.load(f)

    if view_name in model.get("views", {}):
        del model["views"][view_name]

        with open(MODEL_PATH, "w", encoding="utf-8") as f:
            json.dump(model, f, indent=2)

        return f"Deleted view '{view_name}'"

    return f"View '{view_name}' not found"


def copy_view(from_view: str, to_view: str) -> str:
    """
    Copy a view to a new name.

    Args:
        from_view: Source view
        to_view: Destination view

    Returns:
        Status message
    """
    import json

    with open(MODEL_PATH, encoding="utf-8") as f:
        model = json.load(f)

    if from_view in model.get("views", {}):
        model["views"][to_view] = model["views"][from_view].copy()

        with open(MODEL_PATH, "w", encoding="utf-8") as f:
            json.dump(model, f, indent=2)

        return f"Copied '{from_view}' to '{to_view}'"

    return f"View '{from_view}' not found"


# === Convenience: Reality-specific views ===

def view_spawnie() -> str:
    """Show Spawnie hierarchy."""
    return show_hierarchy("reality-spawnie", "spawnie", depth=2)


def view_root() -> str:
    """Show Root (Seed) hierarchy."""
    return show_hierarchy("reality-seed", "root", depth=2)


def view_store() -> str:
    """Show Root Model Store hierarchy."""
    return show_hierarchy("reality-root-model-store", "store", depth=3)


def view_core() -> str:
    """Show Root Core hierarchy."""
    return show_hierarchy("reality-seed-core", "core", depth=3)


def view_ui() -> str:
    """Show UI/Renderer hierarchy."""
    return show_hierarchy("reality-seed-ui", "ui", depth=2)


def view_bam() -> str:
    """Show BAM hierarchy."""
    return show_hierarchy("reality-bam", "bam", depth=2)


# === SchauspielerSub Coordination ===

def scan_visualization_requests() -> List[Dict[str, Any]]:
    """
    Main Schauspieler scans for all active visualization requests.

    Returns:
        List of nodes with active visualization requests
    """
    from src.ui.schauspieler_protocol import scan_all_requests
    return scan_all_requests()


def get_all_sub_views() -> List[Dict[str, Any]]:
    """
    Main Schauspieler gets all views created by SchauspielerSubs.

    Returns:
        List of {node_id, views} for all nodes with sub-views
    """
    from src.ui.schauspieler_protocol import get_all_views
    return get_all_views()


def create_master_view(view_name: str = "schauspieler-master") -> str:
    """
    Create a master view showing all sub-Schauspieler activity.

    Args:
        view_name: Name for the master view

    Returns:
        Status message
    """
    from src.ui.schauspieler_protocol import scan_all_requests, get_all_views

    view = AgentView(view_name)
    view.clear()

    # Get all requests and views
    requests = scan_all_requests()
    all_views = get_all_views()

    # Create a summary visualization
    y_offset = 50
    for req in requests:
        node_id = req["node_id"]
        status = req["status"]
        viz_type = req["request"].get("type", "unknown")

        # Add a card for each active request
        view.add_rect(
            f"req-{node_id}",
            x=50, y=y_offset, w=300, h=60,
            fill="#d29922" if status == "requested" else "#58a6ff",
            stroke="#ffffff",
            label=f"{node_id}: {viz_type} ({status})"
        )
        y_offset += 80

    # Add view count summary
    if all_views:
        view.add_text(
            "summary",
            f"Active Sub-Schauspielers: {len(all_views)}",
            x=50, y=20,
            fill="#c9d1d9",
            font="14px sans-serif"
        )

    view.render()
    return f"Master view created: {len(requests)} active requests, {len(all_views)} sub-schauspielers"


# === Info ===

def get_view_info(view_name: str) -> Dict[str, Any]:
    """
    Get info about a view.

    Args:
        view_name: View name

    Returns:
        Dict with view info
    """
    import json

    with open(MODEL_PATH, encoding="utf-8") as f:
        model = json.load(f)

    view = model.get("views", {}).get(view_name, {})

    return {
        "name": view_name,
        "exists": bool(view),
        "element_count": len(view.get("elements", [])),
        "canvas": view.get("canvas", {}),
        "updated_at": view.get("updated_at"),
    }


# CLI
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("UI Tools - Quick functions for agents")
        print()
        print("Commands:")
        print("  list                    - List all views")
        print("  hierarchy <node> [view] - Show hierarchy")
        print("  focus <node> [view]     - Focus on node")
        print("  all [view]              - Show all nodes")
        print("  type <type> [view]      - Show nodes of type")
        print("  delete <view>           - Delete a view")
        print()
        print("Quick views:")
        print("  spawnie, root, store, core, ui, bam")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "list":
        for v in list_views():
            info = get_view_info(v)
            print(f"  {v}: {info['element_count']} elements")

    elif cmd == "hierarchy" and len(sys.argv) >= 3:
        view = sys.argv[3] if len(sys.argv) > 3 else None
        print(show_hierarchy(sys.argv[2], view))

    elif cmd == "focus" and len(sys.argv) >= 3:
        view = sys.argv[3] if len(sys.argv) > 3 else "focus"
        print(focus_node(sys.argv[2], view))

    elif cmd == "all":
        view = sys.argv[2] if len(sys.argv) > 2 else "main"
        print(show_all(view))

    elif cmd == "type" and len(sys.argv) >= 3:
        view = sys.argv[3] if len(sys.argv) > 3 else None
        print(show_type(sys.argv[2], view))

    elif cmd == "delete" and len(sys.argv) >= 3:
        print(delete_view(sys.argv[2]))

    elif cmd in ["spawnie", "root", "store", "core", "ui", "bam"]:
        func = globals()[f"view_{cmd}"]
        print(func())

    else:
        print(f"Unknown command: {cmd}")
