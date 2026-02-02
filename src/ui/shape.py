#!/usr/bin/env python3
"""
Shape - Self-contained visual representation for nodes.

Each node can create its own Shape - a visual component with:
- Relative coordinates (origin at 0,0)
- Bounding box (width, height)
- Visual elements (rects, lines, text)
- Metadata (capabilities, state)

Shapes are composed by the orchestrator (Main Schauspieler) who places them
and manages interactions.

The Vision:
- Dog node creates Dog shape
- Tree node creates Tree shape
- Orchestrator places both, detects collision
- Quality of interaction depends on quality of each shape

Usage:
    from src.ui.shape import Shape

    # Node creates its own shape
    dog = Shape("dog", node_id="node-dog")
    dog.add_rect(0, 0, 50, 40, fill="#ff9800", label="🐕")
    dog.set_capability("movable", True)
    dog.set_capability("velocity", {"x": 5, "y": 0})
    dog.save()

    # Orchestrator places and composes
    from src.ui.composer import Composer
    composer = Composer("main-view")
    composer.add_shape("dog", x=100, y=100)
    composer.add_shape("tree", x=200, y=100)
    composer.detect_interactions()
    composer.render()
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

MODEL_PATH = Path(__file__).parent.parent.parent / "model" / "sketch.json"


class Shape:
    """Self-contained visual representation for a node."""

    def __init__(self, shape_id: str, node_id: str = None, model_path: Optional[Path] = None):
        """
        Create a shape.

        Args:
            shape_id: Unique ID for this shape
            node_id: Node this shape represents (optional)
            model_path: Optional custom model path
        """
        self.shape_id = shape_id
        self.node_id = node_id
        self.model_path = model_path or MODEL_PATH

        # Shape definition (relative coords)
        self.elements: List[Dict[str, Any]] = []
        self.bounds = {"w": 100, "h": 100}  # Default bounds

        # Metadata
        self.capabilities: Dict[str, Any] = {}
        self.state: Dict[str, Any] = {}

        # Visual defaults
        self.anchor = {"x": 0, "y": 0}  # Anchor point for placement

    # === Elements (relative coords) ===

    def add_rect(
        self,
        x: float, y: float,
        w: float, h: float,
        fill: str = "#6e7681",
        stroke: str = "#ffffff",
        label: str = "",
        **kwargs
    ) -> "Shape":
        """Add a rectangle element (relative coords)."""
        elem = {
            "type": "rect",
            "x": x, "y": y, "w": w, "h": h,
            "fill": fill, "stroke": stroke,
        }
        if label:
            elem["label"] = label
        elem.update(kwargs)
        self.elements.append(elem)
        return self

    def add_line(
        self,
        x1: float, y1: float,
        x2: float, y2: float,
        stroke: str = "#30363d",
        strokeWidth: float = 1,
        **kwargs
    ) -> "Shape":
        """Add a line element (relative coords)."""
        elem = {
            "type": "line",
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "stroke": stroke, "strokeWidth": strokeWidth,
        }
        elem.update(kwargs)
        self.elements.append(elem)
        return self

    def add_text(
        self,
        x: float, y: float,
        text: str,
        fill: str = "#c9d1d9",
        font: str = "12px sans-serif",
        **kwargs
    ) -> "Shape":
        """Add a text element (relative coords)."""
        elem = {
            "type": "text",
            "x": x, "y": y,
            "text": text,
            "fill": fill, "font": font,
        }
        elem.update(kwargs)
        self.elements.append(elem)
        return self

    def add_circle(
        self,
        cx: float, cy: float,
        r: float,
        fill: str = "#6e7681",
        stroke: str = "#ffffff",
        **kwargs
    ) -> "Shape":
        """Add a circle element (relative coords)."""
        elem = {
            "type": "circle",
            "cx": cx, "cy": cy, "r": r,
            "fill": fill, "stroke": stroke,
        }
        elem.update(kwargs)
        self.elements.append(elem)
        return self

    # === Bounds ===

    def set_bounds(self, w: float, h: float) -> "Shape":
        """Set the bounding box for this shape."""
        self.bounds = {"w": w, "h": h}
        return self

    def auto_calculate_bounds(self) -> "Shape":
        """Calculate bounds from elements (finds min/max)."""
        if not self.elements:
            return self

        max_x = max_y = 0
        for elem in self.elements:
            if elem["type"] == "rect":
                max_x = max(max_x, elem["x"] + elem["w"])
                max_y = max(max_y, elem["y"] + elem["h"])
            elif elem["type"] == "circle":
                max_x = max(max_x, elem["cx"] + elem["r"])
                max_y = max(max_y, elem["cy"] + elem["r"])
            elif elem["type"] == "text":
                # Rough estimate
                max_x = max(max_x, elem["x"] + len(elem.get("text", "")) * 6)
                max_y = max(max_y, elem["y"] + 12)

        self.bounds = {"w": max_x, "h": max_y}
        return self

    def set_anchor(self, x: float, y: float) -> "Shape":
        """Set anchor point (default 0,0 = top-left)."""
        self.anchor = {"x": x, "y": y}
        return self

    # === Capabilities & State ===

    def set_capability(self, key: str, value: Any) -> "Shape":
        """Set a capability (movable, collidable, velocity, etc.)."""
        self.capabilities[key] = value
        return self

    def get_capability(self, key: str) -> Any:
        """Get a capability value."""
        return self.capabilities.get(key)

    def set_state(self, key: str, value: Any) -> "Shape":
        """Set state (position, animation frame, etc.)."""
        self.state[key] = value
        return self

    def get_state(self, key: str) -> Any:
        """Get state value."""
        return self.state.get(key)

    # === Serialization ===

    def to_dict(self) -> Dict[str, Any]:
        """Convert shape to dictionary."""
        return {
            "id": self.shape_id,
            "node_id": self.node_id,
            "bounds": self.bounds.copy(),
            "anchor": self.anchor.copy(),
            "elements": [e.copy() for e in self.elements],
            "capabilities": self.capabilities.copy(),
            "state": self.state.copy(),
            "updated_at": datetime.now().isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], model_path: Optional[Path] = None) -> "Shape":
        """Create shape from dictionary."""
        shape = cls(data["id"], data.get("node_id"), model_path)
        shape.bounds = data.get("bounds", {"w": 100, "h": 100})
        shape.anchor = data.get("anchor", {"x": 0, "y": 0})
        shape.elements = data.get("elements", [])
        shape.capabilities = data.get("capabilities", {})
        shape.state = data.get("state", {})
        return shape

    # === Persistence ===

    def save(self) -> "Shape":
        """Save shape to model.shapes registry."""
        with open(self.model_path, encoding="utf-8") as f:
            model = json.load(f)

        if "shapes" not in model:
            model["shapes"] = {}

        model["shapes"][self.shape_id] = self.to_dict()
        model["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

        with open(self.model_path, "w", encoding="utf-8") as f:
            json.dump(model, f, indent=2)

        return self

    @classmethod
    def load(cls, shape_id: str, model_path: Optional[Path] = None) -> Optional["Shape"]:
        """Load shape from model.shapes registry."""
        model_path = model_path or MODEL_PATH

        with open(model_path, encoding="utf-8") as f:
            model = json.load(f)

        shape_data = model.get("shapes", {}).get(shape_id)
        if not shape_data:
            return None

        return cls.from_dict(shape_data, model_path)

    def delete(self) -> None:
        """Delete shape from model."""
        with open(self.model_path, encoding="utf-8") as f:
            model = json.load(f)

        if "shapes" in model and self.shape_id in model["shapes"]:
            del model["shapes"][self.shape_id]
            model["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

            with open(self.model_path, "w", encoding="utf-8") as f:
                json.dump(model, f, indent=2)

    # === Helpers ===

    def clear(self) -> "Shape":
        """Clear all elements."""
        self.elements = []
        return self

    def clone(self, new_id: str) -> "Shape":
        """Create a copy of this shape with a new ID."""
        new_shape = Shape(new_id, self.node_id, self.model_path)
        new_shape.bounds = self.bounds.copy()
        new_shape.anchor = self.anchor.copy()
        new_shape.elements = [e.copy() for e in self.elements]
        new_shape.capabilities = self.capabilities.copy()
        new_shape.state = self.state.copy()
        return new_shape


# === Helper Functions ===

def list_shapes(model_path: Optional[Path] = None) -> List[str]:
    """List all shape IDs in the model."""
    model_path = model_path or MODEL_PATH

    with open(model_path, encoding="utf-8") as f:
        model = json.load(f)

    return list(model.get("shapes", {}).keys())


def get_shapes_for_node(node_id: str, model_path: Optional[Path] = None) -> List[str]:
    """Get all shape IDs associated with a node."""
    model_path = model_path or MODEL_PATH

    with open(model_path, encoding="utf-8") as f:
        model = json.load(f)

    shapes = []
    for shape_id, shape_data in model.get("shapes", {}).items():
        if shape_data.get("node_id") == node_id:
            shapes.append(shape_id)

    return shapes


# CLI
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Shape - Self-contained visual representation")
        print()
        print("Commands:")
        print("  list                  - List all shapes")
        print("  show <shape_id>       - Show shape details")
        print("  delete <shape_id>     - Delete a shape")
        print("  node <node_id>        - List shapes for a node")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "list":
        for shape_id in list_shapes():
            print(f"  {shape_id}")

    elif cmd == "show" and len(sys.argv) >= 3:
        shape = Shape.load(sys.argv[2])
        if shape:
            print(json.dumps(shape.to_dict(), indent=2))
        else:
            print(f"Shape '{sys.argv[2]}' not found")

    elif cmd == "delete" and len(sys.argv) >= 3:
        shape = Shape.load(sys.argv[2])
        if shape:
            shape.delete()
            print(f"Deleted shape '{sys.argv[2]}'")
        else:
            print(f"Shape '{sys.argv[2]}' not found")

    elif cmd == "node" and len(sys.argv) >= 3:
        shapes = get_shapes_for_node(sys.argv[2])
        print(f"Shapes for {sys.argv[2]}:")
        for shape_id in shapes:
            print(f"  {shape_id}")

    else:
        print(f"Unknown command: {cmd}")
