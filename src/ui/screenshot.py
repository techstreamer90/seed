#!/usr/bin/env python3
"""
Screenshot Tool - Capture what the user is seeing.

Usage:
    python screenshot.py [output_file]
"""

import sys
from pathlib import Path

try:
    from PIL import ImageGrab

    def capture_screen(output_path: str = "src/ui/window_capture.png"):
        """Capture the entire screen."""
        screenshot = ImageGrab.grab()
        screenshot.save(output_path)
        print(f"Screenshot saved to: {output_path}")
        return output_path

except ImportError:
    print("PIL not available. Install with: pip install pillow")
    sys.exit(1)

if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "src/ui/window_capture.png"
    capture_screen(output)
