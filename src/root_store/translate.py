from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .loader import load_merged_model


@dataclass(frozen=True)
class HumanStateConfig:
    root_model_path: Path
    max_items: int = 10


def _safe_str(x: Any) -> str:
    return str(x) if x is not None else ""


def _pick_label(n: Dict[str, Any]) -> str:
    return _safe_str(n.get("label") or n.get("id") or "(unknown)")


def _iter_nodes_by_type(nodes: Dict[str, Dict[str, Any]], node_type: str) -> Iterable[Dict[str, Any]]:
    for n in nodes.values():
        if n.get("type") == node_type:
            yield n


def _status_bucket(status: str) -> str:
    s = (status or "").strip().lower()
    if s in {"pass", "ok", "green"}:
        return "good"
    if s in {"fail", "error", "red"}:
        return "bad"
    if s in {"warn", "warning", "yellow"}:
        return "warning"
    if s in {"planned", "ready", "proposed", "in-progress", "pending", "active", "vision", "ongoing"}:
        return "neutral"
    return "neutral"


def render_human_state(config: HumanStateConfig) -> str:
    """Render a plain-English snapshot of Root's current state.

    Goal: user-facing text. Avoid schema/type jargon.
    """

    root_model_path = config.root_model_path.resolve()
    graph = load_merged_model(root_model_path)
    nodes = graph.nodes

    root = nodes.get("reality-seed", {})
    title = _pick_label(root) or "Root"

    # --- Realities overview (top-level, from root file) ---
    root_file = str(root_model_path.as_posix())
    top_realities: List[Dict[str, Any]] = []
    for n in _iter_nodes_by_type(nodes, "Reality"):
        nid = n.get("id")
        if not isinstance(nid, str):
            continue
        prov = graph.provenance_by_node_id.get(nid)
        if prov and prov.file == root_file:
            top_realities.append(n)

    def _reality_line(r: Dict[str, Any]) -> str:
        label = _pick_label(r)
        status = _safe_str(r.get("status") or "")
        if status:
            return f"- {label} ({status})"
        return f"- {label}"

    # --- What's failing right now ---
    failing_audits: List[Dict[str, Any]] = []
    for a in _iter_nodes_by_type(nodes, "Audit"):
        if _status_bucket(_safe_str(a.get("status"))) == "bad":
            failing_audits.append(a)

    # Prefer root compliance + store consistency first
    priority_audit_ids = [
        "audit-root-compliance",
        "audit-root-store-index-consistency",
        "audit-change-executor-gate",
        "audit-seed-model-consistency",
    ]
    failing_audits.sort(key=lambda a: priority_audit_ids.index(a.get("id")) if a.get("id") in priority_audit_ids else 999)

    # --- Work queue (from the root agent_context) ---
    work_queue_items: List[str] = []
    ac = root.get("agent_context") if isinstance(root, dict) else None
    if isinstance(ac, dict):
        wq = ac.get("work_queue")
        if isinstance(wq, list):
            for item in wq[: config.max_items]:
                if not isinstance(item, dict):
                    continue
                tid = item.get("id")
                todo = nodes.get(tid) if isinstance(tid, str) else None
                if isinstance(todo, dict):
                    label = _pick_label(todo)
                    status = _safe_str(todo.get("status") or "")
                    if status:
                        work_queue_items.append(f"- {label} ({status})")
                    else:
                        work_queue_items.append(f"- {label}")

    # --- High priority gaps (human phrasing) ---
    gaps: List[Dict[str, Any]] = []
    for g in _iter_nodes_by_type(nodes, "Gap"):
        pr = _safe_str(g.get("priority") or "").lower()
        if pr in {"critical", "high"}:
            gaps.append(g)

    def _gap_sort_key(g: Dict[str, Any]) -> int:
        pr = _safe_str(g.get("priority") or "").lower()
        return 0 if pr == "critical" else 1

    gaps.sort(key=_gap_sort_key)

    # --- Scream packet hint (if present) ---
    scream_hint: Optional[str] = None
    for a in failing_audits:
        ev = a.get("evidence")
        if isinstance(ev, dict):
            scream = ev.get("scream")
            if isinstance(scream, dict) and scream.get("packet"):
                scream_hint = _safe_str(scream.get("packet"))
                break

    # --- Common "needs details" messaging (v0 heuristic) ---
    needs_details: List[str] = []
    compliance = nodes.get("audit-root-compliance")
    if isinstance(compliance, dict):
        ev = compliance.get("evidence")
        if isinstance(ev, dict):
            results = ev.get("results")
            if isinstance(results, dict):
                checks = results.get("checks")
                if isinstance(checks, dict):
                    hc = checks.get("hash_control")
                    if isinstance(hc, dict) and hc.get("missing_hash"):
                        missing = hc.get("missing_hash")
                        if isinstance(missing, list) and len(missing) > 0:
                            needs_details.append(
                                "Hash coverage is incomplete. Decide: do we auto-add file hashes now (requires a controlled change executor), or defer?"
                            )

    lines: List[str] = []
    lines.append(f"{title} — current state")
    lines.append("")

    if failing_audits:
        lines.append("What’s wrong (needs attention):")
        for a in failing_audits[: config.max_items]:
            label = _pick_label(a)
            summary = ""
            findings = a.get("findings")
            if isinstance(findings, list) and findings:
                summary = _safe_str(findings[0])
            if summary:
                lines.append(f"- {label}: {summary}")
            else:
                lines.append(f"- {label}")
        if scream_hint:
            lines.append("")
            lines.append(f"More detail captured here: {scream_hint}")
        lines.append("")
    else:
        lines.append("What’s wrong (needs attention):")
        lines.append("- Nothing obvious is failing right now.")
        lines.append("")

    if needs_details:
        lines.append("Questions / decisions needed:")
        for q in needs_details:
            lines.append(f"- {q}")
        lines.append("")

    if work_queue_items:
        lines.append("What Root thinks we should do next:")
        lines.extend(work_queue_items)
        lines.append("")

    if gaps:
        lines.append("Big gaps (why things aren’t done yet):")
        for g in gaps[: config.max_items]:
            lines.append(f"- {_pick_label(g)}")
        lines.append("")

    if top_realities:
        lines.append("What exists in this world:")
        for r in top_realities[: config.max_items]:
            lines.append(_reality_line(r))
        lines.append("")

    lines.append(f"Model: {root_model_path.as_posix()}")
    return "\n".join(lines).strip() + "\n"


def write_human_state(*, config: HumanStateConfig, out_path: Path) -> Path:
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_human_state(config), encoding="utf-8")
    return out_path
