"""Delete nodes from the model and their corresponding source files.

This module provides the "delete button" counterpart to the "save button",
ensuring model and reality stay in sync when removing nodes.

Deletion is recursive ("turtles all the way down"):
- Deleting a Reality/Subsystem deletes all CONTAINS descendants
- Deleting an Audit deletes its Checks (HAS_CHECK bidirectional)
- Each deleted node's source files/folders are removed from disk
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

from .loader import load_merged_model
from .writeback import read_json, write_json, resolve_node_model_file


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def _model_base_dir_for_provenance_file(prov_file: str) -> Path:
    """Get base directory for a model file.

    Convention: model file lives at <base>/model/sketch.json
    So base dir is parent.parent.
    """
    p = Path(prov_file)
    try:
        return p.parent.parent
    except Exception:
        return p.parent


def compute_delete_closure(graph: Any, seed_node_ids: Iterable[str]) -> Set[str]:
    """Compute the minimal closure that must be deleted together.

    Deletion closure rules (same as move):
    - Audit <-> Check via HAS_CHECK (delete both directions)
    - Reality/Subsystem containment via CONTAINS (delete all descendants)

    This makes "partial deletes" impossible: deleting a parent always
    deletes children, deleting an Audit always deletes its Checks.
    """

    queue: List[str] = [nid for nid in seed_node_ids if isinstance(nid, str)]
    seen: Set[str] = set()

    while queue:
        nid = queue.pop(0)
        if nid in seen:
            continue
        seen.add(nid)

        t = _node_type(graph, nid)

        # Audit -> Check via HAS_CHECK
        if t == "Audit":
            for e in _out_edges(graph, edge_type="HAS_CHECK", from_id=nid):
                to_id = e.get("to")
                if isinstance(to_id, str) and to_id not in seen:
                    queue.append(to_id)

        # Check <- Audit via HAS_CHECK (bidirectional)
        if t == "Check":
            for e in _in_edges(graph, edge_type="HAS_CHECK", to_id=nid):
                from_id = e.get("from")
                if isinstance(from_id, str) and from_id not in seen:
                    queue.append(from_id)

        # Reality/Subsystem -> children via CONTAINS
        if t in {"Reality", "Subsystem"}:
            for e in _out_edges(graph, edge_type="CONTAINS", from_id=nid):
                to_id = e.get("to")
                if isinstance(to_id, str) and to_id not in seen:
                    queue.append(to_id)

    return seen


def resolve_source_paths(
    graph: Any,
    node_ids: Set[str],
    root_model_path: Path,
) -> Dict[str, Path]:
    """Resolve source file/folder paths for nodes.

    Returns a mapping from node_id to the full resolved path of its source.
    Only includes nodes that have a source.path defined.
    """

    result: Dict[str, Path] = {}

    for nid in node_ids:
        node = graph.nodes.get(nid)
        if not isinstance(node, dict):
            continue

        source = node.get("source")
        if not isinstance(source, dict):
            continue

        # Get the relative path (could be 'path' for files or directories)
        rel_path = source.get("path")
        if not isinstance(rel_path, str) or not rel_path:
            continue

        # Resolve base directory from provenance
        prov = graph.provenance_by_node_id.get(nid)
        if prov:
            base_dir = _model_base_dir_for_provenance_file(prov.file)
        else:
            base_dir = root_model_path.parent.parent

        full_path = (base_dir / rel_path).resolve()
        result[nid] = full_path

    return result


@dataclass
class DeleteResult:
    """Result of a delete operation."""
    seed_node_id: str
    deleted_node_ids: List[str]
    deleted_source_paths: List[str]
    removed_edge_count: int
    model_files_updated: List[str]
    ok: bool
    errors: List[str] = field(default_factory=list)


def delete_nodes(
    *,
    root_model_path: Path,
    seed_node_ids: List[str],
    delete_source_files: bool = True,
    dry_run: bool = False,
) -> DeleteResult:
    """Delete nodes and their source files from model and disk.

    This is the "delete button" - the counterpart to verbal_save.
    It removes nodes from the model and optionally deletes their
    corresponding source files/folders.

    Args:
        root_model_path: Path to the root model file
        seed_node_ids: Node IDs to delete (will include closure)
        delete_source_files: Whether to delete source files/folders
        dry_run: If True, compute what would be deleted but don't actually delete

    Returns:
        DeleteResult with summary of the operation
    """

    root_model_path = root_model_path.resolve()
    errors: List[str] = []

    # 1. Load the merged model
    graph = load_merged_model(root_model_path)

    # Verify seed nodes exist
    for nid in seed_node_ids:
        if nid not in graph.nodes:
            errors.append(f"Node not found: {nid}")

    if errors:
        return DeleteResult(
            seed_node_id=seed_node_ids[0] if seed_node_ids else "",
            deleted_node_ids=[],
            deleted_source_paths=[],
            removed_edge_count=0,
            model_files_updated=[],
            ok=False,
            errors=errors,
        )

    # 2. Compute deletion closure
    closure = compute_delete_closure(graph, seed_node_ids)

    # 3. Resolve source paths for all nodes in closure
    source_paths = resolve_source_paths(graph, closure, root_model_path)

    # 4. Group nodes by their provenance model file
    by_file: Dict[Path, List[str]] = {}
    for nid in sorted(closure):
        src_file = resolve_node_model_file(
            graph=graph, node_id=nid, default_model_file=root_model_path
        )
        by_file.setdefault(src_file, []).append(nid)

    # 5. Identify edges to remove (any edge touching a deleted node)
    edges_to_remove: List[int] = []
    for idx, e in enumerate(graph.edges):
        if not isinstance(e, dict):
            continue
        from_id = e.get("from")
        to_id = e.get("to")
        if from_id in closure or to_id in closure:
            edges_to_remove.append(idx)

    if dry_run:
        return DeleteResult(
            seed_node_id=seed_node_ids[0] if seed_node_ids else "",
            deleted_node_ids=sorted(closure),
            deleted_source_paths=[str(p) for p in source_paths.values() if p.exists()],
            removed_edge_count=len(edges_to_remove),
            model_files_updated=sorted(str(f) for f in by_file.keys()),
            ok=True,
            errors=[],
        )

    # 6. Remove nodes from model files
    updated_files: List[str] = []
    for model_file, node_ids_to_remove in by_file.items():
        try:
            model = read_json(model_file)
            nodes = model.get("nodes", [])
            edges = model.get("edges", [])

            if not isinstance(nodes, list):
                errors.append(f"Nodes is not a list in {model_file}")
                continue

            # Filter out deleted nodes
            ids_set = set(node_ids_to_remove)
            kept_nodes = [
                n for n in nodes
                if not (isinstance(n, dict) and n.get("id") in ids_set)
            ]

            # Filter out edges touching deleted nodes
            kept_edges = [
                e for e in edges
                if not (isinstance(e, dict) and (
                    e.get("from") in closure or e.get("to") in closure
                ))
            ]

            if len(kept_nodes) != len(nodes) or len(kept_edges) != len(edges):
                model["nodes"] = kept_nodes
                model["edges"] = kept_edges
                model["updated_at"] = _utc_now()
                write_json(model_file, model)
                updated_files.append(str(model_file))

        except Exception as e:
            errors.append(f"Failed to update {model_file}: {e}")

    # 7. Delete source files/folders
    deleted_paths: List[str] = []
    if delete_source_files:
        for nid, full_path in source_paths.items():
            if not full_path.exists():
                continue
            try:
                if full_path.is_dir():
                    shutil.rmtree(full_path)
                else:
                    full_path.unlink()
                deleted_paths.append(str(full_path))
            except Exception as e:
                errors.append(f"Failed to delete {full_path}: {e}")

    return DeleteResult(
        seed_node_id=seed_node_ids[0] if seed_node_ids else "",
        deleted_node_ids=sorted(closure),
        deleted_source_paths=deleted_paths,
        removed_edge_count=len(edges_to_remove),
        model_files_updated=updated_files,
        ok=len(errors) == 0,
        errors=errors,
    )
