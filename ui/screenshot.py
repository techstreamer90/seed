#!/usr/bin/env python3
"""
Screenshot tool for Claude to see what user sees.

Captures the screen and saves to a file Claude can read.
Requires: pip install mss pillow
"""

import sys
from pathlib import Path
from datetime import datetime

def capture_screenshot(output_path: Path = None):
    """Capture screen and save to file."""
    try:
        import mss
        import mss.tools
    except ImportError:
        print("Installing mss...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "mss", "--quiet"])
        import mss
        import mss.tools

    if output_path is None:
        output_path = Path(__file__).parent / "screenshot.png"

    with mss.mss() as sct:
        # Capture primary monitor
        monitor = sct.monitors[1]  # Primary monitor
        screenshot = sct.grab(monitor)

        # Save to file
        mss.tools.to_png(screenshot.rgb, screenshot.size, output=str(output_path))

    print(f"Screenshot saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    capture_screenshot(output)
