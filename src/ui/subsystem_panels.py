#!/usr/bin/env python3
"""
Subsystem Panel Views - Self-rendering panel views for each subsystem.

Each subsystem renders itself showing:
- Component status
- Dependencies
- Current state

Used by subsystems to visualize their internal structure and health.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Optional

from src.ui.agent_view import AgentView
from src.root_store.loader import load_merged_model

MODEL_PATH = Path(__file__).parent.parent.parent / "model" / "sketch.json"


def create_subsystem_panel(subsystem_id: str, view_name: str = None) -> AgentView:
    """
    Create a self-rendering panel for a subsystem showing component status.

    Args:
        subsystem_id: ID of the subsystem (e.g., "subsystem-root-store")
        view_name: Name for the view (defaults to subsystem name)

    Returns:
        AgentView with subsystem panel
    """
    if view_name is None:
        view_name = subsystem_id.replace("subsystem-", "")

    view = AgentView(view_name)
    view.set_size(1000, 600)
    view.set_background("#0d1117")
    view.clear()

    # Load the merged model to get subsystem data
    graph = view._get_graph()
    subsystem = graph.nodes.get(subsystem_id)

    if not subsystem:
        return view

    # Title bar with subsystem label and status
    label = subsystem.get("label", subsystem_id)
    status = subsystem.get("status", "unknown")
    status_color = {
        "design": "#d29922",
        "stub": "#d29922",
        "active": "#238636",
        "planning": "#58a6ff",
        "implemented": "#238636",
        "unknown": "#6e7681",
    }.get(status, "#6e7681")

    # Header
    view.add_rect(
        "header",
        x=10, y=10, w=980, h=50,
        fill="#1c2128", stroke="#30363d", label=""
    )

    view.add_text(
        "header-title",
        f"{label} ({status})",
        x=30, y=35,
        fill="#c9d1d9", font="16px bold sans-serif"
    )

    # Status indicator
    view.add_rect(
        "status-indicator",
        x=960, y=20, w=20, h=30,
        fill=status_color, stroke=status_color
    )

    # Get modules/children of this subsystem
    modules = _get_subsystem_modules(graph, subsystem_id)

    # Render modules as cards showing component status
    y_offset = 80
    x_left = 20
    col_width = 300
    col_height = 150
    cols = 3
    col_count = 0

    for module_id, module in modules:
        col = col_count % cols
        row = col_count // cols
        x = x_left + col * (col_width + 20)
        y = y_offset + row * (col_height + 20)

        # Module card
        module_status = module.get("status", "unknown")
        module_status_color = {
            "implemented": "#238636",
            "in_progress": "#58a6ff",
            "design": "#d29922",
            "stub": "#d29922",
            "planning": "#58a6ff",
            "unknown": "#6e7681",
        }.get(module_status, "#6e7681")

        view.add_rect(
            f"module-{module_id}",
            x=x, y=y, w=col_width, h=col_height,
            fill="#161b22", stroke=module_status_color,
            label=""
        )

        # Module label
        mod_label = module.get("label", module_id.replace("mod-", ""))
        view.add_text(
            f"mod-label-{module_id}",
            mod_label,
            x=x + 10, y=y + 20,
            fill="#c9d1d9", font="12px bold sans-serif"
        )

        # Status badge
        view.add_rect(
            f"mod-status-badge-{module_id}",
            x=x + col_width - 60, y=y + 8, w=50, h=16,
            fill=module_status_color, stroke="#ffffff"
        )

        view.add_text(
            f"mod-status-text-{module_id}",
            module_status[:4].upper(),
            x=x + col_width - 55, y=y + 18,
            fill="#000000", font="10px bold sans-serif"
        )

        # Component count
        components = _get_module_components(graph, module_id)
        component_text = f"Components: {len(components)}"
        view.add_text(
            f"mod-components-{module_id}",
            component_text,
            x=x + 10, y=y + 50,
            fill="#8b949e", font="10px sans-serif"
        )

        # Dependencies info
        deps = _get_module_dependencies(graph, module_id)
        deps_text = f"Dependencies: {len(deps)}"
        view.add_text(
            f"mod-deps-{module_id}",
            deps_text,
            x=x + 10, y=y + 70,
            fill="#8b949e", font="10px sans-serif"
        )

        # Current reality snippet
        current_reality = module.get("plan", {}).get("current_reality", "")
        if current_reality:
            snippet = current_reality[:50] + "..." if len(current_reality) > 50 else current_reality
            view.add_text(
                f"mod-reality-{module_id}",
                snippet,
                x=x + 10, y=y + 90,
                fill="#6e7681", font="9px sans-serif"
            )

        col_count += 1

    # Summary section at bottom
    summary_y = 450
    view.add_rect(
        "summary-bg",
        x=10, y=summary_y, w=980, h=140,
        fill="#161b22", stroke="#30363d"
    )

    view.add_text(
        "summary-title",
        "Subsystem Summary",
        x=30, y=summary_y + 20,
        fill="#c9d1d9", font="12px bold sans-serif"
    )

    # Summary stats
    total_modules = len(modules)
    total_components = sum(len(_get_module_components(graph, m[0])) for m in modules)
    total_deps = sum(len(_get_module_dependencies(graph, m[0])) for m in modules)

    view.add_text(
        "summary-stats",
        f"Total Modules: {total_modules} | Total Components: {total_components} | Dependencies: {total_deps}",
        x=30, y=summary_y + 50,
        fill="#8b949e", font="11px sans-serif"
    )

    # Current aspiration
    aspiration = subsystem.get("plan", {}).get("aspiration", "")
    if aspiration:
        snippet = aspiration[:100] + "..." if len(aspiration) > 100 else aspiration
        view.add_text(
            "summary-aspiration",
            f"Aspiration: {snippet}",
            x=30, y=summary_y + 80,
            fill="#6e7681", font="10px italic sans-serif"
        )

    return view


def _get_subsystem_modules(graph: Any, subsystem_id: str) -> List[tuple]:
    """Get all modules/children of a subsystem."""
    modules = []

    # Find nodes with parent = subsystem_id
    for node_id, node in graph.nodes.items():
        if node.get("parent") == subsystem_id and node.get("type") == "Module":
            modules.append((node_id, node))

    # Also check subsystems field if present
    subsystem = graph.nodes.get(subsystem_id, {})
    if "subsystems" in subsystem:
        for sub_id in subsystem["subsystems"]:
            node = graph.nodes.get(sub_id, {})
            if node and node.get("type") == "Module":
                modules.append((sub_id, node))

    return modules


def _get_module_components(graph: Any, module_id: str) -> List[tuple]:
    """Get all components in a module."""
    components = []

    for node_id, node in graph.nodes.items():
        if node.get("parent") == module_id and node.get("type") == "Component":
            components.append((node_id, node))

    return components


def _get_module_dependencies(graph: Any, module_id: str) -> List[tuple]:
    """Get dependencies of a module."""
    dependencies = []

    for edge in graph.edges:
        if edge.get("from") == module_id and edge.get("type").upper() == "USES":
            to_id = edge.get("to")
            if to_id and to_id not in [d[0] for d in dependencies]:
                node = graph.nodes.get(to_id)
                if node:
                    dependencies.append((to_id, node))

    return dependencies


# === Quick functions for each subsystem ===

def show_root_store_panel() -> str:
    """Create panel for subsystem-root-store."""
    view = create_subsystem_panel("subsystem-root-store", "root-store-panel")
    view.render()
    return f"Root Store panel: {view.get_element_count()} elements"


def show_ui_panel() -> str:
    """Create panel for subsystem-ui."""
    view = create_subsystem_panel("subsystem-ui", "ui-panel")
    view.render()
    return f"UI panel: {view.get_element_count()} elements"


def show_core_panel() -> str:
    """Create panel for subsystem-core."""
    view = create_subsystem_panel("subsystem-core", "core-panel")
    view.render()
    return f"Core panel: {view.get_element_count()} elements"


def show_canvas_panel() -> str:
    """Create panel for subsystem-schauspieler-canvas."""
    view = create_subsystem_panel("subsystem-schauspieler-canvas", "canvas-panel")
    view.render()
    return f"Canvas panel: {view.get_element_count()} elements"


def show_render_api_panel() -> str:
    """Create panel for subsystem-schauspieler-render-api."""
    view = create_subsystem_panel("subsystem-schauspieler-render-api", "render-api-panel")
    view.render()
    return f"Render API panel: {view.get_element_count()} elements"


def show_orchestrator_panel() -> str:
    """Create panel for subsystem-schauspieler-orchestrator."""
    view = create_subsystem_panel("subsystem-schauspieler-orchestrator", "orchestrator-panel")
    view.render()
    return f"Orchestrator panel: {view.get_element_count()} elements"


def render_all_subsystem_panels() -> Dict[str, str]:
    """Render all 6 subsystem panels."""
    results = {}

    panels = [
        ("subsystem-root-store", "root-store-panel"),
        ("subsystem-ui", "ui-panel"),
        ("subsystem-core", "core-panel"),
        ("subsystem-schauspieler-canvas", "canvas-panel"),
        ("subsystem-schauspieler-render-api", "render-api-panel"),
        ("subsystem-schauspieler-orchestrator", "orchestrator-panel"),
    ]

    for subsystem_id, view_name in panels:
        view = create_subsystem_panel(subsystem_id, view_name)
        view.render()
        results[view_name] = f"{view.get_element_count()} elements"

    return results


# CLI
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Subsystem Panel Views - Self-rendering subsystem panels")
        print()
        print("Commands:")
        print("  root-store      - Show Root Store panel")
        print("  ui              - Show UI panel")
        print("  core            - Show Core panel")
        print("  canvas          - Show Canvas panel")
        print("  render-api      - Show Render API panel")
        print("  orchestrator    - Show Orchestrator panel")
        print("  all             - Render all 6 panels")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "root-store":
        print(show_root_store_panel())
    elif cmd == "ui":
        print(show_ui_panel())
    elif cmd == "core":
        print(show_core_panel())
    elif cmd == "canvas":
        print(show_canvas_panel())
    elif cmd == "render-api":
        print(show_render_api_panel())
    elif cmd == "orchestrator":
        print(show_orchestrator_panel())
    elif cmd == "all":
        results = render_all_subsystem_panels()
        for view_name, info in results.items():
            print(f"  {view_name}: {info}")
    else:
        print(f"Unknown command: {cmd}")
