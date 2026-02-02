#!/usr/bin/env python3
"""Add instantiate_template capability to Spawnie."""

import json
from datetime import datetime
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / "model" / "sketch.json"

print("Loading model...")
with open(MODEL_PATH, encoding="utf-8") as f:
    model = json.load(f)

# Find Spawnie (my node)
spawnie = None
for node in model["nodes"]:
    if node.get("id") == "reality-spawnie":
        spawnie = node
        break

if not spawnie:
    print("ERROR: reality-spawnie node not found")
    exit(1)

print("Found my node (reality-spawnie)")
print("Enhancing myself with template instantiation capability...")

# Add capability
spawnie["capabilities"]["instantiate_template"] = "Create actual nodes from template definitions, with proper lineage tracking and role context"

# Add tool reference
if "agent_context" not in spawnie:
    spawnie["agent_context"] = {}

spawnie["agent_context"]["your_tools"] = spawnie["agent_context"].get("your_tools", {})
spawnie["agent_context"]["your_tools"]["instantiate_template"] = "src/ui/instantiate_template.py - Create nodes from templates"

# Add usage example
spawnie["agent_context"]["template_instantiation"] = {
    "what": "Create actual AgentNodes from template definitions",
    "why": "Templates are blueprints, instantiation creates the actual agents",
    "how": {
        "code": """from src.ui.instantiate_template import instantiate_template

instantiate_template(
    template_id="template-reality-pm",
    new_node_id="reality-pm",
    parent_node_id="reality-seed",  # Where it belongs
    overrides={"description": "Custom description"}
)""",
        "cli": "python src/ui/instantiate_template.py template-reality-pm reality-pm --parent reality-seed"
    },
    "what_it_does": [
        "Reads the template definition",
        "Creates new node with unique ID",
        "Adds instantiation metadata (from which template, when)",
        "Adds role context (node knows where it belongs)",
        "Creates CONTAINS edge to parent",
        "Writes to model"
    ],
    "node_knows_its_role": "Instantiated node has agent_context.my_role with parent, purpose, location_in_world"
}

# Save
print("\nUpdating my node...")
model["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
with open(MODEL_PATH, "w", encoding="utf-8") as f:
    json.dump(model, f, indent=2)

print("\n" + "="*60)
print("SPAWNIE ENHANCED WITH TEMPLATE INSTANTIATION")
print("="*60)
print("Added to my node:")
print("  - capabilities.instantiate_template")
print("  - agent_context.your_tools.instantiate_template")
print("  - agent_context.template_instantiation (usage guide)")
print("\nI can now create actual nodes from templates!")
print("Instantiated nodes will know:")
print("  - Which template they came from")
print("  - Where they belong (parent node)")
print("  - Their role and purpose")
print("="*60)
