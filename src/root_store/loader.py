from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List


@dataclass(frozen=True)
class Provenance:
    file: str


@dataclass
class LoadedGraph:
    nodes: Dict[str, Dict[str, Any]]
    edges: List[Dict[str, Any]]
    provenance_by_node_id: Dict[str, Provenance]
    provenance_by_edge_index: Dict[int, Provenance]


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_ref_path(ref: str) -> Path:
    # Accept both C:/seed/... and relative paths.
    if ref.startswith("C:/"):
        return Path(ref.replace("/", "\\"))
    return Path(ref)


def _discover_model_refs(model: Dict[str, Any]) -> Iterable[str]:
    for node in model.get("nodes", []):
        mm = node.get("model")
        if isinstance(mm, dict) and isinstance(mm.get("_ref"), str):
            yield mm["_ref"]


def discover_model_files(root_model_paths: List[Path]) -> List[Path]:
    """Discover all model files reachable from one or more root entry models.

    This follows nested `_ref` links recursively.
    """

    queue: List[Path] = [p.resolve() for p in root_model_paths]
    seen: set[Path] = set()

    while queue:
        p = queue.pop(0).resolve()
        if p in seen:
            continue
        seen.add(p)

        try:
            model = _read_json(p)
        except Exception:
            continue

        base_dir = p.parent.parent
        for ref in _discover_model_refs(model):
            ref_path = _normalize_ref_path(ref)
            if not ref_path.is_absolute():
                ref_path = (base_dir / ref_path).resolve()
            if ref_path.exists() and ref_path not in seen:
                queue.append(ref_path)

    return sorted(seen)


def load_merged_models(root_model_paths: List[Path]) -> LoadedGraph:
    """Load one logical graph from multiple root entry models.

    Merge strategy is the same as `load_merged_model` (first definition wins).
    """

    roots = [p.resolve() for p in root_model_paths]
    files = discover_model_files(roots)

    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []
    prov_nodes: Dict[str, Provenance] = {}
    prov_edges: Dict[int, Provenance] = {}

    def ingest(model: Dict[str, Any], file_path: Path) -> None:
        file_str = file_path.as_posix()
        for n in model.get("nodes", []):
            nid = n.get("id")
            if isinstance(nid, str) and nid not in nodes:
                nodes[nid] = n
                prov_nodes[nid] = Provenance(file=file_str)
        start = len(edges)
        edges.extend(model.get("edges", []))
        for idx in range(start, len(edges)):
            prov_edges[idx] = Provenance(file=file_str)

    for f in files:
        try:
            ingest(_read_json(f), f)
        except Exception:
            continue

    return LoadedGraph(
        nodes=nodes,
        edges=edges,
        provenance_by_node_id=prov_nodes,
        provenance_by_edge_index=prov_edges,
    )


def load_merged_model(root_model_path: Path) -> LoadedGraph:
    """Load root model + referenced _ref submodels into one logical graph.

    Provenance is recorded per node/edge (which file defined it).

    Merge strategy:
    - First definition wins for duplicate node ids.
    - All edges are appended; edges referencing unknown nodes are retained (audits can flag).
    """

    return load_merged_models([root_model_path])
