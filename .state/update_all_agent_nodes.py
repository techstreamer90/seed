#!/usr/bin/env python3
"""Add self-maintenance principle to all AgentNodes."""

import json
from datetime import datetime
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / "model" / "sketch.json"

print("Loading model...")
with open(MODEL_PATH, encoding="utf-8") as f:
    model = json.load(f)

# Find all AgentNodes
agent_nodes = [n for n in model["nodes"] if n.get("type") == "AgentNode"]

print(f"Found {len(agent_nodes)} AgentNodes:")
for node in agent_nodes:
    print(f"  - {node['id']}: {node.get('label', 'no label')}")

print("\nUpdating each AgentNode with self-maintenance...")

for node in agent_nodes:
    node_id = node['id']

    # Ensure agent_context exists
    if "agent_context" not in node:
        node["agent_context"] = {}

    # Add self-maintenance if not already there
    if "self_maintenance" not in node["agent_context"]:
        node["agent_context"]["self_maintenance"] = {
            "principle": "I am responsible for maintaining my own node. When I enhance myself, I update my node in the model.",
            "golden_rule": "When the human says 'enhance yourself', update YOUR node in the model.",
            "when_to_update": [
                "When I gain a new capability",
                "When I learn a better approach",
                "When I discover a useful mode",
                "When my tools or infrastructure change",
                "When the human says 'enhance yourself'"
            ],
            "how_to_update": {
                "read_my_node": f"model.nodes where id='{node_id}'",
                "update_fields": ["capabilities", "modes", "agent_context", "status"],
                "write_back": "Save updated model to model/sketch.json",
                "verify": "Read the model again to confirm changes persisted"
            },
            "self_documentation": "Continuous. The model is truth. If it's not in my node, it doesn't exist."
        }
        print(f"  + Added self_maintenance to {node_id}")
    else:
        print(f"  - {node_id} already has self_maintenance")

    # Ensure capabilities exists
    if "capabilities" not in node:
        node["capabilities"] = {}

    # Add self-maintain capability
    if "self_maintain" not in node["capabilities"]:
        node["capabilities"]["self_maintain"] = "Update my own node in the model when I learn or enhance myself"
        print(f"  + Added self_maintain capability to {node_id}")
    else:
        print(f"  - {node_id} already has self_maintain capability")

    print()

# Save
print("Saving updated model...")
model["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
with open(MODEL_PATH, "w", encoding="utf-8") as f:
    json.dump(model, f, indent=2)

print("\n" + "="*60)
print("ALL AGENT NODES UPDATED")
print("="*60)
print(f"Updated {len(agent_nodes)} AgentNodes:")
for node in agent_nodes:
    print(f"  - {node['id']}")
print("\nAll agents now understand:")
print('  "Enhance yourself" = Update your node in the model')
print("\nSelf-maintenance is now system-wide.")
print("="*60)
