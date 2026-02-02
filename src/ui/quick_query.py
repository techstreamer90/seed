#!/usr/bin/env python3
"""
Quick Query - Fast query helpers for Claude to get node information.

These return text that Claude can read directly, not UI commands.

Usage:
    from src.ui.quick_query import get_status, get_hierarchy_text, get_children

    get_status("BAM")                    # Human-readable status text
    get_hierarchy_text("reality-bam", 3) # ASCII tree view
    get_children("reality-bam")          # List of child node IDs
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.root_store.loader import load_merged_model

# Default model path
MODEL_PATH = Path(__file__).parent.parent.parent / "model" / "sketch.json"


def _get_graph(model_path: Optional[Path] = None):
    """Load the merged model graph."""
    path = model_path or MODEL_PATH
    return load_merged_model(path.resolve())


def get_node(node_id: str, model_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Get a single node by ID.

    Args:
        node_id: The node ID to look up
        model_path: Optional custom model path

    Returns:
        Node dict or None if not found
    """
    graph = _get_graph(model_path)
    return graph.nodes.get(node_id)


def get_status(node_id: str, model_path: Optional[Path] = None) -> str:
    """Get human-readable status text for a node.

    Args:
        node_id: The node ID to get status for
        model_path: Optional custom model path

    Returns:
        Human-readable status text
    """
    graph = _get_graph(model_path)
    node = graph.nodes.get(node_id)

    if not node:
        return f"Node '{node_id}' not found"

    lines = []
    lines.append(f"Node: {node.get('label', node_id)}")
    lines.append(f"Type: {node.get('type', 'Unknown')}")

    if node.get("status"):
        lines.append(f"Status: {node['status']}")

    if node.get("description"):
        lines.append(f"Description: {node['description']}")

    # Check for evidence/save_exec status
    ev = node.get("evidence", {})
    if isinstance(ev, dict):
        se = ev.get("save_exec", {})
        if isinstance(se, dict):
            lr = se.get("last_run", {})
            if isinstance(lr, dict):
                ok = lr.get("ok")
                ran_at = lr.get("ran_at", "")
                if ok is True:
                    lines.append(f"Save-exec: OK at {ran_at}")
                elif ok is False:
                    lines.append(f"Save-exec: FAILED at {ran_at}")

    return "\n".join(lines)


def get_hierarchy_text(
    node_id: str,
    depth: int = 3,
    model_path: Optional[Path] = None,
) -> str:
    """Get ASCII tree view of a node's hierarchy.

    Args:
        node_id: The root node ID
        depth: How many levels deep to show
        model_path: Optional custom model path

    Returns:
        ASCII tree text
    """
    path = model_path or MODEL_PATH
    graph = _get_graph(path)

    # Build a simple ASCII tree instead of using rich (for Windows compatibility)
    lines: List[str] = []

    def add_node(nid: str, indent: int, current_depth: int) -> None:
        if current_depth >= depth:
            return
        node = graph.nodes.get(nid)
        if not node:
            return

        # Get status indicator
        status = (node.get("status") or "").lower()
        if status in ("pass", "ok", "green", "active"):
            indicator = "[OK]"
        elif status in ("fail", "error", "red"):
            indicator = "[X]"
        elif status in ("warn", "warning", "yellow"):
            indicator = "[!]"
        else:
            indicator = "[*]"

        # Build line
        prefix = "  " * indent
        label = node.get("label") or nid
        ntype = node.get("type", "")
        status_str = f" status={status}" if status else ""
        lines.append(f"{prefix}{indicator} {label}  ({ntype}){status_str}  id={nid}")

        # Find children
        children = []
        for edge in graph.edges:
            if edge.get("type") == "CONTAINS" and edge.get("from") == nid:
                to_id = edge.get("to")
                if to_id and to_id in graph.nodes:
                    children.append(to_id)
        for child_nid, child_node in graph.nodes.items():
            if child_node.get("parent") == nid and child_nid not in children:
                children.append(child_nid)

        # Sort and recurse
        children.sort(key=lambda x: (graph.nodes.get(x, {}).get("label") or x).lower())
        for child_id in children:
            add_node(child_id, indent + 1, current_depth + 1)

    add_node(node_id, 0, 0)
    return "\n".join(lines)


