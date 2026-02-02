from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

from .loader import load_merged_model
from .writeback import read_json, write_json, resolve_node_model_file


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class MoveSummary:
    moved_node_ids: List[str]
    source_files: List[str]
    dest_file: str


def _node_type(graph: Any, node_id: str) -> str | None:
    n = getattr(graph, "nodes", {}).get(node_id)
    if isinstance(n, dict):
        t = n.get("type")
        return t if isinstance(t, str) else None
    return None


def _out_edges(graph: Any, *, edge_type: str, from_id: str) -> Iterable[Dict[str, Any]]:
    for e in getattr(graph, "edges", []):
        if not isinstance(e, dict):
            continue
        if e.get("type") != edge_type:
            continue
        if e.get("from") != from_id:
            continue
        yield e


def _in_edges(graph: Any, *, edge_type: str, to_id: str) -> Iterable[Dict[str, Any]]:
    for e in getattr(graph, "edges", []):
        if not isinstance(e, dict):
            continue
        if e.get("type") != edge_type:
            continue
        if e.get("to") != to_id:
            continue
        yield e


def compute_move_closure(graph: Any, seed_node_ids: Iterable[str]) -> Set[str]:
    """Compute the minimal closure that must move together.

    v0 closure rules:
    - Audit <-> Check via HAS_CHECK (move both directions)
    - Reality/Subsystem containment via CONTAINS (move descendants)

    This makes "partial moves" hard: moving an Audit always brings its Checks.
    """

    queue: List[str] = [nid for nid in seed_node_ids if isinstance(nid, str)]
    seen: Set[str] = set()

    while queue:
        nid = queue.pop(0)
        if nid in seen:
            continue
        seen.add(nid)

        t = _node_type(graph, nid)

        if t == "Audit":
            for e in _out_edges(graph, edge_type="HAS_CHECK", from_id=nid):
                to_id = e.get("to")
                if isinstance(to_id, str) and to_id not in seen:
                    queue.append(to_id)

        if t == "Check":
            for e in _in_edges(graph, edge_type="HAS_CHECK", to_id=nid):
                from_id = e.get("from")
                if isinstance(from_id, str) and from_id not in seen:
                    queue.append(from_id)

        if t in {"Reality", "Subsystem"}:
            for e in _out_edges(graph, edge_type="CONTAINS", from_id=nid):
                to_id = e.get("to")
                if isinstance(to_id, str) and to_id not in seen:
                    queue.append(to_id)

    return seen


def move_nodes_to_file(
    *,
    root_model_path: Path,
    seed_node_ids: List[str],
    dest_model_file: Path,
    include_closure: bool = True,
) -> MoveSummary:
    """Move nodes (and their attachment-closure) into `dest_model_file`.

    This performs an actual rewrite:
    - removes nodes from their provenance files
    - appends nodes to the destination model file

    It does not currently move edges; instead it relies on audits to scream if
    structural attachments become inconsistent.
    """

    root_model_path = root_model_path.resolve()
    dest_model_file = dest_model_file.resolve()

    graph = load_merged_model(root_model_path)

    closure = compute_move_closure(graph, seed_node_ids) if include_closure else set(seed_node_ids)

    # Resolve per-node source file.
    by_source: Dict[Path, List[str]] = {}
    for nid in sorted(closure):
        src = resolve_node_model_file(graph=graph, node_id=nid, default_model_file=root_model_path)
        by_source.setdefault(src, []).append(nid)

    # Create destination model if missing.
    if not dest_model_file.exists():
        dest_model_file.parent.mkdir(parents=True, exist_ok=True)
        write_json(
            dest_model_file,
            {
                "schema_version": "3.0",
                "project": "moved-bundle",
                "description": "Created by root_store.move_nodes_to_file",
                "updated_at": _utc_now(),
                "nodes": [],
                "edges": [],
            },
        )

    dest_model = read_json(dest_model_file)
    dest_nodes = dest_model.get("nodes", [])
    if not isinstance(dest_nodes, list):
        raise ValueError(f"Destination model nodes is not a list: {dest_model_file}")

    existing_ids = {
        n.get("id")
        for n in dest_nodes
        if isinstance(n, dict) and isinstance(n.get("id"), str)
    }

    # Remove from sources and collect moved node dicts.
    moved_nodes: List[Dict[str, Any]] = []
    for src_file, ids in by_source.items():
        model = read_json(src_file)
        nodes = model.get("nodes", [])
        if not isinstance(nodes, list):
            continue

        kept: List[Any] = []
        for n in nodes:
            if not isinstance(n, dict) or not isinstance(n.get("id"), str):
                kept.append(n)
                continue
            if n["id"] in closure:
                if n["id"] in existing_ids:
                    raise ValueError(f"Destination already has node id: {n['id']}")
                moved_nodes.append(n)
            else:
                kept.append(n)

        if len(kept) != len(nodes):
            model["nodes"] = kept
            model["updated_at"] = _utc_now()
            write_json(src_file, model)

    if not moved_nodes:
        raise ValueError("No nodes were moved (ids not found in provenance files?)")

    dest_nodes.extend(moved_nodes)
    dest_model["nodes"] = dest_nodes
    dest_model["updated_at"] = _utc_now()
    write_json(dest_model_file, dest_model)

    return MoveSummary(
        moved_node_ids=sorted([n.get("id") for n in moved_nodes if isinstance(n.get("id"), str)]),
        source_files=sorted([p.as_posix() for p in by_source.keys()]),
        dest_file=dest_model_file.as_posix(),
    )
