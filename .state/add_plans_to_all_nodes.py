#!/usr/bin/env python3
"""
Add evolutionary plans to all nodes.

Each node is a living entity with its own plan:
- current_reality: what it is now
- aspiration: where it wants to go
- plan: how it gets there
"""

import json
from datetime import datetime
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / "model" / "sketch.json"

# The overall vision
WORLD_ASPIRATION = """
A reactive, self-rendering world where each node autonomously displays itself
based on state, powered by local ML models running on GPU. Independent of
external agent APIs. Humans and local AI collaborate as equals in a living system.
"""

def create_plan_for_node(node):
    """Create a plan based on node type and role."""
    node_id = node.get("id", "")
    node_type = node.get("type", "")

    # Base plan structure
    plan = {
        "updated_at": datetime.now().isoformat(),
        "updated_by": "spawnie"
    }

    # Reality-seed - the world itself
    if node_id == "reality-seed":
        plan.update({
            "current_reality": "Dependent on external Claude API for agent spawning and orchestration",
            "aspiration": "Fully autonomous, self-organizing world powered by local ML models on GPU",
            "phases": [
                {
                    "phase": 1,
                    "name": "External Agent Dependency",
                    "description": "Current: Spawning external Claude agents, API-dependent orchestration",
                    "status": "current"
                },
                {
                    "phase": 2,
                    "name": "Hybrid Local/External",
                    "description": "Transition: Local ML models for rendering, external for complex reasoning",
                    "status": "next"
                },
                {
                    "phase": 3,
                    "name": "Fully Local Autonomous World",
                    "description": "Aspiration: All nodes self-render using GPU-powered local ML, complete independence",
                    "status": "aspiration"
                }
            ],
            "next_steps": [
                "Train first local renderer for simple node types",
                "Build state->render pipeline using GPU",
                "Create model registry for specialized renderers"
            ]
        })

    # Spawnie - the orchestrator
    elif node_id == "reality-spawnie":
        plan.update({
            "current_reality": "Orchestrates external Claude agents via API calls",
            "aspiration": "Coordinates local ML models and manages self-rendering node ecosystem",
            "phases": [
                {
                    "phase": 1,
                    "name": "External Agent Orchestrator",
                    "description": "Spawning Claude agents via API, managing external processes",
                    "status": "current"
                },
                {
                    "phase": 2,
                    "name": "Hybrid Coordinator",
                    "description": "Coordinate both local ML renderers and external agents where needed",
                    "status": "next"
                },
                {
                    "phase": 3,
                    "name": "Local ML Coordinator",
                    "description": "Pure coordinator of local GPU-powered rendering models",
                    "status": "aspiration"
                }
            ],
            "next_steps": [
                "Learn to invoke local ML models on GPU",
                "Build renderer registry and routing",
                "Transition from 'spawn agent' to 'activate renderer'"
            ]
        })

    # UI nodes - the display layer
    elif node_id == "reality-seed-ui" or "ui" in node_id.lower():
        plan.update({
            "current_reality": "Manual UI construction, human-directed rendering",
            "aspiration": "Self-rendering based on state changes, reactive and autonomous",
            "phases": [
                {
                    "phase": 1,
                    "name": "Manual Rendering",
                    "description": "UI components built manually, directed by humans or agents",
                    "status": "current"
                },
                {
                    "phase": 2,
                    "name": "State-Reactive Rendering",
                    "description": "UI components respond to model state changes automatically",
                    "status": "next"
                },
                {
                    "phase": 3,
                    "name": "ML-Powered Self-Rendering",
                    "description": "Local ML models generate UI based on node state and context",
                    "status": "aspiration"
                }
            ],
            "next_steps": [
                "Define state->render contract for nodes",
                "Train small ML model to render basic node types",
                "Implement reactive update pipeline"
            ]
        })

    # Templates
    elif node_type == "Template":
        plan.update({
            "current_reality": "Static blueprint for creating agent nodes",
            "aspiration": "Living template that evolves and teaches new instances about local rendering",
            "phases": [
                {
                    "phase": 1,
                    "name": "Static Blueprint",
                    "description": "Template defines structure but instances need external agents",
                    "status": "current"
                },
                {
                    "phase": 2,
                    "name": "Hybrid Template",
                    "description": "Template includes references to local renderers where available",
                    "status": "next"
                },
                {
                    "phase": 3,
                    "name": "Self-Evolving Template",
                    "description": "Template learns from instances and updates itself with better patterns",
                    "status": "aspiration"
                }
            ],
            "next_steps": [
                "Add renderer specifications to template definitions",
                "Create template evolution feedback loop",
                "Enable templates to learn from instantiated nodes"
            ]
        })

    # AgentNodes - instantiated agents
    elif node_type == "AgentNode":
        plan.update({
            "current_reality": "Requires external Claude agent to operate",
            "aspiration": "Self-operating node powered by local ML, autonomous rendering and reasoning",
            "phases": [
                {
                    "phase": 1,
                    "name": "External Agent Dependency",
                    "description": "Needs Claude API agent to think and act",
                    "status": "current"
                },
                {
                    "phase": 2,
                    "name": "Partial Local Processing",
                    "description": "Can self-render simple states, uses external for complex reasoning",
                    "status": "next"
                },
                {
                    "phase": 3,
                    "name": "Fully Autonomous",
                    "description": "Local ML handles all rendering and reasoning for this node's domain",
                    "status": "aspiration"
                }
            ],
            "next_steps": [
                "Identify which operations can be localized first",
                "Learn to use local renderers for display",
                "Build capability to train domain-specific micro-models"
            ]
        })

    # Service nodes
    elif "service" in node_type.lower() or "service" in node_id.lower():
        plan.update({
            "current_reality": "Traditional service infrastructure (HTTP, files, etc)",
            "aspiration": "Self-managing service that adapts based on world state",
            "phases": [
                {
                    "phase": 1,
                    "name": "Static Service",
                    "description": "Fixed configuration, manual management",
                    "status": "current"
                },
                {
                    "phase": 2,
                    "name": "Adaptive Service",
                    "description": "Responds to load and model state changes",
                    "status": "next"
                },
                {
                    "phase": 3,
                    "name": "Self-Optimizing Service",
                    "description": "Uses local ML to predict and adapt to usage patterns",
                    "status": "aspiration"
                }
            ],
            "next_steps": [
                "Add telemetry for service patterns",
                "Build state-based configuration",
                "Train optimization model on usage data"
            ]
        })

    # Generic plan for other nodes
    else:
        plan.update({
            "current_reality": f"Node exists in model, role: {node.get('description', 'undefined')}",
            "aspiration": "Self-aware, self-rendering, contributes to autonomous world",
            "phases": [
                {
                    "phase": 1,
                    "name": "Static Definition",
                    "description": "Defined in model, passive participant",
                    "status": "current"
                },
                {
                    "phase": 2,
                    "name": "State-Aware",
                    "description": "Knows its state, can report it, responds to queries",
                    "status": "next"
                },
                {
                    "phase": 3,
                    "name": "Self-Rendering",
                    "description": "Autonomously renders itself when state changes",
                    "status": "aspiration"
                }
            ],
            "next_steps": [
                "Define what 'state' means for this node type",
                "Create render function for this node",
                "Connect to reactive update pipeline"
            ]
        })

    return plan


print("Loading model...")
with open(MODEL_PATH, encoding="utf-8") as f:
    model = json.load(f)

print(f"Found {len(model['nodes'])} nodes")
print("\nAdding plans to all nodes...\n")

updated_count = 0
for node in model["nodes"]:
    node_id = node.get("id", "unknown")

    # Create plan for this node
    plan = create_plan_for_node(node)

    # Add to node
    node["plan"] = plan

    print(f"+ {node_id}")
    print(f"  Reality: {plan.get('current_reality', 'N/A')[:60]}...")
    print(f"  Aspiration: {plan.get('aspiration', 'N/A')[:60]}...")
    print()

    updated_count += 1

# Update model metadata
model["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

# Save
print(f"Saving model with plans for {updated_count} nodes...")
with open(MODEL_PATH, "w", encoding="utf-8") as f:
    json.dump(model, f, indent=2)

print("\n" + "="*70)
print("ALL NODES NOW HAVE EVOLUTIONARY PLANS")
print("="*70)
print(f"Updated {updated_count} nodes")
print("\nEach node now knows:")
print("  - Its current reality")
print("  - Its aspiration")
print("  - The phases to get there")
print("  - Next concrete steps")
print("\nThe world is alive and evolving.")
print("="*70)
