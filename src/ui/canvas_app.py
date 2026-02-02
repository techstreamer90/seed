#!/usr/bin/env python3
"""
Canvas App - The Stage Where Nodes Render Themselves

A simple, model-driven canvas application that:
1. Provides a drawing surface (the stage)
2. Reads the model to know what to display
3. Lets nodes render themselves using their view definitions
4. Eventually controlled by Schauspieler

Architecture:
- Canvas app is DUMB - just a stage
- Nodes render THEMSELVES using their view definitions
- Schauspieler coordinates (tells nodes where to render)
- Model is the source of truth

Usage:
    python src/ui/canvas_app.py
    python src/ui/canvas_app.py --view=main
    python src/ui/canvas_app.py --width=1200 --height=800
"""

import json
import tkinter as tk
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import argparse

MODEL_PATH = Path(__file__).parent.parent.parent / "model" / "sketch.json"


class CanvasApp:
    """A simple stage where nodes can render themselves."""

    def __init__(
        self,
        model_path: Path = None,
        view_name: str = "main",
        width: int = 1200,
        height: int = 800,
        background: str = "#0d1117"
    ):
        self.model_path = model_path or MODEL_PATH
        self.view_name = view_name
        self.default_width = width
        self.default_height = height
        self.default_background = background

        # Create window
        self.root = tk.Tk()
        self.root.title(f"Canvas - {view_name}")
        self.root.geometry(f"{width}x{height}")
        self.root.configure(bg=background)

        # Create canvas
        self.canvas = tk.Canvas(
            self.root,
            width=width,
            height=height,
            bg=background,
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # State
        self.elements = []
        self.last_update = None
        self.update_interval = 1000  # Check model every 1 second

        # Status bar
        self.status_label = tk.Label(
            self.root,
            text="Loading...",
            bg="#161b22",
            fg="#8b949e",
            font=("Consolas", 9),
            anchor="w",
            padx=10
        )
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def read_model(self) -> Dict[str, Any]:
        """Read the model from disk."""
        try:
            with open(self.model_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.update_status(f"Error reading model: {e}")
            return {}

    def get_view(self, model: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get the current view from the model."""
        views = model.get("views", {})
        return views.get(self.view_name)

    def render_view(self):
        """Read model and render the view."""
        model = self.read_model()
        if not model:
            return

        view = self.get_view(model)
        if not view:
            self.update_status(f"No view '{self.view_name}' in model")
            return

        # Check if view has been updated
        view_updated_at = view.get("updated_at")
        if view_updated_at == self.last_update:
            return  # No changes

        self.last_update = view_updated_at

        # Clear canvas
        self.canvas.delete("all")

        # Get canvas config
        canvas_config = view.get("canvas", {})
        bg = canvas_config.get("background", self.default_background)
        self.canvas.configure(bg=bg)

        # Get elements
        elements = view.get("elements", [])
        styles = view.get("styles", {})

        # Render each element
        element_count = 0
        for elem in elements:
            elem_type = elem.get("type")
            if elem_type == "rect":
                self.draw_rect(elem)
                element_count += 1
            elif elem_type == "line":
                self.draw_line(elem)
                element_count += 1
            elif elem_type == "text":
                self.draw_text(elem)
                element_count += 1

        self.update_status(
            f"View '{self.view_name}' | {element_count} elements | "
            f"Updated: {view_updated_at or 'unknown'}"
        )

    def draw_rect(self, elem: Dict[str, Any]):
        """Draw a rectangle element."""
        x = elem.get("x", 0)
        y = elem.get("y", 0)
        w = elem.get("w", 100)
        h = elem.get("h", 50)
        fill = elem.get("fill", "#6e7681")
        stroke = elem.get("stroke", "#ffffff")
        label = elem.get("label", "")

        # Draw rectangle
        self.canvas.create_rectangle(
            x, y, x + w, y + h,
            fill=fill,
            outline=stroke,
            width=2,
            tags=elem.get("id", "")
        )

        # Draw label if present
        if label:
            self.canvas.create_text(
                x + w / 2, y + h / 2,
                text=label,
                fill="#ffffff",
                font=("Arial", 10, "bold"),
                tags=f"{elem.get('id', '')}-label"
            )

    def draw_line(self, elem: Dict[str, Any]):
        """Draw a line element."""
        x1 = elem.get("x1", 0)
        y1 = elem.get("y1", 0)
        x2 = elem.get("x2", 100)
        y2 = elem.get("y2", 100)
        stroke = elem.get("stroke", "#30363d")
        stroke_width = elem.get("strokeWidth", 1)

        self.canvas.create_line(
            x1, y1, x2, y2,
            fill=stroke,
            width=stroke_width,
            tags=elem.get("id", "")
        )

    def draw_text(self, elem: Dict[str, Any]):
        """Draw a text element."""
        x = elem.get("x", 0)
        y = elem.get("y", 0)
        text = elem.get("text", "")
        fill = elem.get("fill", "#c9d1d9")
        font_str = elem.get("font", "12px sans-serif")
        align = elem.get("align", "center")

        # Parse font string (e.g., "12px sans-serif")
        font_size = 12
        font_family = "Arial"
        try:
            parts = font_str.split()
            if parts and "px" in parts[0]:
                font_size = int(parts[0].replace("px", ""))
            if len(parts) > 1:
                font_family = parts[1]
        except:
            pass

        # Map align to tkinter anchor
        anchor_map = {
            "left": tk.W,
            "center": tk.CENTER,
            "right": tk.E
        }
        anchor = anchor_map.get(align, tk.CENTER)

        self.canvas.create_text(
            x, y,
            text=text,
            fill=fill,
            font=(font_family, font_size),
            anchor=anchor,
            tags=elem.get("id", "")
        )

    def update_status(self, message: str):
        """Update status bar."""
        self.status_label.config(text=message)

    def check_for_updates(self):
        """Periodically check for model updates."""
        self.render_view()
        self.root.after(self.update_interval, self.check_for_updates)

    def run(self):
        """Start the canvas app."""
        self.render_view()  # Initial render
        self.check_for_updates()  # Start update loop
        self.root.mainloop()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Canvas App - The Stage Where Nodes Render Themselves")
    parser.add_argument(
        "--view",
        default="main",
        help="View name to display (default: main)"
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1200,
        help="Canvas width (default: 1200)"
    )
    parser.add_argument(
        "--height",
        type=int,
        default=800,
        help="Canvas height (default: 800)"
    )
    parser.add_argument(
        "--background",
        default="#0d1117",
        help="Background color (default: #0d1117)"
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=MODEL_PATH,
        help=f"Path to model file (default: {MODEL_PATH})"
    )

    args = parser.parse_args()

    app = CanvasApp(
        model_path=args.model,
        view_name=args.view,
        width=args.width,
        height=args.height,
        background=args.background
    )

    print(f"Canvas App starting...")
    print(f"  View: {args.view}")
    print(f"  Size: {args.width}x{args.height}")
    print(f"  Model: {args.model}")
    print()
    print("Reading from model and rendering...")

    app.run()


if __name__ == "__main__":
    main()
