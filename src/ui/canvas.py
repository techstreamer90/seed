#!/usr/bin/env python3
"""
Canvas API - Direct visual control for Claude.

Claude computes exact positions, sizes, colors.
UI just draws what's in the model.

Usage:
    from src.ui.canvas import canvas

    canvas.clear()
    canvas.rect("n1", x=100, y=50, w=120, h=36, fill="#238636", label="Root")
    canvas.line("e1", x1=220, y1=68, x2=300, y2=68, stroke="#58a6ff")
    canvas.text("t1", "USES", x=260, y=60)
    canvas.render()  # writes to model, UI picks it up
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

MODEL_PATH = Path(__file__).parent.parent.parent / "model" / "sketch.json"


class Canvas:
    """Direct canvas control - Claude computes, UI just draws."""

    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path or MODEL_PATH
        self.elements: List[Dict[str, Any]] = []
        self.styles: Dict[str, Dict[str, Any]] = {}
        self.canvas_config = {
            "width": 1200,
            "height": 800,
            "background": "#0d1117"
        }

        # Default styles
        self.styles = {
            "node-reality": {"fill": "#238636", "stroke": "#ffffff", "font": "12px sans-serif", "textFill": "#ffffff"},
            "node-subsystem": {"fill": "#3fb950", "stroke": "#ffffff", "font": "11px sans-serif", "textFill": "#ffffff"},
            "node-aspiration": {"fill": "#a371f7", "stroke": "#ffffff", "font": "12px sans-serif", "textFill": "#ffffff"},
            "node-gap": {"fill": "#f85149", "stroke": "#ffffff", "font": "12px sans-serif", "textFill": "#ffffff"},
            "node-todo": {"fill": "#d29922", "stroke": "#ffffff", "font": "11px sans-serif", "textFill": "#ffffff"},
            "node-concept": {"fill": "#58a6ff", "stroke": "#ffffff", "font": "11px sans-serif", "textFill": "#ffffff"},
            "node-default": {"fill": "#6e7681", "stroke": "#ffffff", "font": "11px sans-serif", "textFill": "#ffffff"},
            "edge-default": {"stroke": "#30363d", "strokeWidth": 1},
            "edge-contains": {"stroke": "#30363d", "strokeWidth": 2},
            "edge-uses": {"stroke": "#58a6ff", "strokeWidth": 1},
            "label-default": {"fill": "#6e7681", "font": "10px sans-serif"},
        }

    def _read_model(self) -> Dict[str, Any]:
        with open(self.model_path, encoding="utf-8") as f:
            return json.load(f)

    def _write_model(self, model: Dict[str, Any]) -> None:
        model["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(self.model_path, "w", encoding="utf-8") as f:
            json.dump(model, f, indent=2)

    def clear(self) -> "Canvas":
        """Clear all elements."""
        self.elements = []
        return self

    def size(self, width: int, height: int) -> "Canvas":
        """Set canvas size."""
        self.canvas_config["width"] = width
        self.canvas_config["height"] = height
        return self

    def background(self, color: str) -> "Canvas":
        """Set background color."""
        self.canvas_config["background"] = color
        return self

    def rect(
        self,
        id: str,
        x: float,
        y: float,
        w: float,
        h: float,
        fill: str = "#6e7681",
        stroke: str = "#ffffff",
        label: str = "",
        style: str = None,
        data: Dict[str, Any] = None,
    ) -> "Canvas":
        """Add a rectangle (node)."""
        elem = {
            "id": id,
            "type": "rect",
            "x": x, "y": y, "w": w, "h": h,
            "fill": fill,
            "stroke": stroke,
            "label": label,
        }
        if style:
            elem["style"] = style
        if data:
            elem["data"] = data
        self.elements.append(elem)
        return self

    def line(
        self,
        id: str,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        stroke: str = "#30363d",
        strokeWidth: float = 1,
        style: str = None,
    ) -> "Canvas":
        """Add a line (edge)."""
        elem = {
            "id": id,
            "type": "line",
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "stroke": stroke,
            "strokeWidth": strokeWidth,
        }
        if style:
            elem["style"] = style
        self.elements.append(elem)
        return self

    def text(
        self,
        id: str,
        text: str,
        x: float,
        y: float,
        fill: str = "#c9d1d9",
        font: str = "12px sans-serif",
        align: str = "center",
        style: str = None,
    ) -> "Canvas":
        """Add text."""
        elem = {
            "id": id,
            "type": "text",
            "text": text,
            "x": x, "y": y,
            "fill": fill,
            "font": font,
            "align": align,
        }
        if style:
            elem["style"] = style
        self.elements.append(elem)
        return self

    def node(
        self,
        node_id: str,
        x: float,
        y: float,
        label: str = None,
        node_type: str = "default",
        w: float = None,
        h: float = 32,
    ) -> "Canvas":
        """Add a node with automatic styling based on type."""
        style_key = f"node-{node_type.lower()}"
        if style_key not in self.styles:
            style_key = "node-default"

        style = self.styles[style_key]

        # Auto-calculate width based on label
        display_label = label or node_id
        if w is None:
            w = max(80, len(display_label) * 8 + 20)

        self.rect(
            id=f"node-{node_id}",
            x=x, y=y, w=w, h=h,
            fill=style["fill"],
            stroke=style["stroke"],
            label=display_label,
            data={"nodeId": node_id, "nodeType": node_type}
        )
        return self

    def edge(
        self,
        from_id: str,
        to_id: str,
        edge_type: str = "default",
        label: str = None,
    ) -> "Canvas":
        """Add an edge between two nodes (positions calculated from existing elements)."""
        # Find source and target nodes
        from_elem = next((e for e in self.elements if e.get("data", {}).get("nodeId") == from_id), None)
        to_elem = next((e for e in self.elements if e.get("data", {}).get("nodeId") == to_id), None)

        if not from_elem or not to_elem:
            return self  # Skip if nodes not found

        # Calculate edge endpoints (center-right of from, center-left of to)
        x1 = from_elem["x"] + from_elem["w"]
        y1 = from_elem["y"] + from_elem["h"] / 2
        x2 = to_elem["x"]
        y2 = to_elem["y"] + to_elem["h"] / 2

        style_key = f"edge-{edge_type.lower()}"
        if style_key not in self.styles:
            style_key = "edge-default"
        style = self.styles[style_key]

        self.line(
            id=f"edge-{from_id}-{to_id}",
            x1=x1, y1=y1, x2=x2, y2=y2,
            stroke=style["stroke"],
            strokeWidth=style.get("strokeWidth", 1),
        )

        # Add label if provided
        if label:
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2 - 8
            self.text(
                id=f"label-{from_id}-{to_id}",
                text=label,
                x=mid_x, y=mid_y,
                fill="#6e7681",
                font="10px sans-serif",
            )

        return self

    def render(self, view_name: str = "main") -> None:
        """Write the current canvas state to the model."""
        model = self._read_model()

        # Ensure views structure exists
        if "views" not in model:
            model["views"] = {}

        # Write the view
        model["views"][view_name] = {
            "canvas": self.canvas_config.copy(),
            "elements": self.elements.copy(),
            "styles": self.styles.copy(),
            "updated_at": datetime.now().isoformat(),
        }

        self._write_model(model)

    # === Layout Helpers (Claude computes positions) ===

    def layout_grid(
        self,
        node_ids: List[str],
        labels: Dict[str, str] = None,
        types: Dict[str, str] = None,
        cols: int = 4,
        spacing_x: float = 160,
        spacing_y: float = 60,
        start_x: float = 50,
        start_y: float = 50,
    ) -> "Canvas":
        """Layout nodes in a grid."""
        labels = labels or {}
        types = types or {}

        for i, node_id in enumerate(node_ids):
            col = i % cols
            row = i // cols
            x = start_x + col * spacing_x
            y = start_y + row * spacing_y

            self.node(
                node_id=node_id,
                x=x, y=y,
                label=labels.get(node_id, node_id),
                node_type=types.get(node_id, "default"),
            )

        return self

    def layout_tree(
        self,
        root_id: str,
        children: Dict[str, List[str]],
        labels: Dict[str, str] = None,
        types: Dict[str, str] = None,
        spacing_x: float = 180,
        spacing_y: float = 80,
        start_x: float = 100,
        start_y: float = 50,
    ) -> "Canvas":
        """Layout nodes as a tree (top-down)."""
        labels = labels or {}
        types = types or {}

        # BFS to assign levels
        levels: Dict[str, int] = {root_id: 0}
        queue = [root_id]
        while queue:
            node = queue.pop(0)
            for child in children.get(node, []):
                if child not in levels:
                    levels[child] = levels[node] + 1
                    queue.append(child)

        # Group by level
        by_level: Dict[int, List[str]] = {}
        for node, level in levels.items():
            by_level.setdefault(level, []).append(node)

        # Position nodes
        positions: Dict[str, Tuple[float, float]] = {}
        for level, nodes in sorted(by_level.items()):
            y = start_y + level * spacing_y
            total_width = (len(nodes) - 1) * spacing_x
            start = start_x + (600 - total_width) / 2  # Center horizontally

            for i, node_id in enumerate(nodes):
                x = start + i * spacing_x
                positions[node_id] = (x, y)

                self.node(
                    node_id=node_id,
                    x=x, y=y,
                    label=labels.get(node_id, node_id),
                    node_type=types.get(node_id, "default"),
                )

        # Add edges
        for parent, kids in children.items():
            for child in kids:
                if parent in positions and child in positions:
                    self.edge(parent, child, edge_type="contains")

        return self

    def check_overlaps(self) -> List[Tuple[str, str]]:
        """Check for overlapping elements. Returns list of overlapping pairs."""
        overlaps = []
        rects = [e for e in self.elements if e["type"] == "rect"]

        for i, r1 in enumerate(rects):
            for r2 in rects[i+1:]:
                # Check AABB overlap
                if (r1["x"] < r2["x"] + r2["w"] and
                    r1["x"] + r1["w"] > r2["x"] and
                    r1["y"] < r2["y"] + r2["h"] and
                    r1["y"] + r1["h"] > r2["y"]):
                    overlaps.append((r1["id"], r2["id"]))

        return overlaps

    def auto_spread(self, min_gap: float = 20) -> "Canvas":
        """Automatically spread overlapping nodes apart."""
        rects = [e for e in self.elements if e["type"] == "rect"]

        # Simple iterative push-apart
        for _ in range(10):  # Max iterations
            moved = False
            for i, r1 in enumerate(rects):
                for r2 in rects[i+1:]:
                    # Check overlap
                    overlap_x = min(r1["x"] + r1["w"], r2["x"] + r2["w"]) - max(r1["x"], r2["x"])
                    overlap_y = min(r1["y"] + r1["h"], r2["y"] + r2["h"]) - max(r1["y"], r2["y"])

                    if overlap_x > -min_gap and overlap_y > -min_gap:
                        # Push apart
                        if overlap_x < overlap_y:
                            push = (overlap_x + min_gap) / 2
                            if r1["x"] < r2["x"]:
                                r1["x"] -= push
                                r2["x"] += push
                            else:
                                r1["x"] += push
                                r2["x"] -= push
                        else:
                            push = (overlap_y + min_gap) / 2
                            if r1["y"] < r2["y"]:
                                r1["y"] -= push
                                r2["y"] += push
                            else:
                                r1["y"] += push
                                r2["y"] -= push
                        moved = True

            if not moved:
                break

        return self

    def from_model(self, view_name: str = "main") -> "Canvas":
        """Load canvas state from model."""
        model = self._read_model()
        view = model.get("views", {}).get(view_name, {})

        self.canvas_config = view.get("canvas", self.canvas_config)
        self.elements = view.get("elements", [])
        self.styles = view.get("styles", self.styles)

        return self

    def capture(self) -> Path:
        """Capture the current UI window."""
        from src.ui.capture_window import capture_window
        return capture_window()


# Global instance
canvas = Canvas()


# === Quick functions for common operations ===

def draw_model(view_name: str = "main") -> str:
    """Draw the entire model as a visual."""
    from src.ui.quick_query import _get_graph

    graph = _get_graph()
    c = Canvas()

    # Get all nodes grouped by type
    nodes_by_type: Dict[str, List[tuple]] = {}
    for nid, node in graph.nodes.items():
        ntype = node.get("type", "Unknown")
        nodes_by_type.setdefault(ntype, []).append((nid, node))

    # Layout: Realities on top, then others below
    y = 50
    x_start = 50
    spacing_x = 180
    spacing_y = 70

    priority_types = ["Reality", "Subsystem", "Aspiration", "Gap", "Todo", "Concept"]

    for ntype in priority_types:
        if ntype not in nodes_by_type:
            continue

        nodes = nodes_by_type[ntype]
        x = x_start

        for nid, node in sorted(nodes, key=lambda x: (x[1].get("label") or x[0]).lower()):
            label = node.get("label") or nid
            c.node(nid, x=x, y=y, label=label, node_type=ntype)
            x += spacing_x

            if x > 1000:  # Wrap to next row
                x = x_start
                y += spacing_y

        y += spacing_y + 20  # Gap between types

    # Add edges
    for edge in graph.edges:
        c.edge(edge.get("from"), edge.get("to"), edge_type=edge.get("type", "default").lower())

    # Check and fix overlaps
    c.auto_spread()

    # Render
    c.render(view_name)

    return f"Drew {len(graph.nodes)} nodes, {len(graph.edges)} edges to view '{view_name}'"


def draw_clean_layout(view_name: str = "main") -> str:
    """Draw a clean, readable layout with proper spacing by type."""
    from src.ui.quick_query import _get_graph

    graph = _get_graph()
    c = Canvas()
    c.size(1600, 1200)

    # Group nodes by type
    nodes_by_type: Dict[str, List[tuple]] = {}
    for nid, node in graph.nodes.items():
        ntype = node.get("type", "Unknown")
        nodes_by_type.setdefault(ntype, []).append((nid, node))

    # Layout with good spacing
    y = 50
    x_start = 50
    spacing_x = 200
    spacing_y = 70
    max_x = 1500

    # Priority order for types
    priority_types = ["Reality", "Subsystem", "Module", "Aspiration", "Gap", "Todo", "Concept"]

    for ntype in priority_types:
        if ntype not in nodes_by_type:
            continue

        nodes = sorted(nodes_by_type[ntype], key=lambda x: (x[1].get("label") or x[0]).lower())
        x = x_start

        for nid, node in nodes:
            label = node.get("label") or nid
            c.node(nid, x=x, y=y, label=label, node_type=ntype)
            x += spacing_x

            if x > max_x:
                x = x_start
                y += spacing_y

        y += spacing_y + 20  # Gap between types

    # Add edges
    for edge in graph.edges:
        c.edge(edge.get("from"), edge.get("to"), edge_type=edge.get("type", "default").lower())

    c.render(view_name)
    return f"Drew {len(graph.nodes)} nodes, {len(graph.edges)} edges to view '{view_name}'"


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "draw":
        print(draw_clean_layout())
    elif len(sys.argv) > 1 and sys.argv[1] == "draw-raw":
        print(draw_model())
    else:
        print("Usage: python canvas.py draw|draw-raw")
