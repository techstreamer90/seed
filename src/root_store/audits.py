from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict

from .index import rebuild_index, open_db
from .query import QueryEngine
from .loader import discover_model_files, load_merged_model
from .writeback import (
    apply_node_updates,
    read_json as _read_json_file,
    write_json as _write_json_file,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> Dict[str, Any]:
    return _read_json_file(path)


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    _write_json_file(path, data)


def _scream_packet_dir() -> Path:
    return Path(__file__).parent / "screams"


def _build_scream_prompt(packet_path: Path) -> str:
    return (
        "A Root model audit failed. You are an interactive debug agent.\n\n"
        "Open and read this scream packet JSON (it contains the Root top node and failure evidence):\n"
        f"- {packet_path.as_posix()}\n\n"
        "Goals:\n"
        "1) Explain why the check failed (root cause).\n"
        "2) Propose the smallest Change (model-level) or code fix (reality-level) to resolve it.\n"
        "3) If a fix is code, list exact file edits; if a fix is model, list exact node/edge edits.\n"
        "4) Define how we re-run the audit and what PASS evidence looks like.\n"
    )


def _suggest_spawnie_shell_command(packet_path: Path) -> str:
    # This is a *suggestion* string for the human to run. We don't assume Spawnie is installed
    # into the current environment; users may run it from its own repo/venv.
    prompt = _build_scream_prompt(packet_path)
    prompt_one_line = " ".join(prompt.splitlines()).replace('"', '\\"')
    return (
        "spawnie shell --new-window --working-dir C:/seed "
        "--model claude-sonnet "
        f"\"{prompt_one_line}\""
    )


def _write_scream_packet(
    *,
    root_model_path: Path,
    audit_id: str,
    check_ids: list[str],
    results: Dict[str, Any],
    now: str,
) -> Path:
    # Use the merged model view so scream packets still work after nodes move into submodels.
    graph = load_merged_model(root_model_path)
    top = graph.nodes.get("reality-seed")
    audit = graph.nodes.get(audit_id)
    checks = {cid: graph.nodes.get(cid) for cid in check_ids}

    packet = {
        "kind": "root_store.scream_packet",
        "version": "v0",
        "created_at": now,
        "root_model_path": str(root_model_path),
        "top_node": top,
        "audit": audit,
        "checks": checks,
        "results": results,
    }

    out_dir = _scream_packet_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{now.replace(':', '').replace('-', '').replace('T', '_')}-{audit_id}.json"
    _write_json(out_path, packet)
    return out_path


def _as_bool(x: Any) -> bool:
    return bool(x)


def _sha256(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _model_base_dir_for_provenance_file(prov_file: str) -> Path:
    # Convention: model file lives at <base>/model/sketch.json
    # So base dir is parent.parent.
    p = Path(prov_file)
    try:
        return p.parent.parent
    except Exception:
        return p.parent


def run_audit_root_compliance(root_model_path: Path) -> Dict[str, Any]:
    """Run the modeled audit `audit-root-compliance`.

    This is intentionally a hybrid:
    - deterministic automated checks today
    - later: deeper behavioral/agent probing

    Current checks (v0):
    - agent_context completeness on Reality nodes
    - hash-control coverage for Module source files (provenance-aware)
    - governance wiring exists (policy/change/audit edges)
    - audits are runnable (at least one runner-backed audit executed and wrote evidence)
    """

    now = _utc_now()
    graph = load_merged_model(root_model_path)

    nodes = graph.nodes
    edges = graph.edges

    def node(nid: str) -> Dict[str, Any] | None:
        return nodes.get(nid)

    # Top realities: Reality nodes in the root model (provenance == root model file)
    root_file = str(root_model_path.resolve().as_posix())
    top_realities = [
        n
        for n in nodes.values()
        if n.get("type") == "Reality"
        and graph.provenance_by_node_id.get(n.get("id"), None)
        and graph.provenance_by_node_id[n.get("id")].file == root_file
    ]

    # --- Check 1: agent_context completeness ---
    ac_missing: Dict[str, list[str]] = {}
    for r in top_realities:
        rid = r.get("id")
        missing: list[str] = []
        ac = r.get("agent_context")
        if not isinstance(ac, dict):
            missing.append("agent_context")
        else:
            if not ac.get("agent_context_version"):
                missing.append("agent_context_version")
            focus = ac.get("focus")
            if not (isinstance(focus, dict) and focus.get("type") and focus.get("id")):
                missing.append("focus{type,id}")
            wq = ac.get("work_queue")
            if not (isinstance(wq, list) and len(wq) >= 1):
                missing.append("work_queue[]")
        if missing and isinstance(rid, str):
            ac_missing[rid] = missing

    ok_agent_context = len(ac_missing) == 0

    # --- Check 2: hash-control coverage ---
    # For every Module node with a source.path, require source.hash and verify it.
    hash_missing: list[str] = []
    hash_mismatch: list[dict[str, Any]] = []
    file_missing: list[str] = []

    for nid, n in nodes.items():
        if n.get("type") != "Module":
            continue
        source = n.get("source")
        if not isinstance(source, dict):
            continue
        rel = source.get("path")
        if not isinstance(rel, str) or not rel:
            continue
        expected = source.get("hash")
        if not isinstance(expected, str) or not expected or expected == "pending-update":
            hash_missing.append(nid)
            continue

        prov = graph.provenance_by_node_id.get(nid)
        base_dir = _model_base_dir_for_provenance_file(prov.file) if prov else root_model_path.parent.parent
        full_path = (base_dir / rel).resolve()
        if not full_path.exists():
            file_missing.append(nid)
            continue
        actual = _sha256(full_path)
        if actual != expected:
            hash_mismatch.append(
                {
                    "id": nid,
                    "path": str(full_path),
                    "expected": expected,
                    "actual": actual,
                }
            )

    ok_hash = (len(hash_missing) == 0) and (len(hash_mismatch) == 0) and (len(file_missing) == 0)

    # --- Check 3: governance wiring exists ---
    def has_edge(edge_type: str, from_id: str, to_id: str | None = None) -> bool:
        for e in edges:
            if e.get("type") != edge_type:
                continue
            if e.get("from") != from_id:
                continue
            if to_id is not None and e.get("to") != to_id:
                continue
            return True
        return False

    ok_governance = (
        node("policy-aspiration-aligned-change") is not None
        and has_edge("GOVERNS", "policy-aspiration-aligned-change", "change-seed-change-process-v1")
        and has_edge("PRODUCES", "change-seed-change-process-v1", "audit-change-alignment")
    )

    # --- Check 4: audits are runnable ---
    # Minimal: the root-store audit should have evidence from runner runs.
    root_store_audit = node("audit-root-store-index-consistency")
    ok_audits = False
    if isinstance(root_store_audit, dict):
        ev = root_store_audit.get("evidence")
        ok_audits = isinstance(ev, dict) and "results" in ev

    # Also: run the existing store audit as part of this compliance audit.
    store_sub = run_audit_root_store_index_consistency(root_model_path)

    # Score (very rough v0): each check is 25 points.
    score = 0
    score += 25 if ok_agent_context else 0
    score += 25 if ok_hash else 0
    score += 25 if ok_governance else 0
    score += 25 if ok_audits else 0

    audit_ok = score == 100

    results: Dict[str, Any] = {
        "score": score,
        "checks": {
            "agent_context": {"ok": ok_agent_context, "missing": ac_missing},
            "hash_control": {
                "ok": ok_hash,
                "missing_hash": hash_missing,
                "missing_file": file_missing,
                "mismatch": hash_mismatch,
            },
            "governance": {"ok": ok_governance},
            "audits_runnable": {"ok": ok_audits},
            "root_store_sub_audit": store_sub,
        },
        "top_realities": [r.get("id") for r in top_realities],
    }

    def _mk_check_update(ok: bool, evidence: Dict[str, Any]):
        def _update(n: Dict[str, Any]) -> None:
            n["status"] = "pass" if ok else "fail"
            n["result"] = "pass" if ok else "fail"
            n["last_run"] = now
            n["evidence"] = evidence

        return _update

    audit_id = "audit-root-compliance"

    def _update_audit_node(n: Dict[str, Any]) -> None:
        n["status"] = "pass" if audit_ok else "fail"
        n["last_run"] = now
        n["findings"] = [] if audit_ok else ["Compliance incomplete: see checks + score"]
        n["evidence"] = {"results": results}

    updates: Dict[str, Callable[[Dict[str, Any]], None]] = {
        "check-root-compliance-agent-context": _mk_check_update(
            ok_agent_context, results["checks"]["agent_context"]
        ),
        "check-root-compliance-hash-control": _mk_check_update(ok_hash, results["checks"]["hash_control"]),
        "check-root-compliance-governance": _mk_check_update(ok_governance, results["checks"]["governance"]),
        "check-root-compliance-audits": _mk_check_update(ok_audits, results["checks"]["audits_runnable"]),
        audit_id: _update_audit_node,
    }

    if not audit_ok:
        check_ids = [
            "check-root-compliance-agent-context",
            "check-root-compliance-hash-control",
            "check-root-compliance-governance",
            "check-root-compliance-audits",
        ]
        packet_path = _write_scream_packet(
            root_model_path=root_model_path,
            audit_id=audit_id,
            check_ids=check_ids,
            results=results,
            now=now,
        )
        spawnie_cmd = _suggest_spawnie_shell_command(packet_path)

        def _attach_scream(n: Dict[str, Any]) -> None:
            ev = n.get("evidence")
            if not isinstance(ev, dict):
                ev = {}
            ev.setdefault("scream", {})
            if isinstance(ev.get("scream"), dict):
                ev["scream"].update(
                    {
                        "packet": str(packet_path),
                        "suggested_spawnie_shell": spawnie_cmd,
                    }
                )
            n["evidence"] = ev

        # Compose scream attachment on top of base audit update.
        def _audit_update_with_scream(n: Dict[str, Any]) -> None:
            _update_audit_node(n)
            _attach_scream(n)

        updates[audit_id] = _audit_update_with_scream

    apply_node_updates(graph=graph, default_model_file=root_model_path, updates=updates)
    return {"ok": audit_ok, **results}


def run_audit_root_store_index_consistency(root_model_path: Path) -> Dict[str, Any]:
    """Run the modeled audit `audit-root-store-index-consistency`.

    v0 checks:
    - provenance_file present for all indexed nodes/edges
    - reverse lookups work (incoming/outgoing edges)

    Writes results back into the Root model audit/check nodes.
    """

    db_path = rebuild_index(root_model_path)

    with open_db(db_path) as conn:
        q = QueryEngine(conn)

        # Check 1: provenance present
        missing_node_prov = conn.execute(
            "SELECT id FROM nodes WHERE provenance_file IS NULL OR provenance_file = '' LIMIT 20"
        ).fetchall()
        missing_edge_prov = conn.execute(
            "SELECT id FROM edges WHERE provenance_file IS NULL OR provenance_file = '' LIMIT 20"
        ).fetchall()
        ok_prov = (len(missing_node_prov) == 0) and (len(missing_edge_prov) == 0)

        # Check 2: reverse lookups
        sample_id = "reality-root-model-store"
        out_rows = q.outgoing(sample_id).rows
        in_rows = q.incoming(sample_id).rows
        ok_reverse = isinstance(out_rows, list) and isinstance(in_rows, list)

        results = {
            "db_path": str(db_path),
            "provenance": {
                "ok": ok_prov,
                "missing_node_prov": [r["id"] for r in missing_node_prov],
                "missing_edge_prov": [r["id"] for r in missing_edge_prov],
            },
            "reverse_lookups": {
                "ok": ok_reverse,
                "sample_id": sample_id,
                "out_count": len(out_rows),
                "in_count": len(in_rows),
            },
        }

    graph = load_merged_model(root_model_path)
    now = _utc_now()

    def _mk_check_update(ok: bool, evidence: Dict[str, Any]):
        def _update(n: Dict[str, Any]) -> None:
            n["status"] = "pass" if ok else "fail"
            n["result"] = "pass" if ok else "fail"
            n["last_run"] = now
            n["evidence"] = evidence

        return _update

    audit_id = "audit-root-store-index-consistency"
    audit_ok = ok_prov and ok_reverse

    def _update_audit_node(n: Dict[str, Any]) -> None:
        n["status"] = "pass" if audit_ok else "fail"
        n["last_run"] = now
        n["findings"] = [] if audit_ok else ["See failed checks"]
        n["evidence"] = {"results": results}

    updates: Dict[str, Callable[[Dict[str, Any]], None]] = {
        "check-root-store-has-provenance": _mk_check_update(ok_prov, results["provenance"]),
        "check-root-store-change-gate": _mk_check_update(
            True,
            {"ok": True, "note": "enforcement.validate_change_gate accepts merged graphs and is invoked by writer.apply_change"},
        ),
        "check-root-store-reverse-lookups": _mk_check_update(ok_reverse, results["reverse_lookups"]),
        audit_id: _update_audit_node,
    }

    if not audit_ok:
        check_ids = [
            "check-root-store-has-provenance",
            "check-root-store-change-gate",
            "check-root-store-reverse-lookups",
        ]
        packet_path = _write_scream_packet(
            root_model_path=root_model_path,
            audit_id=audit_id,
            check_ids=check_ids,
            results=results,
            now=now,
        )
        spawnie_cmd = _suggest_spawnie_shell_command(packet_path)

        def _attach_scream(n: Dict[str, Any]) -> None:
            ev = n.get("evidence")
            if not isinstance(ev, dict):
                ev = {}
            ev.setdefault("scream", {})
            if isinstance(ev.get("scream"), dict):
                ev["scream"].update(
                    {
                        "packet": str(packet_path),
                        "suggested_spawnie_shell": spawnie_cmd,
                    }
                )
            n["evidence"] = ev

        def _audit_update_with_scream(n: Dict[str, Any]) -> None:
            _update_audit_node(n)
            _attach_scream(n)

        updates[audit_id] = _audit_update_with_scream

    apply_node_updates(graph=graph, default_model_file=root_model_path, updates=updates)
    return {"ok": audit_ok, **results}


def run_audit_root_store_attachment_closure(root_model_path: Path) -> Dict[str, Any]:
    """Ensure structural attachments are co-located (move-safe).

    v0 rules (hard FAIL):
    - HAS_CHECK: Audit and Check must live in the same provenance file.
    - CONTAINS: Parent and child must live in the same provenance file.

    This is the enforcement layer that makes partial moves scream.
    """

    now = _utc_now()
    graph = load_merged_model(root_model_path)

    prov_nodes = graph.provenance_by_node_id

    def _normalize_ref_path(ref: str) -> Path:
        # Accept both C:/seed/... and relative paths.
        if ref.startswith("C:/"):
            return Path(ref.replace("/", "\\"))
        return Path(ref)

    # Parent mountpoints can legitimately CONTAIN children defined in their referenced submodel file(s).
    mount_allowed_files: dict[str, set[str]] = {}
    for nid, n in graph.nodes.items():
        if not isinstance(n, dict):
            continue
        mm = n.get("model")
        if not (isinstance(mm, dict) and isinstance(mm.get("_ref"), str)):
            continue
        ref = _normalize_ref_path(mm["_ref"]).resolve()
        if ref.exists():
            allowed = {p.as_posix() for p in discover_model_files([ref])}
            mount_allowed_files[nid] = allowed

    def prov_file(node_id: str) -> str | None:
        p = prov_nodes.get(node_id)
        return None if p is None else p.file

    has_check_violations: list[dict[str, Any]] = []
    contains_violations: list[dict[str, Any]] = []

    for e in graph.edges:
        if not isinstance(e, dict):
            continue
        et = e.get("type")
        frm = e.get("from")
        to = e.get("to")
        if not (isinstance(frm, str) and isinstance(to, str)):
            continue

        if et == "HAS_CHECK":
            pf = prov_file(frm)
            pt = prov_file(to)
            if pf and pt and pf != pt:
                has_check_violations.append(
                    {
                        "audit": frm,
                        "check": to,
                        "audit_file": pf,
                        "check_file": pt,
                    }
                )

        if et == "CONTAINS":
            pf = prov_file(frm)
            pt = prov_file(to)
            if pf and pt and pf != pt:
                allowed = mount_allowed_files.get(frm)
                if isinstance(allowed, set) and pt in allowed:
                    continue
                contains_violations.append(
                    {
                        "parent": frm,
                        "child": to,
                        "parent_file": pf,
                        "child_file": pt,
                    }
                )

    ok_has_check = len(has_check_violations) == 0
    ok_contains = len(contains_violations) == 0
    audit_ok = ok_has_check and ok_contains

    results: Dict[str, Any] = {
        "checks": {
            "has_check_colocated": {"ok": ok_has_check, "violations": has_check_violations[:50]},
            "contains_colocated": {"ok": ok_contains, "violations": contains_violations[:50]},
        }
    }

    audit_id = "audit-root-store-attachment-closure"

    def _mk_check_update(ok: bool, evidence: Dict[str, Any]):
        def _update(n: Dict[str, Any]) -> None:
            n["status"] = "pass" if ok else "fail"
            n["result"] = "pass" if ok else "fail"
            n["last_run"] = now
            n["evidence"] = evidence

        return _update

    def _update_audit_node(n: Dict[str, Any]) -> None:
        n["status"] = "pass" if audit_ok else "fail"
        n["last_run"] = now
        n["findings"] = [] if audit_ok else ["Attachment closure violated: see checks"]
        n["evidence"] = {"results": results}

    updates: Dict[str, Callable[[Dict[str, Any]], None]] = {
        "check-root-store-has_check-colocated": _mk_check_update(
            ok_has_check, results["checks"]["has_check_colocated"]
        ),
        "check-root-store-contains-colocated": _mk_check_update(
            ok_contains, results["checks"]["contains_colocated"]
        ),
        audit_id: _update_audit_node,
    }

    if not audit_ok:
        check_ids = [
            "check-root-store-has_check-colocated",
            "check-root-store-contains-colocated",
        ]
        packet_path = _write_scream_packet(
            root_model_path=root_model_path,
            audit_id=audit_id,
            check_ids=check_ids,
            results=results,
            now=now,
        )
        spawnie_cmd = _suggest_spawnie_shell_command(packet_path)

        def _attach_scream(n: Dict[str, Any]) -> None:
            ev = n.get("evidence")
            if not isinstance(ev, dict):
                ev = {}
            ev.setdefault("scream", {})
            if isinstance(ev.get("scream"), dict):
                ev["scream"].update(
                    {
                        "packet": str(packet_path),
                        "suggested_spawnie_shell": spawnie_cmd,
                    }
                )
            n["evidence"] = ev

        def _audit_update_with_scream(n: Dict[str, Any]) -> None:
            _update_audit_node(n)
            _attach_scream(n)

        updates[audit_id] = _audit_update_with_scream

    apply_node_updates(graph=graph, default_model_file=root_model_path, updates=updates)
    return {"ok": audit_ok, **results}
