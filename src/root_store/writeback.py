from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from typing import Any, Callable, Dict, Mapping


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def update_node_in_file(*, model_file: Path, node_id: str, update: Callable[[Dict[str, Any]], None]) -> bool:
    """Update a node in a specific model file.

    Returns True if the node was found and updated.
    """

    model_file = model_file.resolve()
    model = read_json(model_file)
    nodes = model.get("nodes", [])
    if not isinstance(nodes, list):
        return False

    for n in nodes:
        if isinstance(n, dict) and n.get("id") == node_id:
            update(n)
            write_json(model_file, model)
            return True

    return False


def resolve_node_model_file(*, graph: Any, node_id: str, default_model_file: Path) -> Path:
    """Resolve which model file defines `node_id`.

    Uses `graph.provenance_by_node_id[node_id].file` when available.
    Falls back to `default_model_file`.
    """

    prov_map = getattr(graph, "provenance_by_node_id", None)
    if isinstance(prov_map, dict):
        prov = prov_map.get(node_id)
        prov_file = getattr(prov, "file", None)
        if isinstance(prov_file, str) and prov_file:
            return Path(prov_file).resolve()
    return default_model_file.resolve()


def apply_node_updates(
    *,
    graph: Any,
    default_model_file: Path,
    updates: Mapping[str, Callable[[Dict[str, Any]], None]],
) -> Dict[str, bool]:
    """Apply node updates across provenance files.

    Groups updates per model file so each file is read/written once.
    Returns a per-node success map.
    """

    by_file: Dict[Path, list[tuple[str, Callable[[Dict[str, Any]], None]]]] = defaultdict(list)
    for node_id, update in updates.items():
        model_file = resolve_node_model_file(graph=graph, node_id=node_id, default_model_file=default_model_file)
        by_file[model_file].append((node_id, update))

    results: Dict[str, bool] = {node_id: False for node_id in updates}

    for model_file, items in by_file.items():
        try:
            model = read_json(model_file)
        except Exception:
            continue

        nodes = model.get("nodes", [])
        if not isinstance(nodes, list):
            continue

        nodes_by_id: Dict[str, Dict[str, Any]] = {
            n["id"]: n
            for n in nodes
            if isinstance(n, dict) and isinstance(n.get("id"), str)
        }

        changed = False
        for node_id, update in items:
            node = nodes_by_id.get(node_id)
            if node is None:
                continue
            update(node)
            results[node_id] = True
            changed = True

        if changed:
            write_json(model_file, model)

    return results
