#!/usr/bin/env python3
"""Fix critical model issues from audit."""

import json
from datetime import datetime
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / "model" / "sketch.json"

print("Loading model...")
with open(MODEL_PATH, encoding="utf-8") as f:
    model = json.load(f)

# 1. Remove duplicate system-control node
print("\n1. Removing duplicate system-control node...")
control_nodes = [i for i, n in enumerate(model["nodes"]) if n.get("id") == "system-control"]
print(f"   Found {len(control_nodes)} system-control nodes at indices: {control_nodes}")

if len(control_nodes) > 1:
    # Keep the first one, remove others
    for idx in reversed(control_nodes[1:]):
        removed = model["nodes"].pop(idx)
        print(f"   Removed duplicate at index {idx}")
else:
    print("   No duplicates found")

# 2. Add service-ui-server node
print("\n2. Adding service-ui-server node...")
service_node = {
    "id": "service-ui-server",
    "type": "Service",
    "label": "UI Server",
    "description": "HTTP server that serves the model JSON and UI files. The portal through which humans see the model.",
    "port": 8420,
    "host": "localhost",
    "url": "http://localhost:8420",
    "status": {
        "state": "unknown",
        "pid": None,
        "last_check": None,
        "health": "unknown"
    },
    "endpoints": {
        "model": "/model/sketch.json",
        "broadcast": "/broadcast",
        "ui": "/src/ui/",
        "layout": "/ui/layout.json"
    },
    "source": {
        "path": "src/ui/server.py"
    },
    "start_command": "python src/ui/server.py",
    "x": 350.0,
    "y": -600.0
}

model["nodes"].append(service_node)
print("   Added service-ui-server node")

# 3. Add channel-broadcast node
print("\n3. Adding channel-broadcast node...")
broadcast_node = {
    "id": "channel-broadcast",
    "type": "CommunicationChannel",
    "label": "Broadcast",
    "description": "System-wide broadcast channel. Everyone can see and respond. The model is the communication fabric - everything flows through it.",
    "state_path": ".state/broadcast.json",
    "status": {
        "message_count": 0,
        "participants": [],
        "last_message_at": None,
        "last_check": None
    },
    "source": {
        "path": "src/ui/broadcast.py"
    },
    "ui_url": "http://localhost:8420/src/ui/broadcast.html",
    "api_endpoints": {
        "read": "GET /broadcast",
        "send": "POST /broadcast"
    },
    "purpose": "Global conversation space for users and agents. Any agent can respond to any message. Enables emergent coordination.",
    "x": 175.0,
    "y": -600.0
}

model["nodes"].append(broadcast_node)
print("   Added channel-broadcast node")

# 4. Add edges
print("\n4. Adding edges...")
new_edges = [
    {"type": "USES", "from": "reality-seed", "to": "service-ui-server"},
    {"type": "USES", "from": "reality-seed", "to": "channel-broadcast"},
    {"type": "DEPENDS_ON", "from": "reality-seed-ui", "to": "service-ui-server"},
    {"type": "DEPENDS_ON", "from": "channel-broadcast", "to": "service-ui-server"},
    {"type": "MONITORS", "from": "system-control", "to": "service-ui-server"},
    {"type": "MONITORS", "from": "system-control", "to": "channel-broadcast"},
]

for edge in new_edges:
    # Check if edge already exists
    exists = any(
        e.get("type") == edge["type"] and
        e.get("from") == edge["from"] and
        e.get("to") == edge["to"]
        for e in model.get("edges", [])
    )
    if not exists:
        model["edges"].append(edge)
        print(f"   Added: {edge['from']} --{edge['type']}--> {edge['to']}")
    else:
        print(f"   Skipped (exists): {edge['from']} --{edge['type']}--> {edge['to']}")

# 5. Update schema to include new node types
print("\n5. Updating schema...")
if "schema" not in model:
    model["schema"] = {}
if "node_types" not in model["schema"]:
    model["schema"]["node_types"] = {}

model["schema"]["node_types"]["Service"] = {
    "description": "A runtime service (server, daemon, background process)",
    "properties": ["port", "host", "url", "status", "endpoints"],
    "required": ["status"]
}

model["schema"]["node_types"]["CommunicationChannel"] = {
    "description": "A channel for agent and user communication",
    "properties": ["state_path", "status", "api_endpoints"],
    "required": ["state_path"]
}

print("   Added Service and CommunicationChannel to schema")

# 6. Update system-control to reference service URLs
print("\n6. Updating system-control infrastructure...")
control_node = next((n for n in model["nodes"] if n.get("id") == "system-control"), None)
if control_node:
    if "infrastructure" not in control_node.get("agent_context", {}):
        control_node["agent_context"]["infrastructure"] = {}

    control_node["agent_context"]["infrastructure"]["services_to_monitor"] = [
        "service-ui-server",
        "channel-broadcast"
    ]
    control_node["agent_context"]["infrastructure"]["ui_server_url_ref"] = "service-ui-server.url"
    control_node["agent_context"]["infrastructure"]["broadcast_url_ref"] = "channel-broadcast.ui_url"

    print("   Updated system-control infrastructure references")

# Save model
print("\n7. Saving model...")
model["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
with open(MODEL_PATH, "w", encoding="utf-8") as f:
    json.dump(model, f, indent=2)

print(f"   Saved: {MODEL_PATH}")

print("\n" + "="*60)
print("CRITICAL FIXES COMPLETE")
print("="*60)
print("✓ Removed duplicate system-control")
print("✓ Added service-ui-server node")
print("✓ Added channel-broadcast node")
print("✓ Added USES, DEPENDS_ON, MONITORS edges")
print("✓ Updated schema with Service and CommunicationChannel types")
print("✓ Updated system-control to reference services")
print("\nNext: Implement Control agent self-updating behavior")
