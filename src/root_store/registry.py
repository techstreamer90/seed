from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .loader import LoadedGraph


@dataclass(frozen=True)
class ModelRoot:
    """A root-entry model path for a world."""

    reality_id: str
    model_file: Path


def _as_path(p: str) -> Path:
    # Accept both C:/... and Windows paths.
    if p.startswith("C:/"):
        return Path(p.replace("/", "\\"))
    return Path(p)


def discover_model_roots(graph: LoadedGraph) -> List[ModelRoot]:
    """Discover model roots from Reality nodes.

    v0 convention: a Reality with source.path and source.model_path points at a root-entry model file.

    This intentionally does not require a dedicated registry schema yet; the model itself is the registry.
    """

    roots: List[ModelRoot] = []

    for nid, n in graph.nodes.items():
        if n.get("type") != "Reality":
            continue
        source = n.get("source")
        if not isinstance(source, dict):
            continue
        base = source.get("path")
        rel = source.get("model_path")
        if not (isinstance(base, str) and base and isinstance(rel, str) and rel):
            continue

        model_file = (_as_path(base) / rel).resolve()
        roots.append(ModelRoot(reality_id=nid, model_file=model_file))

    # Deterministic order
    roots.sort(key=lambda r: (r.model_file.as_posix().lower(), r.reality_id))

    # Only keep existing model files for now
    existing: List[ModelRoot] = []
    seen: set[Path] = set()
    for r in roots:
        if r.model_file.exists() and r.model_file not in seen:
            existing.append(r)
            seen.add(r.model_file)

    return existing
