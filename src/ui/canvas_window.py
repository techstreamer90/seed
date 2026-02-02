"""
Canvas Window - Input Capture & Agent Display

A window that displays agent bitmaps from .state/render/ directory.
Also captures mouse clicks and keyboard input.
Events are written to .state/canvas_events.json for nodes to consume.

Watches .state/render/ for PNG files and auto-refreshes when they change.

Usage:
    python src/ui/canvas_window.py
"""

import tkinter as tk
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageTk
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.ui.broadcast import broadcast


class CanvasWindow:
    """Window that displays agent bitmaps and captures input."""

    def __init__(self, width=800, height=600):
        self.root = tk.Tk()
        self.root.title("Canvas - Agent Display")

        # Create canvas
        self.canvas = tk.Canvas(
            self.root,
            width=width,
            height=height,
            bg='white',
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Chat input at bottom
        self.chat_entry = tk.Entry(self.root, font=('Arial', 12))
        self.chat_entry.pack(side=tk.BOTTOM, fill=tk.X)
        self.chat_entry.bind("<Return>", self._send_chat)

        # Events storage
        self.events = []
        self.events_file = Path(__file__).parent.parent.parent / ".state" / "canvas_events.json"

        # Render directory for agent bitmaps
        self.render_dir = Path(__file__).parent.parent.parent / ".state" / "render"

        # Image tracking
        self.loaded_images = {}  # filename -> PhotoImage
        self.image_objects = {}  # filename -> canvas image id
        self.last_modified = {}  # filename -> timestamp

        # Ensure directories exist
        self.events_file.parent.mkdir(exist_ok=True)
        self.render_dir.mkdir(exist_ok=True)

        # Initialize events file
        self._save_events()

        # Bind input events
        self.canvas.bind("<Button-1>", self._on_click)
        self.root.bind("<KeyPress>", self._on_keypress)

        # Focus canvas for keyboard events
        self.canvas.focus_set()

        # Load initial images
        self._load_images()

        # Start periodic refresh (check for new/updated images every 500ms)
        self._schedule_refresh()

        print(f"Canvas Window started")
        print(f"Size: {width}x{height}")
        print(f"Events file: {self.events_file}")
        print(f"Render dir: {self.render_dir}")
        print(f"Click anywhere or press keys to capture input")

    def _on_click(self, event):
        """Capture mouse click."""
        click_event = {
            "type": "click",
            "x": event.x,
            "y": event.y,
            "timestamp": datetime.now().isoformat()
        }
        self.events.append(click_event)
        self._save_events()
        print(f"Click: ({event.x}, {event.y})")

    def _on_keypress(self, event):
        """Capture keyboard input."""
        key_event = {
            "type": "keypress",
            "key": event.char if event.char else event.keysym,
            "keysym": event.keysym,
            "timestamp": datetime.now().isoformat()
        }
        self.events.append(key_event)
        self._save_events()
        print(f"Key: {event.char if event.char else event.keysym}")

    def _send_chat(self, event):
        """Send chat message to broadcast system."""
        message = self.chat_entry.get()
        if message.strip():
            broadcast.send("user", message)
            print(f"Broadcast: {message}")
            self.chat_entry.delete(0, tk.END)
        # Return focus to canvas for input capture
        self.canvas.focus_set()
        return "break"  # Prevent default behavior

    def _save_events(self):
        """Write events to file."""
        with open(self.events_file, 'w') as f:
            json.dump({"events": self.events}, f, indent=2)

    def _load_images(self):
        """Load all PNG files from render directory and display them."""
        if not self.render_dir.exists():
            return

        # Get all PNG files
        png_files = sorted(self.render_dir.glob("*.png"))

        # Track which files we've seen
        current_files = set()

        for png_path in png_files:
            filename = png_path.name
            current_files.add(filename)

            # Check if file is new or modified
            try:
                mtime = png_path.stat().st_mtime
                if filename not in self.last_modified or self.last_modified[filename] != mtime:
                    # Load/reload the image
                    self._load_single_image(png_path, filename, mtime)
            except Exception as e:
                print(f"Error loading {filename}: {e}")

        # Remove images that no longer exist
        removed_files = set(self.loaded_images.keys()) - current_files
        for filename in removed_files:
            self._remove_image(filename)

        # Redraw canvas with current images
        self._redraw_canvas()

    def _load_single_image(self, png_path, filename, mtime):
        """Load a single PNG image."""
        try:
            # Load image with PIL
            pil_image = Image.open(png_path)

            # Convert to PhotoImage for tkinter
            photo_image = ImageTk.PhotoImage(pil_image)

            # Store the image (keep reference to prevent garbage collection)
            self.loaded_images[filename] = photo_image
            self.last_modified[filename] = mtime

            print(f"Loaded: {filename} ({pil_image.width}x{pil_image.height})")
        except Exception as e:
            print(f"Error loading {filename}: {e}")

    def _remove_image(self, filename):
        """Remove an image that no longer exists."""
        if filename in self.loaded_images:
            del self.loaded_images[filename]
        if filename in self.last_modified:
            del self.last_modified[filename]
        if filename in self.image_objects:
            self.canvas.delete(self.image_objects[filename])
            del self.image_objects[filename]
        print(f"Removed: {filename}")

    def _redraw_canvas(self):
        """Redraw all images on the canvas."""
        # Clear existing image objects
        for img_id in self.image_objects.values():
            self.canvas.delete(img_id)
        self.image_objects.clear()

        # Simple layout: tile images vertically
        y_offset = 10
        x_offset = 10

        for filename in sorted(self.loaded_images.keys()):
            photo_image = self.loaded_images[filename]

            # Place image on canvas
            img_id = self.canvas.create_image(
                x_offset, y_offset,
                anchor=tk.NW,
                image=photo_image
            )

            self.image_objects[filename] = img_id

            # Move down for next image
            y_offset += photo_image.height() + 10

    def _schedule_refresh(self):
        """Schedule periodic check for new/updated images."""
        self._load_images()
        # Schedule next refresh in 500ms
        self.root.after(500, self._schedule_refresh)

    def run(self):
        """Start the window event loop."""
        self.root.mainloop()


def main():
    """Run the canvas window."""
    window = CanvasWindow(width=800, height=600)
    window.run()


if __name__ == "__main__":
    main()
