#!/usr/bin/env python3
"""
Spawn batched agents to update node plans.

Groups related nodes and spawns one agent per batch.
"""

import json
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / "model" / "sketch.json"

print("Loading model...")
with open(MODEL_PATH, encoding="utf-8") as f:
    model = json.load(f)

# Group nodes into logical batches
batches = {
    "core_system": {
        "description": "Core system nodes (seed, spawnie, ui, control)",
        "node_ids": ["reality-seed", "reality-spawnie", "reality-seed-ui", "system-control"]
    },
    "templates": {
        "description": "All template nodes",
        "node_ids": [n["id"] for n in model["nodes"] if n["id"].startswith("template-")]
    },
    "aspirations": {
        "description": "Aspiration nodes",
        "node_ids": [n["id"] for n in model["nodes"] if n["id"].startswith("aspiration-")]
    },
    "services_channels": {
        "description": "Services and communication channels",
        "node_ids": [n["id"] for n in model["nodes"] if n["id"].startswith(("service-", "channel-"))]
    },
    "subsystems": {
        "description": "Subsystem nodes",
        "node_ids": [n["id"] for n in model["nodes"] if n["id"].startswith("subsystem-")]
    },
    "instantiated_agents": {
        "description": "Instantiated agent nodes",
        "node_ids": [n["id"] for n in model["nodes"]
                     if n.get("instantiated_from") and n.get("type") == "AgentNode"]
    },
    "other": {
        "description": "All other nodes",
        "node_ids": []
    }
}

# Collect all categorized node IDs
categorized = set()
for batch in batches.values():
    categorized.update(batch["node_ids"])

# Add remaining nodes to "other"
all_node_ids = {n["id"] for n in model["nodes"]}
batches["other"]["node_ids"] = list(all_node_ids - categorized)

# Print batch summary
print(f"\nFound {len(model['nodes'])} nodes, grouped into {len(batches)} batches:\n")
for batch_name, batch_info in batches.items():
    if batch_info["node_ids"]:
        print(f"{batch_name}: {len(batch_info['node_ids'])} nodes - {batch_info['description']}")

# Create task files for each batch
print("\nCreating task files for spawning...\n")

for batch_name, batch_info in batches.items():
    if not batch_info["node_ids"]:
        continue

    task = f"""You are a plan specialist for the Seed world.

Batch: {batch_info['description']}
Nodes to update: {', '.join(batch_info['node_ids'])}

Your mission: Update the plan for each of these nodes to be highly personalized.

For EACH node in your batch:
1. Read the node from model/sketch.json
2. Understand its current capabilities, agent_context, description, role, type
3. Understand what makes this node unique and special
4. Update node.plan with a personalized evolutionary path:
   - current_reality: Its SPECIFIC current state (not generic!)
   - aspiration: Its SPECIFIC goal aligned with local ML vision
   - phases: Meaningful progression for THIS node's role
   - next_steps: Actionable items specific to this node

Overall world vision:
- Aspiration: Fully local, GPU-powered, self-rendering reactive world
- Evolution: External dependency -> Hybrid -> Autonomous local
- Each node eventually self-renders based on state using local ML

Make each plan deeply specific to that node's role, capabilities, and context.

Update all nodes in your batch, then save the model.
Work silently - use your judgment based on the node's content.
"""

    task_file = Path(".state") / f"task_batch_{batch_name}.txt"
    with open(task_file, "w", encoding="utf-8") as f:
        f.write(task)

    print(f"Created: {task_file.name}")
    print(f"  Nodes: {', '.join(batch_info['node_ids'][:3])}" +
          (f"... (+{len(batch_info['node_ids'])-3} more)" if len(batch_info['node_ids']) > 3 else ""))
    print()

print("="*70)
print("BATCH TASK FILES CREATED")
print("="*70)
print("\nTo spawn agents, use:")
print("  spawnie spawn reality-spawnie implement --task @.state/task_batch_<name>.txt")
print("\nOr spawn all batches with Task tool in parallel")
print("="*70)
