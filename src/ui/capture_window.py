#!/usr/bin/env python3
"""
Capture a specific window by title, regardless of which desktop it's on.

Uses Windows PrintWindow API to capture the window content only,
excluding any overlapping windows.
"""

import sys
import ctypes
from ctypes import wintypes
from pathlib import Path


def capture_window(title_contains: str = "Seed - Model Visualization", output_path: Path = None):
    """Capture a window by partial title match using Win32 PrintWindow API."""

    try:
        from PIL import Image
    except ImportError:
        print("Installing pillow...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow", "--quiet"])
        from PIL import Image

    if output_path is None:
        output_path = Path(__file__).parent / "window_capture.png"

    # Win32 API setup
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    # Constants
    SRCCOPY = 0x00CC0020
    PW_RENDERFULLCONTENT = 0x00000002  # Capture even if window is on another desktop
    DIB_RGB_COLORS = 0
    BI_RGB = 0

    # Find window by partial title match
    hwnd_found = None
    window_title = None

    # Callback for EnumWindows
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def enum_callback(hwnd, lparam):
        nonlocal hwnd_found, window_title
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd) + 1
            if length > 1:
                buffer = ctypes.create_unicode_buffer(length)
                user32.GetWindowTextW(hwnd, buffer, length)
                title = buffer.value
                if title_contains.lower() in title.lower():
                    hwnd_found = hwnd
                    window_title = title
                    return False  # Stop enumeration
        return True  # Continue enumeration

    user32.EnumWindows(WNDENUMPROC(enum_callback), 0)

    if not hwnd_found:
        print(f"No window found containing '{title_contains}'")
        print("Available windows:")

        def list_callback(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd) + 1
                if length > 1:
                    buffer = ctypes.create_unicode_buffer(length)
                    user32.GetWindowTextW(hwnd, buffer, length)
                    if buffer.value:
                        print(f"  - {buffer.value}")
            return True

        user32.EnumWindows(WNDENUMPROC(list_callback), 0)
        return None

    print(f"Found window: {window_title}")

    # Get window dimensions (client area for content, full rect for frame)
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd_found, ctypes.byref(rect))
    width = rect.right - rect.left
    height = rect.bottom - rect.top

    print(f"Window size: {width}x{height}")

    # Create device contexts and bitmap
    hwnd_dc = user32.GetWindowDC(hwnd_found)
    mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
    bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
    old_bitmap = gdi32.SelectObject(mem_dc, bitmap)

    # Use PrintWindow to capture the window content (works even if obscured)
    result = user32.PrintWindow(hwnd_found, mem_dc, PW_RENDERFULLCONTENT)

    if not result:
        # Fallback to BitBlt if PrintWindow fails
        print("PrintWindow failed, trying BitBlt fallback...")
        gdi32.BitBlt(mem_dc, 0, 0, width, height, hwnd_dc, 0, 0, SRCCOPY)

    # Prepare BITMAPINFOHEADER
    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ('biSize', wintypes.DWORD),
            ('biWidth', wintypes.LONG),
            ('biHeight', wintypes.LONG),
            ('biPlanes', wintypes.WORD),
            ('biBitCount', wintypes.WORD),
            ('biCompression', wintypes.DWORD),
            ('biSizeImage', wintypes.DWORD),
            ('biXPelsPerMeter', wintypes.LONG),
            ('biYPelsPerMeter', wintypes.LONG),
            ('biClrUsed', wintypes.DWORD),
            ('biClrImportant', wintypes.DWORD),
        ]

    bmi = BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.biWidth = width
    bmi.biHeight = -height  # Negative for top-down DIB
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    bmi.biCompression = BI_RGB

    # Get bitmap bits
    buffer_size = width * height * 4
    buffer = ctypes.create_string_buffer(buffer_size)
    gdi32.GetDIBits(mem_dc, bitmap, 0, height, buffer, ctypes.byref(bmi), DIB_RGB_COLORS)

    # Clean up GDI objects
    gdi32.SelectObject(mem_dc, old_bitmap)
    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(mem_dc)
    user32.ReleaseDC(hwnd_found, hwnd_dc)

    # Convert to PIL Image (BGRA -> RGBA)
    img = Image.frombuffer('RGBA', (width, height), buffer.raw, 'raw', 'BGRA', 0, 1)

    # Convert to RGB (remove alpha) and save
    img = img.convert('RGB')
    img.save(str(output_path))

    print(f"Captured to: {output_path}")
    return output_path


if __name__ == "__main__":
    title = sys.argv[1] if len(sys.argv) > 1 else "Seed - Model Visualization"
    capture_window(title)
