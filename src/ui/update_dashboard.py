#!/usr/bin/env python3
"""Update the dashboard node with live stats."""

import json
from datetime import datetime
from collections import Counter
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / "model" / "sketch.json"

def update_dashboard():
    with open(MODEL_PATH) as f:
        model = json.load(f)

    nodes = model['nodes']
    types = Counter(n.get('type', 'Unknown') for n in nodes)

    todos = [n for n in nodes if n.get('type') == 'Todo']
    todo_pending = sum(1 for t in todos if t.get('status') == 'pending')
    todo_progress = sum(1 for t in todos if t.get('status') == 'in-progress')
    todo_done = sum(1 for t in todos if t.get('status') == 'completed')

    label = f"DASHBOARD: {len(nodes)} nodes | {todo_pending} pending | {todo_done} done"

    dashboard_node = {
        'id': 'dashboard-live',
        'type': 'View',
        'label': label,
        'description': f"Live stats. Realities: {types.get('Reality', 0)}, Gaps: {types.get('Gap', 0)}, Todos: {types.get('Todo', 0)}",
        'ui': {'x': 0, 'y': -400}
    }

    # Remove old and add new
    model['nodes'] = [n for n in model['nodes'] if n['id'] != 'dashboard-live']
    model['nodes'].append(dashboard_node)

    with open(MODEL_PATH, 'w') as f:
        json.dump(model, f, indent=2)

    print(label)
    return dashboard_node

if __name__ == "__main__":
    update_dashboard()
