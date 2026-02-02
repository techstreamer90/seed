#!/usr/bin/env python3
"""
SchauspielerSub Protocol - Shared state communication for node visualization.

This module provides the infrastructure for NodeAgent ←→ SchauspielerSub
communication via shared state in the model.

Pattern:
1. NodeAgent writes visualization.current_request
2. SchauspielerSub monitors, creates view, updates status
3. NodeAgent reads status to know when finished

Usage for NodeAgent:
    from src.ui.schauspieler_protocol import request_visualization, check_status

    # Request a visualization
    request_visualization("reality-spawnie", "show_sessions", {"depth": 2})

    # Check if finished
    status = check_status("reality-spawnie")
    if status["status"] == "finished":
        print(f"View ready: {status['view_name']}")

Usage for SchauspielerSub:
    from src.ui.schauspieler_protocol import (
        poll_requests, mark_in_progress, mark_finished, mark_error
    )

    # Poll for requests
    request = poll_requests("reality-spawnie")
    if request:
        mark_in_progress("reality-spawnie")
        # ... create view ...
        mark_finished("reality-spawnie", "spawnie-sessions", element_count=10)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

MODEL_PATH = Path(__file__).parent.parent.parent / "model" / "sketch.json"


def _read_model() -> Dict[str, Any]:
    with open(MODEL_PATH, encoding="utf-8") as f:
        return json.load(f)


def _write_model(model: Dict[str, Any]) -> None:
    model["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(MODEL_PATH, "w", encoding="utf-8") as f:
        json.dump(model, f, indent=2)


def _find_node(node_id: str, model: Dict[str, Any]) -> Optional[Dict]:
    for node in model.get("nodes", []):
        if node.get("id") == node_id:
            return node
    return None


# === NodeAgent API ===

def request_visualization(
    node_id: str,
    viz_type: str,
    params: Dict[str, Any] = None,
    requester: str = "node-agent"
) -> str:
    """
    NodeAgent requests a visualization.

    Args:
        node_id: Node to visualize
        viz_type: Type of visualization (show_hierarchy, show_sessions, etc.)
        params: Optional parameters for the visualization
        requester: Who is requesting (for tracking)

    Returns:
        Status message
    """
    model = _read_model()
    node = _find_node(node_id, model)

    if not node:
        return f"Node '{node_id}' not found"

    if "visualization" not in node:
        node["visualization"] = {
            "enabled": True,
            "current_request": None,
            "status": "idle",
            "view_name": None,
            "schauspieler_sub": {
                "active": False,
                "last_active": None,
                "views_created": []
            }
        }

    node["visualization"]["current_request"] = {
        "type": viz_type,
        "params": params or {},
        "requested_at": datetime.now().isoformat(),
        "requester": requester
    }
    node["visualization"]["status"] = "requested"

    _write_model(model)
    return f"Visualization requested for {node_id}: {viz_type}"


def check_status(node_id: str) -> Optional[Dict[str, Any]]:
    """
    NodeAgent checks visualization status.

    Args:
        node_id: Node to check

    Returns:
        Status dict with: {status, view_name, completed_at, error}
    """
    model = _read_model()
    node = _find_node(node_id, model)

    if not node or "visualization" not in node:
        return None

    viz = node["visualization"]
    return {
        "status": viz.get("status", "idle"),
        "view_name": viz.get("view_name"),
        "completed_at": viz.get("completed_at"),
        "error": viz.get("error"),
        "element_count": viz.get("element_count")
    }


def clear_request(node_id: str) -> str:
    """
    NodeAgent clears the visualization request (after consuming result).

    Args:
        node_id: Node to clear

    Returns:
        Status message
    """
    model = _read_model()
    node = _find_node(node_id, model)

    if not node or "visualization" not in node:
        return f"No visualization for {node_id}"

    node["visualization"]["current_request"] = None
    node["visualization"]["status"] = "idle"

    _write_model(model)
    return f"Cleared visualization request for {node_id}"


# === SchauspielerSub API ===

def poll_requests(node_id: str) -> Optional[Dict[str, Any]]:
    """
    SchauspielerSub polls for visualization requests.

    Args:
        node_id: Node to monitor

    Returns:
        Request dict if status is "requested", None otherwise
    """
    model = _read_model()
    node = _find_node(node_id, model)

    if not node or "visualization" not in node:
        return None

    viz = node["visualization"]
    if viz.get("status") == "requested":
        return viz.get("current_request")

    return None


def mark_in_progress(node_id: str) -> str:
    """
    SchauspielerSub marks visualization as in progress.

    Args:
        node_id: Node being visualized

    Returns:
        Status message
    """
    model = _read_model()
    node = _find_node(node_id, model)

    if not node or "visualization" not in node:
        return f"No visualization for {node_id}"

    node["visualization"]["status"] = "in_progress"
    node["visualization"]["schauspieler_sub"]["active"] = True
    node["visualization"]["schauspieler_sub"]["last_active"] = datetime.now().isoformat()

    _write_model(model)
    return f"Marked {node_id} visualization in progress"


def mark_finished(
    node_id: str,
    view_name: str,
    element_count: int = 0
) -> str:
    """
    SchauspielerSub marks visualization as finished.

    Args:
        node_id: Node that was visualized
        view_name: Name of the created view
        element_count: Number of elements in the view

    Returns:
        Status message
    """
    model = _read_model()
    node = _find_node(node_id, model)

    if not node or "visualization" not in node:
        return f"No visualization for {node_id}"

    viz = node["visualization"]
    viz["status"] = "finished"
    viz["view_name"] = view_name
    viz["element_count"] = element_count
    viz["completed_at"] = datetime.now().isoformat()

    # Track created views
    if view_name not in viz["schauspieler_sub"]["views_created"]:
        viz["schauspieler_sub"]["views_created"].append(view_name)

    _write_model(model)
    return f"Finished {node_id} visualization: {view_name}"


def mark_error(node_id: str, error_message: str) -> str:
    """
    SchauspielerSub marks visualization as error.

    Args:
        node_id: Node that failed
        error_message: Error description

    Returns:
        Status message
    """
    model = _read_model()
    node = _find_node(node_id, model)

    if not node or "visualization" not in node:
        return f"No visualization for {node_id}"

    node["visualization"]["status"] = "error"
    node["visualization"]["error"] = error_message
    node["visualization"]["completed_at"] = datetime.now().isoformat()

    _write_model(model)
    return f"Marked {node_id} visualization as error: {error_message}"


# === Main Schauspieler API ===

def scan_all_requests() -> List[Dict[str, Any]]:
    """
    Main Schauspieler scans all nodes for visualization requests.

    Returns:
        List of {node_id, request, status} dicts for all active requests
    """
    model = _read_model()
    requests = []

    for node in model.get("nodes", []):
        node_id = node.get("id")
        viz = node.get("visualization")

        if viz and viz.get("status") in ["requested", "in_progress"]:
            requests.append({
                "node_id": node_id,
                "request": viz.get("current_request"),
                "status": viz.get("status")
            })

    return requests


def get_all_views() -> List[Dict[str, Any]]:
    """
    Main Schauspieler gets all views created by SchauspielerSubs.

    Returns:
        List of {node_id, views} dicts
    """
    model = _read_model()
    all_views = []

    for node in model.get("nodes", []):
        node_id = node.get("id")
        viz = node.get("visualization")

        if viz:
            views = viz.get("schauspieler_sub", {}).get("views_created", [])
            if views:
                all_views.append({
                    "node_id": node_id,
                    "views": views
                })

    return all_views


# CLI
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("SchauspielerSub Protocol")
        print()
        print("NodeAgent commands:")
        print("  request <node_id> <viz_type>  - Request visualization")
        print("  status <node_id>              - Check status")
        print("  clear <node_id>               - Clear request")
        print()
        print("SchauspielerSub commands:")
        print("  poll <node_id>                - Poll for requests")
        print("  start <node_id>               - Mark in progress")
        print("  finish <node_id> <view_name>  - Mark finished")
        print("  error <node_id> <message>     - Mark error")
        print()
        print("Main Schauspieler commands:")
        print("  scan                          - Scan all requests")
        print("  views                         - Get all sub views")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "request" and len(sys.argv) >= 4:
        print(request_visualization(sys.argv[2], sys.argv[3]))

    elif cmd == "status" and len(sys.argv) >= 3:
        status = check_status(sys.argv[2])
        print(json.dumps(status, indent=2) if status else "No status")

    elif cmd == "clear" and len(sys.argv) >= 3:
        print(clear_request(sys.argv[2]))

    elif cmd == "poll" and len(sys.argv) >= 3:
        req = poll_requests(sys.argv[2])
        print(json.dumps(req, indent=2) if req else "No requests")

    elif cmd == "start" and len(sys.argv) >= 3:
        print(mark_in_progress(sys.argv[2]))

    elif cmd == "finish" and len(sys.argv) >= 4:
        print(mark_finished(sys.argv[2], sys.argv[3]))

    elif cmd == "error" and len(sys.argv) >= 4:
        print(mark_error(sys.argv[2], " ".join(sys.argv[3:])))

    elif cmd == "scan":
        requests = scan_all_requests()
        print(json.dumps(requests, indent=2))

    elif cmd == "views":
        views = get_all_views()
        print(json.dumps(views, indent=2))

    else:
        print(f"Unknown command: {cmd}")
