#!/usr/bin/env python3
"""
Capture a specific window by title, regardless of which desktop it's on.

Uses Windows APIs to find and capture windows even on other virtual desktops.
"""

import sys
from pathlib import Path

def capture_window(title_contains: str = "Seed - Model Visualization", output_path: Path = None):
    """Capture a window by partial title match."""

    try:
        import pygetwindow as gw
        import pyautogui
        from PIL import Image
        import mss
    except ImportError:
        print("Installing required packages...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install",
                              "pygetwindow", "pyautogui", "pillow", "mss", "--quiet"])
        import pygetwindow as gw
        import pyautogui
        from PIL import Image
        import mss

    if output_path is None:
        output_path = Path(__file__).parent / "window_capture.png"

    # Find windows matching the title
    windows = gw.getWindowsWithTitle(title_contains)

    if not windows:
        print(f"No window found containing '{title_contains}'")
        print("Available windows:")
        for w in gw.getAllWindows():
            if w.title:
                print(f"  - {w.title}")
        return None

    window = windows[0]
    print(f"Found window: {window.title}")

    # Get window position and size
    left, top, width, height = window.left, window.top, window.width, window.height

    # Handle minimized windows
    if window.isMinimized:
        print("Window is minimized, restoring...")
        window.restore()
        import time
        time.sleep(0.5)
        left, top, width, height = window.left, window.top, window.width, window.height

    print(f"Window bounds: ({left}, {top}) {width}x{height}")

    # Capture the region
    with mss.mss() as sct:
        monitor = {"left": left, "top": top, "width": width, "height": height}
        screenshot = sct.grab(monitor)

        # Save
        from mss.tools import to_png
        to_png(screenshot.rgb, screenshot.size, output=str(output_path))

    print(f"Captured to: {output_path}")
    return output_path


if __name__ == "__main__":
    title = sys.argv[1] if len(sys.argv) > 1 else "Seed - Model Visualization"
    capture_window(title)
