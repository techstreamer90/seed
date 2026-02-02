#!/usr/bin/env python3
"""
Interactive Broadcast Terminal - Type messages, see responses.
No server needed - direct file-based communication.
"""

import sys
import time
import threading
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ui.broadcast import broadcast


class BroadcastTerminal:
    """Simple terminal interface for broadcast."""

    def __init__(self, username="human"):
        self.username = username
        self.last_count = 0
        self.running = True

    def monitor_thread(self):
        """Background thread that monitors for new messages."""
        while self.running:
            try:
                msgs = broadcast.read(limit=100)
                if len(msgs) > self.last_count:
                    # Print new messages
                    for msg in msgs[self.last_count:]:
                        timestamp = msg.get('at', '')[:19].split('T')[1] if 'T' in msg.get('at', '') else ''
                        sender = msg.get('from', 'unknown')
                        text = msg.get('text', '')

                        # Color code by sender
                        if sender == self.username:
                            color = '\033[33m'  # Yellow for you
                        elif sender == 'system':
                            color = '\033[90m'  # Gray for system
                        else:
                            color = '\033[36m'  # Cyan for others

                        print(f"\r{color}[{timestamp}] {sender}: {text}\033[0m")
                        print(f"\n{self.username}> ", end='', flush=True)

                    self.last_count = len(msgs)
            except Exception as e:
                pass

            time.sleep(1)

    def run(self):
        """Run the interactive terminal."""
        print("\033[2J\033[H")  # Clear screen
        print("="*60)
        print("  BROADCAST TERMINAL")
        print("="*60)
        print(f"  Username: {self.username}")
        print(f"  Messages: .state/broadcast.json")
        print("  Type your message and press Enter to send")
        print("  Press Ctrl+C to exit")
        print("="*60)
        print()

        # Show recent messages
        msgs = broadcast.read(limit=10)
        if msgs:
            print("Recent messages:")
            for msg in msgs:
                timestamp = msg.get('at', '')[:19].split('T')[1] if 'T' in msg.get('at', '') else ''
                print(f"  [{timestamp}] {msg.get('from')}: {msg.get('text')}")
            print()
            self.last_count = len(broadcast.read(limit=100))

        # Start monitor thread
        monitor = threading.Thread(target=self.monitor_thread, daemon=True)
        monitor.start()

        # Main input loop
        try:
            while True:
                message = input(f"{self.username}> ")
                if message.strip():
                    broadcast.send(self.username, message.strip())
                    # Give monitor thread time to show the message
                    time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            self.running = False
        except EOFError:
            self.running = False


if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else "human"
    terminal = BroadcastTerminal(username)
    terminal.run()
