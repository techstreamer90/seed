#!/usr/bin/env python3
"""
Spawn an agent for each node to update its personalized plan.

Each agent will:
1. Read the node's current state
2. Understand its capabilities, role, context
3. Craft a personalized plan for evolution to local ML-powered aspiration
"""

import json
import subprocess
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / "model" / "sketch.json"
SPAWNIE_PATH = "C:/spawnie/src/spawnie/__main__.py"

print("Loading model...")
with open(MODEL_PATH, encoding="utf-8") as f:
    model = json.load(f)

# Get all node IDs
node_ids = [node["id"] for node in model["nodes"]]

print(f"Found {len(node_ids)} nodes")
print("\nSpawning silent plan-updater agent for each node...\n")

# Create task template
task_template = """You are a plan specialist for the Seed world.

Your mission: Update the plan for node '{node_id}' to be highly personalized.

Steps:
1. Read the node from model/sketch.json
2. Understand its current capabilities, agent_context, description, role
3. Understand what makes this node unique
4. Update node.plan with a personalized evolutionary path that:
   - Reflects its SPECIFIC current reality (not generic)
   - Captures its SPECIFIC aspiration aligned with local ML vision
   - Has phases that make sense for THIS node
   - Includes next_steps that are actionable for this specific node

Overall vision context:
- World aspiration: Fully local, GPU-powered, self-rendering
- Each node evolves: External dependency -> Hybrid -> Autonomous local
- Nodes should eventually self-render based on state using local ML

Make the plan deeply specific to {node_id}'s role in the world.

Write the updated node back to the model.
Work silently - no questions, just update the plan based on the node's content.
"""

# Spawn agent for each node
spawned_count = 0
for node_id in node_ids:
    task = task_template.format(node_id=node_id)

    print(f"Spawning agent for: {node_id}")

    # Use spawnie shell to spawn the agent
    # Note: This will spawn them sequentially, but each runs independently
    cmd = [
        "python", SPAWNIE_PATH, "shell",
        "--task", task,
        "--silent"
    ]

    # Run in background (don't wait)
    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd="C:/seed"
    )

    spawned_count += 1

print(f"\n{'='*70}")
print(f"SPAWNED {spawned_count} PLAN-UPDATER AGENTS")
print(f"{'='*70}")
print("Each agent is working silently to update their node's plan.")
print("They will read the node, understand it, and craft a personalized plan.")
print("\nThis is distributed planning in action!")
print(f"{'='*70}")
