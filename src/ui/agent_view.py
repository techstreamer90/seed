#!/usr/bin/env python3
"""
Agent View API - Tools for agents to control their views.

Each agent can have its own view in the model. Views are stored at:
    model.views.<view_name>

Usage:
    from src.ui.agent_view import AgentView

    # Create a view for your agent
    view = AgentView("spawnie")  # Creates views/spawnie

    # Show specific nodes
    view.show_nodes(["reality-spawnie", "subsystem-workflows"])

    # Show hierarchy from a root
    view.show_hierarchy("reality-spawnie", depth=3)

    # Focus on a single node with context
    view.focus("reality-spawnie", show_related=True)

    # Custom layout
    view.clear()
    view.add_node("my-node", x=100, y=100, label="Custom")
    view.render()
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Literal

MODEL_PATH = Path(__file__).parent.parent.parent / "model" / "sketch.json"


class AgentView:
    """View controller for an agent."""

    def __init__(self, view_name: str, model_path: Optional[Path] = None):
        """
        Create a view controller.

        Args:
            view_name: Name of this agent's view (e.g., "spawnie", "bam", "main")
            model_path: Optional custom model path
        """
        self.view_name = view_name
        self.model_path = model_path or MODEL_PATH
        self.elements: List[Dict[str, Any]] = []
        self.canvas = {"width": 1200, "height": 800, "background": "#0d1117"}
        self.styles = _default_styles()

    def _read_model(self) -> Dict[str, Any]:
        with open(self.model_path, encoding="utf-8") as f:
            return json.load(f)

    def _write_model(self, model: Dict[str, Any]) -> None:
        model["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(self.model_path, "w", encoding="utf-8") as f:
            json.dump(model, f, indent=2)

    def _get_graph(self):
        """Get the merged graph."""
        from src.root_store.loader import load_merged_model
        return load_merged_model(self.model_path.resolve())

    # === View State ===

    def clear(self) -> "AgentView":
        """Clear all elements from the view."""
        self.elements = []
        return self

    def set_size(self, width: int, height: int) -> "AgentView":
        """Set canvas size."""
        self.canvas["width"] = width
        self.canvas["height"] = height
        return self

    def set_background(self, color: str) -> "AgentView":
        """Set background color."""
        self.canvas["background"] = color
        return self

    # === Low-level Element Control ===

    def add_rect(
        self,
        id: str,
        x: float, y: float,
        w: float, h: float,
        fill: str = "#6e7681",
        stroke: str = "#ffffff",
        label: str = "",
        data: Dict[str, Any] = None,
    ) -> "AgentView":
        """Add a rectangle element."""
        elem = {
            "id": id, "type": "rect",
            "x": x, "y": y, "w": w, "h": h,
            "fill": fill, "stroke": stroke, "label": label,
        }
        if data:
            elem["data"] = data
        self.elements.append(elem)
        return self

    def add_line(
        self,
        id: str,
        x1: float, y1: float,
        x2: float, y2: float,
        stroke: str = "#30363d",
        strokeWidth: float = 1,
    ) -> "AgentView":
        """Add a line element."""
        self.elements.append({
            "id": id, "type": "line",
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "stroke": stroke, "strokeWidth": strokeWidth,
        })
        return self

    def add_text(
        self,
        id: str,
        text: str,
        x: float, y: float,
        fill: str = "#c9d1d9",
        font: str = "12px sans-serif",
    ) -> "AgentView":
        """Add a text element."""
        self.elements.append({
            "id": id, "type": "text",
            "text": text, "x": x, "y": y,
            "fill": fill, "font": font,
        })
        return self

    def add_node(
        self,
        node_id: str,
        x: float, y: float,
        label: str = None,
        node_type: str = "default",
        w: float = None,
        h: float = 32,
    ) -> "AgentView":
        """Add a styled node (auto-colors based on type)."""
        style = self.styles.get(f"node-{node_type.lower()}", self.styles["node-default"])
        display_label = label or node_id
        if w is None:
            w = max(80, len(display_label) * 8 + 20)

        self.add_rect(
            id=f"node-{node_id}",
            x=x, y=y, w=w, h=h,
            fill=style["fill"],
            stroke=style["stroke"],
            label=display_label,
            data={"nodeId": node_id, "nodeType": node_type}
        )
        return self

    def add_edge(
        self,
        from_id: str,
        to_id: str,
        edge_type: str = "default",
    ) -> "AgentView":
        """Add an edge between two nodes (finds positions automatically)."""
        from_elem = next((e for e in self.elements if e.get("data", {}).get("nodeId") == from_id), None)
        to_elem = next((e for e in self.elements if e.get("data", {}).get("nodeId") == to_id), None)

        if not from_elem or not to_elem:
            return self

        x1 = from_elem["x"] + from_elem["w"]
        y1 = from_elem["y"] + from_elem["h"] / 2
        x2 = to_elem["x"]
        y2 = to_elem["y"] + to_elem["h"] / 2

        style = self.styles.get(f"edge-{edge_type.lower()}", self.styles["edge-default"])

        self.add_line(
            id=f"edge-{from_id}-{to_id}",
            x1=x1, y1=y1, x2=x2, y2=y2,
            stroke=style["stroke"],
            strokeWidth=style.get("strokeWidth", 1),
        )
        return self

    def remove_element(self, element_id: str) -> "AgentView":
        """Remove an element by ID."""
        self.elements = [e for e in self.elements if e["id"] != element_id]
        return self

    # === High-level View Operations ===

    def show_nodes(
        self,
        node_ids: List[str],
        layout: Literal["grid", "horizontal", "vertical"] = "grid",
        show_edges: bool = True,
    ) -> "AgentView":
        """
        Show specific nodes from the model.

        Args:
            node_ids: List of node IDs to show
            layout: How to arrange them
            show_edges: Whether to show edges between them
        """
        graph = self._get_graph()
        self.clear()

        # Get node data
        nodes = []
        for nid in node_ids:
            node = graph.nodes.get(nid)
            if node:
                nodes.append((nid, node))

        # Layout
        positions = _layout_nodes(nodes, layout, self.canvas)

        # Add nodes
        for (nid, node), (x, y) in zip(nodes, positions):
            self.add_node(
                nid, x=x, y=y,
                label=node.get("label", nid),
                node_type=node.get("type", "default"),
            )

        # Add edges
        if show_edges:
            node_set = set(node_ids)
            for edge in graph.edges:
                if edge.get("from") in node_set and edge.get("to") in node_set:
                    self.add_edge(
                        edge.get("from"),
                        edge.get("to"),
                        edge_type=edge.get("type", "default").lower(),
                    )

        return self

    def show_hierarchy(
        self,
        root_id: str,
        depth: int = 3,
        show_edges: bool = True,
    ) -> "AgentView":
        """
        Show hierarchy from a root node.

        Args:
            root_id: Root node ID
            depth: How many levels deep
            show_edges: Whether to show containment edges
        """
        graph = self._get_graph()
        self.clear()

        # Collect nodes by level using BFS
        levels: Dict[int, List[Tuple[str, Dict]]] = {0: []}

        root = graph.nodes.get(root_id)
        if not root:
            return self

        levels[0].append((root_id, root))
        visited = {root_id}

        for level in range(depth - 1):
            levels[level + 1] = []
            for nid, _ in levels[level]:
                children = _get_children(graph, nid)
                for child_id in children:
                    if child_id not in visited:
                        child = graph.nodes.get(child_id)
                        if child:
                            levels[level + 1].append((child_id, child))
                            visited.add(child_id)

        # Layout by level
        y = 50
        spacing_y = 80

        for level in range(depth):
            nodes = levels.get(level, [])
            if not nodes:
                continue

            spacing_x = max(150, self.canvas["width"] // (len(nodes) + 1))

            for i, (nid, node) in enumerate(nodes):
                x = 50 + i * spacing_x
                self.add_node(
                    nid, x=x, y=y,
                    label=node.get("label", nid),
                    node_type=node.get("type", "default"),
                )

            y += spacing_y

        # Add edges
        if show_edges:
            for level in range(depth - 1):
                for nid, _ in levels.get(level, []):
                    for child_id in _get_children(graph, nid):
                        if child_id in visited:
                            self.add_edge(nid, child_id, edge_type="contains")

        return self

    def focus(
        self,
        node_id: str,
        show_related: bool = True,
        show_children: bool = True,
        show_parents: bool = True,
    ) -> "AgentView":
        """
        Focus on a single node with optional context.

        Args:
            node_id: Node to focus on
            show_related: Show nodes connected by edges
            show_children: Show child nodes
            show_parents: Show parent nodes
        """
        graph = self._get_graph()
        self.clear()

        node = graph.nodes.get(node_id)
        if not node:
            return self

        # Collect nodes to show
        nodes_to_show = [(node_id, node)]

        if show_children:
            for child_id in _get_children(graph, node_id):
                child = graph.nodes.get(child_id)
                if child:
                    nodes_to_show.append((child_id, child))

        if show_parents:
            parent_id = node.get("parent")
            if parent_id:
                parent = graph.nodes.get(parent_id)
                if parent:
                    nodes_to_show.insert(0, (parent_id, parent))

        if show_related:
            for edge in graph.edges:
                if edge.get("from") == node_id:
                    related = graph.nodes.get(edge.get("to"))
                    if related and (edge.get("to"), related) not in nodes_to_show:
                        nodes_to_show.append((edge.get("to"), related))
                elif edge.get("to") == node_id:
                    related = graph.nodes.get(edge.get("from"))
                    if related and (edge.get("from"), related) not in nodes_to_show:
                        nodes_to_show.append((edge.get("from"), related))

        # Layout: focused node in center, others around
        cx, cy = self.canvas["width"] // 2, self.canvas["height"] // 2

        # Add focused node
        self.add_node(
            node_id, x=cx - 60, y=cy - 16,
            label=node.get("label", node_id),
            node_type=node.get("type", "default"),
        )

        # Add others in a circle
        import math
        others = [(nid, n) for nid, n in nodes_to_show if nid != node_id]
        for i, (nid, n) in enumerate(others):
            angle = (2 * math.pi * i) / max(len(others), 1)
            radius = 200
            x = cx + radius * math.cos(angle) - 60
            y = cy + radius * math.sin(angle) - 16
            self.add_node(
                nid, x=x, y=y,
                label=n.get("label", nid),
                node_type=n.get("type", "default"),
            )

        # Add edges
        node_set = {nid for nid, _ in nodes_to_show}
        for edge in graph.edges:
            if edge.get("from") in node_set and edge.get("to") in node_set:
                self.add_edge(
                    edge.get("from"),
                    edge.get("to"),
                    edge_type=edge.get("type", "default").lower(),
                )

        return self

    def show_type(
        self,
        node_type: str,
        layout: Literal["grid", "horizontal", "vertical"] = "grid",
    ) -> "AgentView":
        """Show all nodes of a specific type."""
        graph = self._get_graph()
        node_ids = [nid for nid, n in graph.nodes.items() if n.get("type") == node_type]
        return self.show_nodes(node_ids, layout=layout)

    # === Render ===

    def render(self) -> "AgentView":
        """Write the view to the model."""
        model = self._read_model()

        if "views" not in model:
            model["views"] = {}

        model["views"][self.view_name] = {
            "canvas": self.canvas.copy(),
            "elements": self.elements.copy(),
            "styles": self.styles.copy(),
            "updated_at": datetime.now().isoformat(),
        }

        self._write_model(model)
        return self

    def load(self) -> "AgentView":
        """Load existing view state from model."""
        model = self._read_model()
        view = model.get("views", {}).get(self.view_name, {})

        self.canvas = view.get("canvas", self.canvas)
        self.elements = view.get("elements", [])
        self.styles = view.get("styles", self.styles)

        return self

    # === Info ===

    def get_element_count(self) -> int:
        """Get number of elements in view."""
        return len(self.elements)

    def get_node_ids(self) -> List[str]:
        """Get IDs of nodes currently in view."""
        return [
            e.get("data", {}).get("nodeId")
            for e in self.elements
            if e.get("type") == "rect" and e.get("data", {}).get("nodeId")
        ]


# === Helper Functions ===

def _default_styles() -> Dict[str, Dict[str, Any]]:
    return {
        "node-reality": {"fill": "#238636", "stroke": "#ffffff"},
        "node-subsystem": {"fill": "#3fb950", "stroke": "#ffffff"},
        "node-module": {"fill": "#6e7681", "stroke": "#ffffff"},
        "node-aspiration": {"fill": "#a371f7", "stroke": "#ffffff"},
        "node-gap": {"fill": "#f85149", "stroke": "#ffffff"},
        "node-todo": {"fill": "#d29922", "stroke": "#ffffff"},
        "node-concept": {"fill": "#58a6ff", "stroke": "#ffffff"},
        "node-default": {"fill": "#6e7681", "stroke": "#ffffff"},
        "edge-default": {"stroke": "#30363d", "strokeWidth": 1},
        "edge-contains": {"stroke": "#30363d", "strokeWidth": 2},
        "edge-uses": {"stroke": "#58a6ff", "strokeWidth": 1},
    }


def _get_children(graph, node_id: str) -> List[str]:
    """Get child node IDs."""
    children = []

    # Check CONTAINS edges
    for edge in graph.edges:
        if edge.get("type") == "CONTAINS" and edge.get("from") == node_id:
            children.append(edge.get("to"))

    # Check parent field
    for nid, node in graph.nodes.items():
        if node.get("parent") == node_id and nid not in children:
            children.append(nid)

    return children


def _layout_nodes(
    nodes: List[Tuple[str, Dict]],
    layout: str,
    canvas: Dict[str, int],
) -> List[Tuple[float, float]]:
    """Calculate positions for nodes."""
    positions = []

    if layout == "horizontal":
        spacing = canvas["width"] // (len(nodes) + 1)
        y = canvas["height"] // 2 - 16
        for i in range(len(nodes)):
            positions.append((50 + i * spacing, y))

    elif layout == "vertical":
        spacing = canvas["height"] // (len(nodes) + 1)
        x = canvas["width"] // 2 - 60
        for i in range(len(nodes)):
            positions.append((x, 50 + i * spacing))

    else:  # grid
        cols = max(1, int((canvas["width"] - 100) // 180))
        spacing_x = 180
        spacing_y = 70
        for i in range(len(nodes)):
            col = i % cols
            row = i // cols
            positions.append((50 + col * spacing_x, 50 + row * spacing_y))

    return positions


# === Quick Functions for Agents ===

def show_reality(reality_id: str, view_name: str = None) -> str:
    """Quick function to show a reality and its contents."""
    view_name = view_name or reality_id.replace("reality-", "")
    view = AgentView(view_name)
    view.show_hierarchy(reality_id, depth=3)
    view.render()
    return f"View '{view_name}' showing {view.get_element_count()} elements"


def show_focus(node_id: str, view_name: str = "focus") -> str:
    """Quick function to focus on a node."""
    view = AgentView(view_name)
    view.focus(node_id)
    view.render()
    return f"View '{view_name}' focused on {node_id}"


def list_views() -> List[str]:
    """List all available views."""
    with open(MODEL_PATH, encoding="utf-8") as f:
        model = json.load(f)
    return list(model.get("views", {}).keys())


# === CLI ===

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python agent_view.py <command> [args]")
        print("Commands:")
        print("  show-reality <reality-id>  - Show reality hierarchy")
        print("  focus <node-id>            - Focus on a node")
        print("  list                       - List views")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "show-reality" and len(sys.argv) >= 3:
        print(show_reality(sys.argv[2]))
    elif cmd == "focus" and len(sys.argv) >= 3:
        print(show_focus(sys.argv[2]))
    elif cmd == "list":
        for v in list_views():
            print(f"  - {v}")
    else:
        print(f"Unknown command: {cmd}")
