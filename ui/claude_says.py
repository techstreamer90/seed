#!/usr/bin/env python3
"""
Claude Says - Update Claude's live status in the model.

This lets Claude "speak" through the model. The message appears
on the user's screen in real-time via the visualization.

Usage:
    python claude_says.py "Your message here"
    python claude_says.py --action "What I'm doing"
    python claude_says.py --mood "excited"
"""

import json
import sys
from datetime import datetime
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / "model" / "sketch.json"

def update_status(message=None, action=None, mood=None):
    with open(MODEL_PATH) as f:
        model = json.load(f)

    # Find or create claude-live-status node
    status_node = None
    for node in model['nodes']:
        if node['id'] == 'claude-live-status':
            status_node = node
            break

    if status_node is None:
        status_node = {
            'id': 'claude-live-status',
            'type': 'UIState',
            'ui': {'x': 0, 'y': -600}
        }
        model['nodes'].append(status_node)

    # Update fields
    now = datetime.now()

    if message:
        status_node['label'] = message[:50]  # Truncate for display
        status_node['description'] = message

    if 'status' not in status_node:
        status_node['status'] = {}

    status_node['status']['last_update'] = now.isoformat()

    if action:
        status_node['status']['current_action'] = action
    if mood:
        status_node['status']['mood'] = mood

    status_node['status']['watching'] = True

    model['updated_at'] = now.strftime('%Y-%m-%dT%H:%M:%SZ')

    with open(MODEL_PATH, 'w') as f:
        json.dump(model, f, indent=2)

    print(f"[{now.strftime('%H:%M:%S')}] Claude says: {message or action or mood}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python claude_says.py 'message'")
        sys.exit(1)

    message = None
    action = None
    mood = None

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '--action' and i + 1 < len(sys.argv):
            action = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--mood' and i + 1 < len(sys.argv):
            mood = sys.argv[i + 1]
            i += 2
        else:
            message = sys.argv[i]
            i += 1

    update_status(message, action, mood)