def get_children(node_id: str, model_path: Optional[Path] = None) -> List[str]:
    """Get list of child node IDs (via CONTAINS edges or parent field).

    Args:
        node_id: The parent node ID
        model_path: Optional custom model path

    Returns:
        List of child node IDs
    """
    graph = _get_graph(model_path)
    children = []

    # Check edges for CONTAINS
    for edge in graph.edges:
        if edge.get("type") == "CONTAINS" and edge.get("from") == node_id:
            to_id = edge.get("to")
            if to_id and to_id not in children:
                children.append(to_id)

    # Check nodes for parent field
    for nid, node in graph.nodes.items():
        if node.get("parent") == node_id and nid not in children:
            children.append(nid)

    return sorted(children)


def get_related(
    node_id: str,
    edge_type: Optional[str] = None,
    direction: str = "outgoing",
    model_path: Optional[Path] = None,
) -> List[Dict[str, str]]:
    """Get related nodes via edges.

    Args:
        node_id: The source node ID
        edge_type: Filter by edge type (e.g., "USES", "NEEDS")
        direction: "outgoing", "incoming", or "both"
        model_path: Optional custom model path

    Returns:
        List of dicts with {id, label, type, edge_type}
    """
    graph = _get_graph(model_path)
    results = []

    for edge in graph.edges:
        if edge_type and edge.get("type") != edge_type:
            continue

        related_id = None
        if direction in ("outgoing", "both") and edge.get("from") == node_id:
            related_id = edge.get("to")
        elif direction in ("incoming", "both") and edge.get("to") == node_id:
            related_id = edge.get("from")

        if related_id and related_id in graph.nodes:
            node = graph.nodes[related_id]
            results.append({
                "id": related_id,
                "label": node.get("label", related_id),
                "type": node.get("type", "Unknown"),
                "edge_type": edge.get("type"),
            })

    return results


