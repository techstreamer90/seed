#!/usr/bin/env python3
"""Spawn agents to update view definitions for all nodes."""
import json
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / "model" / "sketch.json"

# Read model
with open(MODEL_PATH, encoding="utf-8") as f:
    model = json.load(f)

# Get all nodes except Spawnie (already updated)
nodes = [n["id"] for n in model["nodes"] if n["id"] != "reality-spawnie"]

print(f"Need to update views for {len(nodes)} nodes\n")

# Group into batches (same as plan updates)
batches = {
    "core_system": [n for n in nodes if n in ["reality-seed", "reality-seed-ui", "system-control"]],
    "templates": [n for n in nodes if n.startswith("template-")],
    "aspirations": [n for n in nodes if n.startswith("aspiration-")],
    "services_channels": [n for n in nodes if n.startswith(("service-", "channel-"))],
    "subsystems": [n for n in nodes if n.startswith("subsystem-")],
    "instantiated_agents": [n for n in nodes if any(node.get("instantiated_from") and node["id"] == n for node in model["nodes"])],
    "other": []
}

# Collect categorized
categorized = set()
for batch in batches.values():
    categorized.update(batch)

# Add remaining to other
batches["other"] = [n for n in nodes if n not in categorized]

# Print batches
for batch_name, batch_nodes in batches.items():
    if batch_nodes:
        print(f"{batch_name}: {len(batch_nodes)} nodes")
        for nid in batch_nodes[:3]:
            print(f"  - {nid}")
        if len(batch_nodes) > 3:
            print(f"  ... and {len(batch_nodes)-3} more")
        print()

print("\nReady to spawn agents for each batch")
