#!/usr/bin/env python3
"""
Seed UI Server - Serves the model visualization.

A minimal HTTP server that:
- Serves the UI files (HTML, JS, CSS)
- Serves the model JSON with proper CORS headers
- Enables live reload by allowing model file polling

Usage:
    python server.py [port]

Default port is 8420 (SEED).
"""

import http.server
import socketserver
import os
import sys
from pathlib import Path


class SeedHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler with CORS support for model loading."""

    def __init__(self, *args, **kwargs):
        # Set the directory to serve from (C:/seed, not src/)
        self.seed_root = Path(__file__).parent.parent.parent
        super().__init__(*args, directory=str(self.seed_root), **kwargs)

    def end_headers(self):
        # Add CORS headers for local development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

    def do_POST(self):
        """Handle POST requests - broadcast messages."""
        if self.path == '/broadcast':
            import json
            import sys
            sys.path.insert(0, str(self.seed_root / 'src'))
            from ui.broadcast import broadcast

            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))

            sender = data.get('sender', 'unknown')
            text = data.get('text', '')

            broadcast.send(sender, text)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "sent"}).encode('utf-8'))
            print(f"[Broadcast] {sender}: {text[:50]}...")
        else:
            self.send_response(404)
            self.end_headers()

    def do_PUT(self):
        """Handle PUT requests - save layout from UI."""
        if self.path == '/ui/layout.json':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)

            # Save to file
            layout_path = self.seed_root / 'src' / 'ui' / 'layout.json'
            with open(layout_path, 'wb') as f:
                f.write(body)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "saved"}')
            print(f"[Layout saved] {layout_path}")
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        # Handle broadcast API
        if self.path == '/broadcast':
            import json
            import sys
            sys.path.insert(0, str(self.seed_root / 'src'))
            from ui.broadcast import broadcast

            messages = broadcast.read(limit=100)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(messages).encode('utf-8'))
            return

        # Redirect /ui/ to /src/ui/ for convenience
        if self.path == '/ui/' or self.path == '/ui':
            self.send_response(302)
            self.send_header('Location', '/src/ui/')
            self.end_headers()
            return
        if self.path == '/ui/index.html':
            self.send_response(302)
            self.send_header('Location', '/src/ui/index.html')
            self.end_headers()
            return
        return super().do_GET()

    def log_message(self, format, *args):
        # Custom logging - only log non-polling requests
        path = args[0].split()[1] if args else ''
        if '?t=' not in path:  # Skip cache-busting poll requests
            print(f"[{self.log_date_time_string()}] {args[0]}")


def run_server(port: int = 8420):
    """Run the development server.

    Args:
        port: Port number (default 8420 = SEED on phone keypad)
    """
    with socketserver.TCPServer(("", port), SeedHandler) as httpd:
        print(f"""
================================================================
                    SEED UI SERVER
================================================================
  Visualization:  http://localhost:{port}/ui/
  Model JSON:     http://localhost:{port}/model/sketch.json
================================================================
  The model IS the truth. Change it, and the screen updates.
================================================================

Press Ctrl+C to stop.
""")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8420
    run_server(port)
