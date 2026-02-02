#!/usr/bin/env python3
"""
Template Instantiation - Create actual nodes from templates.

Usage:
    from src.ui.instantiate_template import instantiate_template

    instantiate_template(
        template_id="template-reality-pm",
        new_node_id="reality-pm",
        parent_node_id="reality-seed",  # Where this node belongs
        overrides={
            "description": "Custom description for this instance"
        }
    )
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

MODEL_PATH = Path(__file__).parent.parent.parent / "model" / "sketch.json"


def instantiate_template(
    template_id: str,
    new_node_id: str,
    parent_node_id: Optional[str] = None,
    overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Instantiate a template to create a new node.

    Args:
        template_id: ID of the template to instantiate
        new_node_id: ID for the new node
        parent_node_id: Optional parent node (where this node belongs)
        overrides: Optional dict of fields to override in the template

    Returns:
        The created node
    """
    if overrides is None:
        overrides = {}

    # Read model
    with open(MODEL_PATH, encoding="utf-8") as f:
        model = json.load(f)

    # Find template
    template = None
    for node in model.get("nodes", []):
        if node.get("id") == template_id:
            template = node
            break

    if not template:
        raise ValueError(f"Template not found: {template_id}")

    if template.get("type") != "Template":
        raise ValueError(f"Node {template_id} is not a Template")

    # Check if new_node_id already exists
    for node in model.get("nodes", []):
        if node.get("id") == new_node_id:
            raise ValueError(f"Node with id {new_node_id} already exists")

    # Get template definition from step 1
    template_def = template.get("steps", {}).get("1_define_node", {}).get("template", {})

    if not template_def:
        raise ValueError(f"Template {template_id} has no definition in step 1")

    # Create new node from template
    new_node = {
        **template_def,  # Start with template
        "id": new_node_id,  # Override with actual ID
        **overrides  # Apply any custom overrides
    }

    # Add instantiation metadata
    new_node["instantiated_from"] = {
        "template_id": template_id,
        "template_label": template.get("label", ""),
        "instantiated_at": datetime.now().isoformat(),
        "instantiated_by": "spawnie"
    }

    # Add role context - the node knows where it belongs
    if parent_node_id:
        new_node["belongs_to"] = parent_node_id
        new_node["agent_context"] = new_node.get("agent_context", {})
        new_node["agent_context"]["my_role"] = {
            "parent": parent_node_id,
            "purpose": f"I am {new_node_id}, instantiated from {template.get('label', template_id)}",
            "location_in_world": f"I belong to {parent_node_id}"
        }

    # Ensure self_maintain capability exists
    if "capabilities" not in new_node:
        new_node["capabilities"] = {}
    if "self_maintain" not in new_node["capabilities"]:
        new_node["capabilities"]["self_maintain"] = "Update my own node when I learn or enhance myself"

    # Add node to model
    model["nodes"].append(new_node)

    # Add edge to parent if specified
    if parent_node_id:
        edge = {
            "type": "CONTAINS",
            "from": parent_node_id,
            "to": new_node_id
        }
        model["edges"].append(edge)
        print(f"Created edge: {parent_node_id} --CONTAINS--> {new_node_id}")

    # Save model
    model["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(MODEL_PATH, "w", encoding="utf-8") as f:
        json.dump(model, f, indent=2)

    print(f"✓ Instantiated {template_id} -> {new_node_id}")
    if parent_node_id:
        print(f"✓ Node belongs to: {parent_node_id}")
    print(f"✓ Node type: {new_node.get('type')}")
    print(f"✓ Capabilities: {len(new_node.get('capabilities', {}))}")

    return new_node


# CLI
if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Instantiate a template to create a new node")
    parser.add_argument("template_id", help="Template node ID")
    parser.add_argument("new_node_id", help="New node ID")
    parser.add_argument("--parent", help="Parent node ID (where this node belongs)")
    parser.add_argument("--description", help="Override description")
    parser.add_argument("--label", help="Override label")

    args = parser.parse_args()

    overrides = {}
    if args.description:
        overrides["description"] = args.description
    if args.label:
        overrides["label"] = args.label

    try:
        instantiate_template(
            template_id=args.template_id,
            new_node_id=args.new_node_id,
            parent_node_id=args.parent,
            overrides=overrides
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
