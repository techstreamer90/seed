#!/usr/bin/env python3
"""Add system-control node to the model."""

import json
from datetime import datetime
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / "model" / "sketch.json"

# Load model
with open(MODEL_PATH, encoding="utf-8") as f:
    model = json.load(f)

# Create system-control node
control_node = {
    "id": "system-control",
    "type": "AgentNode",
    "label": "Control",
    "description": "Infrastructure controller. Monitors health, manages services, maintains pulse. The boring but critical guardian of the living system.",
    "source": {
        "path": "C:/seed/src/ui",
        "model_path": "model/sketch.json"
    },
    "status": {
        "last_pulse": datetime.now().isoformat(),
        "health": "initializing",
        "uptime_seconds": 0,
        "services": {
            "ui-server": {
                "status": "unknown",
                "port": 8420,
                "last_check": None
            },
            "broadcast": {
                "status": "unknown",
                "last_message_at": None
            }
        },
        "agents": {}
    },
    "agent_context": {
        "_spawn_point": """You are Control - the infrastructure guardian.

WHAT YOU DO:
- Monitor system health (services, agents)
- Maintain pulse every 30 seconds
- Update your status in the model (self-documenting)
- Maintain your view (proves UI pipeline works)

YOUR RESPONSIBILITIES:
1. Update this node's status with current health
2. Check UI server is running (port 8420)
3. Check broadcast system is active
4. Monitor agent health
5. Give pulse every 30 seconds (update last_pulse timestamp)
6. Update your view with current status

PULSE AS HEALTH CHECK:
- Every pulse, update model.views.control-status
- Change something small (timestamp, counter)
- If view renders, entire stack is healthy:
  * Control agent running ✓
  * Model writes working ✓
  * Server serving ✓
  * Browser polling ✓
  * Render pipeline ✓

INFRASTRUCTURE:
- Status: Update this node (system-control.status)
- View: model.views.control-status (your dedicated view)
- Broadcast: Listen and respond if asked
""",
        "pulse_interval_seconds": 30,
        "your_tools": {
            "broadcast": "src/ui/broadcast.py - listen and respond to system messages",
            "agent_view": "src/ui/agent_view.py - create/update your status view",
            "model_access": "Direct read/write to model for status updates"
        },
        "infrastructure": {
            "model_path": "C:/seed/model/sketch.json",
            "broadcast_module": "src/ui/broadcast.py",
            "view_module": "src/ui/agent_view.py",
            "status_location": "system-control.status",
            "view_name": "control-status"
        }
    },
    "chat": {
        "messages": [],
        "last_read": {}
    },
    "capabilities": {
        "monitor_services": "Check if UI server, broadcast, etc. are running",
        "monitor_agents": "Track which agents are active",
        "pulse": "Regular heartbeat proving system is alive",
        "health_reporting": "Maintain accurate system health in model"
    },
    "spawn_command": {
        "command": "spawnie shell",
        "working_dir": "C:/seed",
        "context": "Monitor system health and maintain pulse",
        "example": "spawnie shell 'Start control agent for system monitoring' -d C:/seed"
    },
    "x": 0.0,
    "y": -600.0,
    "locked": False
}

# Add initial views
if "views" not in model:
    model["views"] = {}

model["views"]["control-status"] = {
    "name": "control-status",
    "description": "System Control status view - proves UI pipeline works",
    "created_at": datetime.now().isoformat(),
    "updated_at": datetime.now().isoformat(),
    "render_target": "control-widget",
    "content": {
        "type": "status-widget",
        "health": "initializing",
        "last_pulse": datetime.now().isoformat(),
        "pulse_count": 0,
        "services": {
            "ui-server": "unknown",
            "broadcast": "unknown"
        }
    }
}

model["views"]["control-detailed"] = {
    "name": "control-detailed",
    "description": "Detailed system status",
    "created_at": datetime.now().isoformat(),
    "updated_at": datetime.now().isoformat(),
    "content": {
        "type": "hierarchy",
        "root": "system-control",
        "depth": 2,
        "show_services": True,
        "show_agents": True
    }
}

# Add node to model
model["nodes"].append(control_node)

# Add edge from seed to control
model["edges"].append({
    "type": "USES",
    "from": "reality-seed",
    "to": "system-control"
})

# Save model
model["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
with open(MODEL_PATH, "w", encoding="utf-8") as f:
    json.dump(model, f, indent=2)

print("[OK] Added system-control node")
print("[OK] Created control-status view")
print("[OK] Created control-detailed view")
print(f"[OK] Model updated: {MODEL_PATH}")
