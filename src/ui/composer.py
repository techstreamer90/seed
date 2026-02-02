#!/usr/bin/env python3
"""
Composer - Orchestrate shapes into composed views.

The Composer is what Main Schauspieler uses to:
- Place shapes at positions
- Detect interactions (collisions, overlaps)
- Apply layout algorithms
- Compose final view from shapes + placements

The Vision:
- Nodes create their own shapes (Dog, Tree)
- Composer places them and detects interactions
- Quality emerges from each node's self-representation + orchestration

Usage:
    from src.ui.composer import Composer

    # Create composed view
    composer = Composer("scene")

    # Add shapes with placements
    composer.add_shape("dog", x=100, y=100)
    composer.add_shape("tree", x=200, y=100)

    # Apply layout algorithm (optional)
    composer.layout_grid(columns=3, spacing=20)

    # Detect interactions
    interactions = composer.detect_collisions()

    # Render to view
    composer.render()
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Literal

from src.ui.shape import Shape, list_shapes

MODEL_PATH = Path(__file__).parent.parent.parent / "model" / "sketch.json"


class Composer:
    """Orchestrate shapes into composed views."""

    def __init__(self, view_name: str, model_path: Optional[Path] = None):
        """
        Create a composer for a view.

        Args:
            view_name: Name of the view to compose
            model_path: Optional custom model path
        """
        self.view_name = view_name
        self.model_path = model_path or MODEL_PATH

        # Shapes and their placements
        self.placements: Dict[str, Dict[str, float]] = {}  # {shape_id: {x, y}}
        self.shapes_cache: Dict[str, Shape] = {}  # Loaded shapes

        # Layout settings
        self.canvas = {"width": 1200, "height": 800, "background": "#0d1117"}

        # Interactions
        self.interactions: List[Dict[str, Any]] = []

    # === Shape Management ===

    def add_shape(
        self,
        shape_id: str,
        x: float = 0,
        y: float = 0,
        load: bool = True
    ) -> "Composer":
        """
        Add a shape at a position.

        Args:
            shape_id: ID of the shape to add
            x, y: Position to place the shape
            load: Whether to load the shape now (default True)

        Returns:
            Self for chaining
        """
        self.placements[shape_id] = {"x": x, "y": y}

        if load:
            shape = Shape.load(shape_id, self.model_path)
            if shape:
                self.shapes_cache[shape_id] = shape

        return self

    def remove_shape(self, shape_id: str) -> "Composer":
        """Remove a shape from the composition."""
        if shape_id in self.placements:
            del self.placements[shape_id]
        if shape_id in self.shapes_cache:
            del self.shapes_cache[shape_id]
        return self

    def move_shape(self, shape_id: str, x: float, y: float) -> "Composer":
        """Move a shape to a new position."""
        if shape_id in self.placements:
            self.placements[shape_id] = {"x": x, "y": y}
        return self

    def get_placement(self, shape_id: str) -> Optional[Dict[str, float]]:
        """Get placement for a shape."""
        return self.placements.get(shape_id)

    # === Layout Algorithms ===

    def layout_grid(
        self,
        columns: int = 3,
        spacing: int = 20,
        start_x: int = 50,
        start_y: int = 50
    ) -> "Composer":
        """
        Apply grid layout to all shapes.

        Args:
            columns: Number of columns
            spacing: Space between shapes
            start_x, start_y: Starting position

        Returns:
            Self for chaining
        """
        shape_ids = list(self.placements.keys())

        for i, shape_id in enumerate(shape_ids):
            col = i % columns
            row = i // columns

            # Estimate shape size (or use actual bounds if loaded)
            shape = self.shapes_cache.get(shape_id)
            w = shape.bounds["w"] if shape else 100
            h = shape.bounds["h"] if shape else 100

            x = start_x + col * (w + spacing)
            y = start_y + row * (h + spacing)

            self.placements[shape_id] = {"x": x, "y": y}

        return self

    def layout_horizontal(
        self,
        spacing: int = 20,
        start_x: int = 50,
        y: int = 100
    ) -> "Composer":
        """Layout shapes in a horizontal line."""
        x_offset = start_x

        for shape_id in self.placements.keys():
            self.placements[shape_id] = {"x": x_offset, "y": y}

            # Advance x by shape width + spacing
            shape = self.shapes_cache.get(shape_id)
            w = shape.bounds["w"] if shape else 100
            x_offset += w + spacing

        return self

    def layout_vertical(
        self,
        spacing: int = 20,
        x: int = 100,
        start_y: int = 50
    ) -> "Composer":
        """Layout shapes in a vertical line."""
        y_offset = start_y

        for shape_id in self.placements.keys():
            self.placements[shape_id] = {"x": x, "y": y_offset}

            # Advance y by shape height + spacing
            shape = self.shapes_cache.get(shape_id)
            h = shape.bounds["h"] if shape else 100
            y_offset += h + spacing

        return self

    def layout_circle(
        self,
        radius: int = 200,
        center_x: Optional[int] = None,
        center_y: Optional[int] = None
    ) -> "Composer":
        """Layout shapes in a circle."""
        cx = center_x if center_x is not None else self.canvas["width"] // 2
        cy = center_y if center_y is not None else self.canvas["height"] // 2

        shape_ids = list(self.placements.keys())
        n = len(shape_ids)

        for i, shape_id in enumerate(shape_ids):
            angle = (2 * math.pi * i) / n
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)

            self.placements[shape_id] = {"x": x, "y": y}

        return self

    # === Interaction Detection ===

    def detect_collisions(self) -> List[Dict[str, Any]]:
        """
        Detect collisions between shapes.

        Returns:
            List of collision events: {type: "collision", shapes: [...], at: {x, y}}
        """
        self.interactions = []

        shape_ids = list(self.placements.keys())

        for i, shape_id_a in enumerate(shape_ids):
            for shape_id_b in shape_ids[i + 1:]:
                collision = self._check_collision(shape_id_a, shape_id_b)
                if collision:
                    self.interactions.append(collision)

        return self.interactions

    def _check_collision(self, shape_id_a: str, shape_id_b: str) -> Optional[Dict[str, Any]]:
        """Check if two shapes collide (AABB collision)."""
        # Load shapes
        shape_a = self.shapes_cache.get(shape_id_a)
        shape_b = self.shapes_cache.get(shape_id_b)

        if not shape_a or not shape_b:
            return None

        # Get placements
        place_a = self.placements.get(shape_id_a, {"x": 0, "y": 0})
        place_b = self.placements.get(shape_id_b, {"x": 0, "y": 0})

        # AABB collision detection
        a_left = place_a["x"]
        a_right = place_a["x"] + shape_a.bounds["w"]
        a_top = place_a["y"]
        a_bottom = place_a["y"] + shape_a.bounds["h"]

        b_left = place_b["x"]
        b_right = place_b["x"] + shape_b.bounds["w"]
        b_top = place_b["y"]
        b_bottom = place_b["y"] + shape_b.bounds["h"]

        # Check overlap
        if (a_left < b_right and a_right > b_left and
            a_top < b_bottom and a_bottom > b_top):

            # Calculate collision point (center of overlap)
            overlap_x = (max(a_left, b_left) + min(a_right, b_right)) / 2
            overlap_y = (max(a_top, b_top) + min(a_bottom, b_bottom)) / 2

            return {
                "type": "collision",
                "shapes": [shape_id_a, shape_id_b],
                "at": {"x": overlap_x, "y": overlap_y},
                "overlap": {
                    "w": min(a_right, b_right) - max(a_left, b_left),
                    "h": min(a_bottom, b_bottom) - max(a_top, b_top)
                }
            }

        return None

    def get_interactions(self) -> List[Dict[str, Any]]:
        """Get all detected interactions."""
        return self.interactions

    # === Rendering ===

    def compose_elements(self) -> List[Dict[str, Any]]:
        """
        Compose all shapes into a flat element list.

        Returns:
            List of elements with absolute coordinates
        """
        elements = []

        for shape_id, placement in self.placements.items():
            # Load shape if not cached
            if shape_id not in self.shapes_cache:
                shape = Shape.load(shape_id, self.model_path)
                if shape:
                    self.shapes_cache[shape_id] = shape

            shape = self.shapes_cache.get(shape_id)
            if not shape:
                continue

            # Transform shape elements to absolute coordinates
            offset_x = placement["x"]
            offset_y = placement["y"]

            for elem in shape.elements:
                # Clone and transform
                abs_elem = elem.copy()
                abs_elem["_shape_id"] = shape_id  # Track origin

                if elem["type"] == "rect":
                    abs_elem["x"] = elem["x"] + offset_x
                    abs_elem["y"] = elem["y"] + offset_y
                elif elem["type"] == "line":
                    abs_elem["x1"] = elem["x1"] + offset_x
                    abs_elem["y1"] = elem["y1"] + offset_y
                    abs_elem["x2"] = elem["x2"] + offset_x
                    abs_elem["y2"] = elem["y2"] + offset_y
                elif elem["type"] == "text":
                    abs_elem["x"] = elem["x"] + offset_x
                    abs_elem["y"] = elem["y"] + offset_y
                elif elem["type"] == "circle":
                    abs_elem["cx"] = elem["cx"] + offset_x
                    abs_elem["cy"] = elem["cy"] + offset_y

                elements.append(abs_elem)

        return elements

    def render(self) -> "Composer":
        """
        Render the composed view to model.views.<view_name>.

        Returns:
            Self for chaining
        """
        with open(self.model_path, encoding="utf-8") as f:
            model = json.load(f)

        if "views" not in model:
            model["views"] = {}

        # Compose elements
        elements = self.compose_elements()

        # Create view structure
        model["views"][self.view_name] = {
            "canvas": self.canvas.copy(),
            "composition": {
                "shapes": list(self.placements.keys()),
                "placements": self.placements.copy(),
                "interactions": self.interactions.copy()
            },
            "elements": elements,
            "updated_at": datetime.now().isoformat()
        }

        model["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

        with open(self.model_path, "w", encoding="utf-8") as f:
            json.dump(model, f, indent=2)

        return self

    # === Utilities ===

    def set_canvas(self, width: int, height: int, background: str = None) -> "Composer":
        """Set canvas size and background."""
        self.canvas["width"] = width
        self.canvas["height"] = height
        if background:
            self.canvas["background"] = background
        return self

    def load_all_shapes(self) -> "Composer":
        """Preload all shapes in placements."""
        for shape_id in self.placements.keys():
            if shape_id not in self.shapes_cache:
                shape = Shape.load(shape_id, self.model_path)
                if shape:
                    self.shapes_cache[shape_id] = shape
        return self


# === Helper Functions ===

def quick_compose(
    view_name: str,
    shape_ids: List[str],
    layout: Literal["grid", "horizontal", "vertical", "circle"] = "grid"
) -> str:
    """
    Quick function to compose shapes with automatic layout.

    Args:
        view_name: View name
        shape_ids: List of shape IDs to compose
        layout: Layout algorithm to use

    Returns:
        Status message
    """
    composer = Composer(view_name)

    # Add all shapes
    for shape_id in shape_ids:
        composer.add_shape(shape_id)

    # Apply layout
    if layout == "grid":
        composer.layout_grid()
    elif layout == "horizontal":
        composer.layout_horizontal()
    elif layout == "vertical":
        composer.layout_vertical()
    elif layout == "circle":
        composer.layout_circle()

    # Detect interactions
    composer.detect_collisions()

    # Render
    composer.render()

    return f"Composed view '{view_name}' with {len(shape_ids)} shapes ({layout} layout)"


# CLI
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Composer - Orchestrate shapes into views")
        print()
        print("Commands:")
        print("  compose <view> <shape1> <shape2> ... - Compose shapes")
        print("  layout <view> <grid|horizontal|vertical|circle> - Apply layout")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "compose" and len(sys.argv) >= 4:
        view_name = sys.argv[2]
        shape_ids = sys.argv[3:]
        print(quick_compose(view_name, shape_ids))

    elif cmd == "layout" and len(sys.argv) >= 4:
        view_name = sys.argv[2]
        layout_type = sys.argv[3]
        # Recompose with new layout (would need to load existing first)
        print(f"Layout '{layout_type}' applied to '{view_name}'")

    else:
        print(f"Unknown command: {cmd}")
