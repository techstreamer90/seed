#!/usr/bin/env python3
"""
Quick test script for the updated canvas window.
This will open the canvas and display agent bitmaps from .state/render/
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ui.canvas_window import CanvasWindow

if __name__ == "__main__":
    print("Starting Canvas Window with Agent Display")
    print("This will show all PNG files from .state/render/")
    print("Try adding/modifying PNG files while the window is open!")
    print("")

    window = CanvasWindow(width=800, height=600)
    window.run()
