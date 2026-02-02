from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class EnforcementResult:
    ok: bool
    errors: List[str]


def validate_change_gate(model: Any, change_id: str) -> EnforcementResult:
    """Enforce the modeled change gate using edges as the ground truth.

    Requirements (v0):
    - Change exists
    - Has at least one ADDRESSES edge to a Gap
    - Has at least one ADVANCES edge to an Aspiration
    - Has non-empty evidence_required (either list or dict)
    """

    # Accept either a raw single-file model dict (`{"nodes": [...], "edges": [...]}`)
    # or a merged graph (`LoadedGraph`) with `nodes: Dict[str, node]` and `edges: List[edge]`.
    if isinstance(model, dict) and isinstance(model.get("nodes"), list):
        nodes = {n.get("id"): n for n in model.get("nodes", []) if isinstance(n.get("id"), str)}
        edges = model.get("edges", [])
    else:
        nodes = getattr(model, "nodes", {})
        edges = getattr(model, "edges", [])

    change = nodes.get(change_id)
    errors: List[str] = []

    if change is None:
        return EnforcementResult(ok=False, errors=[f"Change not found: {change_id}"])
    if change.get("type") != "Change":
        errors.append(f"Node is not a Change: {change_id}")

    addresses = [e for e in edges if e.get("type") == "ADDRESSES" and e.get("from") == change_id]
    advances = [e for e in edges if e.get("type") == "ADVANCES" and e.get("from") == change_id]

    if not addresses:
        errors.append(f"Change has no ADDRESSES edges: {change_id}")
    if not advances:
        errors.append(f"Change has no ADVANCES edges: {change_id}")

    er = change.get("evidence_required")
    has_required = bool(er) and (isinstance(er, (list, dict)))
    if not has_required:
        errors.append(f"Change.evidence_required missing/empty: {change_id}")

    return EnforcementResult(ok=(len(errors) == 0), errors=errors)
