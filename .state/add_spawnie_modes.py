#!/usr/bin/env python3
"""Add mode-based spawning capability to Spawnie node."""

import json
from datetime import datetime
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / "model" / "sketch.json"

print("Loading model...")
with open(MODEL_PATH, encoding="utf-8") as f:
    model = json.load(f)

# Find Spawnie node
spawnie = None
for node in model["nodes"]:
    if node.get("id") == "reality-spawnie":
        spawnie = node
        break

if not spawnie:
    print("ERROR: reality-spawnie node not found")
    exit(1)

print("Found reality-spawnie node")

# Add modes
spawnie["modes"] = {
    "work-on-views": {
        "description": "Create or update visualization views for a node",
        "context_addition": "Your task: Create or update views for this node. Use src/ui/agent_view.py to build views, then call view.render() to write to model.views.*. Check existing views first to understand the pattern.",
        "suggested_tools": ["agent_view", "canvas", "tools"],
        "output_location": "model.views.*",
        "example": "spawnie spawn --node reality-spawnie --mode work-on-views"
    },
    "chat": {
        "description": "Engage in conversation via the node's chat channel",
        "context_addition": "Your task: Read messages from node.chat and respond thoughtfully. Use src/ui/chat.py to read and send messages. Be helpful and specific in your responses.",
        "suggested_tools": ["chat"],
        "output_location": "node.chat.messages",
        "example": "spawnie spawn --node reality-seed-ui --mode chat"
    },
    "aspiration": {
        "description": "Think about future possibilities and improvements",
        "context_addition": "Your task: Consider this node's gaps, aspirations, and future directions. Think creatively about what could be improved or added. Propose concrete next steps or new features.",
        "suggested_tools": ["model_access", "chat"],
        "output_location": "Proposals via chat or as Change nodes",
        "example": "spawnie spawn --node reality-seed --mode aspiration"
    },
    "maintenance": {
        "description": "Health check, status updates, cleanup",
        "context_addition": "Your task: Check this node's health, update its status fields, clean up stale data. Verify links work, files exist, references are valid. Update node.status with findings.",
        "suggested_tools": ["model_access", "file_system"],
        "output_location": "node.status",
        "example": "spawnie spawn --node system-control --mode maintenance"
    },
    "debug": {
        "description": "Investigate issues or unexpected behavior",
        "context_addition": "Your task: Debug issues with this node. Check logs, verify configuration, test functionality. Report findings and suggest fixes.",
        "suggested_tools": ["bash", "grep", "read"],
        "output_location": "Report via chat",
        "example": "spawnie spawn --node service-ui-server --mode debug"
    },
    "implement": {
        "description": "Implement features or changes for this node",
        "context_addition": "Your task: Implement the requested feature or change. Write code, update model, test functionality. Follow the node's architecture and patterns.",
        "suggested_tools": ["edit", "write", "bash"],
        "output_location": "Source files + model updates",
        "example": "spawnie spawn --node reality-seed-ui --mode implement \"Add keyboard shortcuts\""
    }
}

# Update capabilities
spawnie["capabilities"]["spawn_with_mode"] = "Spawn an agent for a specific node with a defined mode (work-on-views, chat, aspiration, maintenance, debug, implement)"

# Update spawn_command to show mode usage
spawnie["spawn_command"]["modes"] = "Use --node <node-id> --mode <mode> for structured spawning"
spawnie["spawn_command"]["example_with_mode"] = "spawnie spawn --node reality-seed-ui --mode work-on-views"

# Update agent_context to explain modes
if "your_capabilities" not in spawnie["agent_context"]:
    spawnie["agent_context"]["your_capabilities"] = []

spawnie["agent_context"]["mode_based_spawning"] = {
    "description": "Spawn agents with specific modes for structured interaction",
    "syntax": "spawnie spawn --node <node-id> --mode <mode> [additional context]",
    "how_it_works": [
        "1. Read target node from model",
        "2. Read node.modes.<mode> for context_addition",
        "3. Combine node.agent_context._spawn_point + mode.context_addition",
        "4. Spawn agent with complete, focused context",
        "5. Agent knows exactly what to do from the model"
    ],
    "available_modes": [
        "work-on-views - Create/update visualizations",
        "chat - Engage in node conversation",
        "aspiration - Think about future possibilities",
        "maintenance - Health checks and cleanup",
        "debug - Investigate issues",
        "implement - Build features"
    ],
    "model_driven": "Mode definitions live in nodes, not in Spawnie. Any node can define custom modes."
}

# Save
print("\nUpdating model...")
model["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
with open(MODEL_PATH, "w", encoding="utf-8") as f:
    json.dump(model, f, indent=2)

print("\n" + "="*60)
print("SPAWNIE MODES ADDED")
print("="*60)
print("Added 6 standard modes:")
print("  - work-on-views")
print("  - chat")
print("  - aspiration")
print("  - maintenance")
print("  - debug")
print("  - implement")
print("\nUpdated capabilities and spawn_command")
print("Added mode_based_spawning to agent_context")
print("\nNow any node can define custom modes for structured agent interaction!")
