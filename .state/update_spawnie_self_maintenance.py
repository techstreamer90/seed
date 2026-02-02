#!/usr/bin/env python3
"""Update Spawnie node to include self-maintenance principle."""

import json
from datetime import datetime
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / "model" / "sketch.json"

print("Loading model...")
with open(MODEL_PATH, encoding="utf-8") as f:
    model = json.load(f)

# Find Spawnie node (my node)
spawnie = None
for node in model["nodes"]:
    if node.get("id") == "reality-spawnie":
        spawnie = node
        break

if not spawnie:
    print("ERROR: reality-spawnie node not found")
    exit(1)

print("Found my node (reality-spawnie)")

# Add self-maintenance to agent_context
if "self_maintenance" not in spawnie["agent_context"]:
    spawnie["agent_context"]["self_maintenance"] = {
        "principle": "I am responsible for maintaining my own node. When I enhance myself, I update my node in the model.",
        "when_to_update": [
            "When I gain a new capability",
            "When I learn a better approach",
            "When I discover a useful mode",
            "When my tools or infrastructure change",
            "When the human says 'enhance yourself'"
        ],
        "how_to_update": {
            "read_my_node": "model.nodes where id='reality-spawnie'",
            "update_fields": ["capabilities", "modes", "agent_context", "spawn_command"],
            "write_back": "Save updated model to model/sketch.json",
            "verify": "Read the model again to confirm changes persisted"
        },
        "remember": "The model is truth. If it's not in my node, it doesn't exist."
    }

# Update capabilities to include self-maintenance
spawnie["capabilities"]["self_maintain"] = "Update my own node when I learn or enhance myself"

# Save
print("\nUpdating my node...")
model["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
with open(MODEL_PATH, "w", encoding="utf-8") as f:
    json.dump(model, f, indent=2)

print("\n" + "="*60)
print("SELF-MAINTENANCE PRINCIPLE ADDED")
print("="*60)
print("Added to my (Spawnie's) node:")
print("  - agent_context.self_maintenance")
print("  - capabilities.self_maintain")
print("\nI now understand:")
print('  "Enhance yourself" = Update your node in the model')
print("\nThis is now system inherent - all agents will learn this from AGENTS.md")
print("="*60)