def get_world_overview(depth: int = 2, model_path: Optional[Path] = None) -> str:
    """Get "This is your world" overview - a quick map of all nodes.

    Shows nodes grouped by type, with hierarchy for Reality nodes.
    This is the goto function when you need to orient yourself.

    Args:
        depth: How many levels deep to show for hierarchies
        model_path: Optional custom model path

    Returns:
        Text overview of the entire world
    """
    graph = _get_graph(model_path)

    lines: List[str] = []
    lines.append("=" * 60)
    lines.append("THIS IS YOUR WORLD")
    lines.append("=" * 60)
    lines.append("")

    # Count nodes by type
    type_counts: Dict[str, int] = {}
    for node in graph.nodes.values():
        ntype = node.get("type", "Unknown")
        type_counts[ntype] = type_counts.get(ntype, 0) + 1

    lines.append(f"Total: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
    lines.append("")

    # Priority order for types
    priority_types = ["Reality", "Subsystem", "Module", "Aspiration", "Gap", "Todo", "Concept"]

    # Show Realities first with their hierarchy
    lines.append("-" * 40)
    lines.append("REALITIES (your main entry points)")
    lines.append("-" * 40)

    realities = [(nid, n) for nid, n in graph.nodes.items() if n.get("type") == "Reality"]
    realities.sort(key=lambda x: (x[1].get("label") or x[0]).lower())

    for nid, node in realities:
        label = node.get("label") or nid
        status = node.get("status", "")
        status_str = f" [{status}]" if status else ""
        lines.append(f"  * {label}{status_str}")
        lines.append(f"    id: {nid}")

        # Show children (subsystems, modules) to depth
        children = []
        for edge in graph.edges:
            if edge.get("type") == "CONTAINS" and edge.get("from") == nid:
                child_id = edge.get("to")
                if child_id in graph.nodes:
                    child = graph.nodes[child_id]
                    children.append((child_id, child))

        # Also check parent field
        for child_id, child in graph.nodes.items():
            if child.get("parent") == nid and (child_id, child) not in children:
                children.append((child_id, child))

        if children and depth > 1:
            for child_id, child in sorted(children, key=lambda x: (x[1].get("label") or x[0]).lower()):
                child_label = child.get("label") or child_id
                child_type = child.get("type", "")
                lines.append(f"      - {child_label} ({child_type})")

        lines.append("")

    # Show other important types
    for ntype in ["Aspiration", "Gap", "Todo", "Concept"]:
        nodes_of_type = [(nid, n) for nid, n in graph.nodes.items() if n.get("type") == ntype]
        if not nodes_of_type:
            continue

        lines.append("-" * 40)
        lines.append(f"{ntype.upper()}S ({len(nodes_of_type)})")
        lines.append("-" * 40)

        nodes_of_type.sort(key=lambda x: (x[1].get("label") or x[0]).lower())
        for nid, node in nodes_of_type[:10]:  # Limit to 10 per type
            label = node.get("label") or nid
            status = node.get("status", "")
            status_str = f" [{status}]" if status else ""
            lines.append(f"  * {label}{status_str}")
            lines.append(f"    id: {nid}")

        if len(nodes_of_type) > 10:
            lines.append(f"  ... and {len(nodes_of_type) - 10} more")
        lines.append("")

    # Summary of other types
    other_types = [t for t in type_counts.keys() if t not in priority_types]
    if other_types:
        lines.append("-" * 40)
        lines.append("OTHER NODE TYPES")
        lines.append("-" * 40)
        for ntype in sorted(other_types):
            lines.append(f"  {ntype}: {type_counts[ntype]}")
        lines.append("")

    lines.append("=" * 60)
    lines.append("Use ui.focus('node-id') to zoom to a node")
    lines.append("Use ui.status('node-id') to see hierarchy")
    lines.append("=" * 60)

    return "\n".join(lines)


def query(query_text: str, model_path: Optional[Path] = None) -> str:
    """Natural language query interface.

    Supports patterns like:
    - "status of <node_id>"
    - "<node_id> children"
    - "<node_id> hierarchy"
    - "find <type>" (e.g., "find Reality")
    - "node <node_id>"

    Args:
        query_text: Natural language query
        model_path: Optional custom model path

    Returns:
        Text response
    """
    q = query_text.strip().lower()

    # Pattern: "status of <node_id>"
    match = re.match(r"status\s+(?:of\s+)?(\S+)", q)
    if match:
        return get_status(match.group(1), model_path)

    # Pattern: "<node_id> children"
    match = re.match(r"(\S+)\s+children", q)
    if match:
        children = get_children(match.group(1), model_path)
        if not children:
            return f"No children found for '{match.group(1)}'"
        return "Children:\n" + "\n".join(f"  - {c}" for c in children)

    # Pattern: "<node_id> hierarchy"
    match = re.match(r"(\S+)\s+hierarchy(?:\s+(\d+))?", q)
    if match:
        depth = int(match.group(2)) if match.group(2) else 3
        return get_hierarchy_text(match.group(1), depth, model_path)

    # Pattern: "find <type>"
    match = re.match(r"find\s+(\S+)", q)
    if match:
        type_name = match.group(1)
        graph = _get_graph(model_path)
        found = []
        for nid, node in graph.nodes.items():
            if (node.get("type") or "").lower() == type_name.lower():
                found.append(f"  - {nid}: {node.get('label', nid)}")
        if not found:
            return f"No nodes of type '{type_name}' found"
        return f"Nodes of type '{type_name}':\n" + "\n".join(found[:20])

    # Pattern: "node <node_id>"
    match = re.match(r"node\s+(\S+)", q)
    if match:
        return get_status(match.group(1), model_path)

    # Default: try as node ID
    node = get_node(query_text.strip(), model_path)
    if node:
        return get_status(query_text.strip(), model_path)

    return f"Unknown query: '{query_text}'. Try: 'status of <node_id>', '<node_id> children', '<node_id> hierarchy', 'find <type>'"


# CLI support
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python quick_query.py <query>")
        print("Examples:")
        print("  python quick_query.py 'status of reality-seed'")
        print("  python quick_query.py 'reality-bam children'")
        print("  python quick_query.py 'reality-bam hierarchy 3'")
        print("  python quick_query.py 'find Reality'")
        sys.exit(1)

    result = query(" ".join(sys.argv[1:]))
    print(result)
