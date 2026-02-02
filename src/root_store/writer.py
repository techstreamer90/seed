from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .enforcement import validate_change_gate
from .loader import load_merged_model
from .writeback import apply_node_updates


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def apply_change(root_model_path: Path, change_id: str) -> None:
    """Apply a modeled Change.

    This is intentionally conservative for v0:
    - Enforces the change gate
    - Does NOT attempt structural patches yet (that will come in v1)

    In practice, v0 is used to prove the enforcement/audit loop is real.
    """

    # Use merged view so Change nodes can live in submodels.
    graph = load_merged_model(root_model_path)
    gate = validate_change_gate(graph, change_id)
    if not gate.ok:
        raise ValueError("Change gate failed: " + "; ".join(gate.errors))

    # v0: no-op patch. We still stamp evidence that the gate passed.
    def _stamp_writer_evidence(n: Dict[str, Any]) -> None:
        ev = n.get("evidence")
        if not isinstance(ev, dict):
            ev = {}
        ev.setdefault("writer", {})
        if isinstance(ev.get("writer"), dict):
            ev["writer"].update({"gate": "pass", "applied": False})
        n["evidence"] = ev

    apply_node_updates(
        graph=graph,
        default_model_file=root_model_path,
        updates={change_id: _stamp_writer_evidence},
    )
