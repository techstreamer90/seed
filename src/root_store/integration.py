from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .audits import run_audit_root_store_attachment_closure, run_audit_root_store_index_consistency
from .delete import compute_delete_closure, resolve_source_paths, delete_nodes, DeleteResult
from .loader import load_merged_model
from .writeback import apply_node_updates


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _git_info(repo_dir: Path) -> Dict[str, Any]:
    """Best-effort git context capture.

    If this isn't a git repo or git isn't installed, returns empty fields.
    """

    repo_dir = repo_dir.resolve()

    def run(args: List[str]) -> str | None:
        try:
            p = subprocess.run(
                args,
                cwd=str(repo_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            if p.returncode != 0:
                return None
            return (p.stdout or "").strip()
        except Exception:
            return None

    inside = run(["git", "rev-parse", "--is-inside-work-tree"])
    if inside != "true":
        return {
            "is_repo": False,
            "branch": None,
            "dirty": None,
            "head": None,
            "upstream": None,
            "ahead": None,
            "behind": None,
        }

    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    head = run(["git", "rev-parse", "HEAD"])
    status = run(["git", "status", "--porcelain"])
    dirty = None if status is None else (len(status.strip()) > 0)

    upstream = run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    ahead = None
    behind = None
    if upstream:
        counts = run(["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"])
        if counts and "\t" in counts:
            left, right = counts.split("\t", 1)
            try:
                ahead = int(left)
                behind = int(right)
            except Exception:
                ahead = None
                behind = None

    return {
        "is_repo": True,
        "branch": branch,
        "dirty": dirty,
        "head": head,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
    }


def _maybe_git_fetch(*, repo_dir: Path, enabled: bool) -> bool:
    if not enabled:
        return False
    try:
        p = subprocess.run(
            ["git", "fetch", "--prune"],
            cwd=str(repo_dir.resolve()),
            capture_output=True,
            text=True,
            check=False,
        )
        return p.returncode == 0
    except Exception:
        return False


def _neighbors(*, graph: Any, node_id: str, radius: int = 1, max_nodes: int = 25) -> Dict[str, Any]:
    """Lightweight local neighborhood summary.

    Used to force a "surrounding area" evaluation before save without needing a full query layer.
    """

    radius = max(0, int(radius))
    out_nodes: List[str] = []
    out_edges: List[Dict[str, Any]] = []

    frontier: List[str] = [node_id]
    seen: set[str] = set()

    for _ in range(radius + 1):
        if not frontier:
            break
        next_frontier: List[str] = []
        for cur in frontier:
            if cur in seen:
                continue
            seen.add(cur)
            out_nodes.append(cur)
            if len(out_nodes) >= max_nodes:
                break

            for e in getattr(graph, "edges", []):
                if not isinstance(e, dict):
                    continue
                frm = e.get("from")
                to = e.get("to")
                if frm == cur and isinstance(to, str):
                    out_edges.append({"type": e.get("type"), "from": frm, "to": to})
                    next_frontier.append(to)
                elif to == cur and isinstance(frm, str):
                    out_edges.append({"type": e.get("type"), "from": frm, "to": to})
                    next_frontier.append(frm)

        frontier = next_frontier
        if len(out_nodes) >= max_nodes:
            break

    # De-dupe edges while preserving order.
    uniq: set[tuple[str, str, str]] = set()
    edges2: List[Dict[str, Any]] = []
    for e in out_edges:
        t = (str(e.get("type")), str(e.get("from")), str(e.get("to")))
        if t in uniq:
            continue
        uniq.add(t)
        edges2.append(e)

    return {
        "radius": radius,
        "node_ids": out_nodes,
        "edge_count": len(edges2),
        "edges": edges2[:100],
        "truncated": len(out_nodes) >= max_nodes or len(edges2) > 100,
    }


def _find_parent_id(graph: Any, node_id: str) -> str | None:
    n = graph.nodes.get(node_id)
    if isinstance(n, dict) and isinstance(n.get("parent"), str):
        return n["parent"]

    # Otherwise infer from CONTAINS edges.
    for e in graph.edges:
        if not isinstance(e, dict):
            continue
        if e.get("type") != "CONTAINS":
            continue
        if e.get("to") != node_id:
            continue
        frm = e.get("from")
        return frm if isinstance(frm, str) else None

    return None


def parent_chain(graph: Any, node_id: str) -> List[str]:
    """Return [node_id, parent, grandparent, ...] until root."""

    out: List[str] = []
    seen: set[str] = set()
    cur: Optional[str] = node_id
    while isinstance(cur, str) and cur and cur not in seen:
        seen.add(cur)
        out.append(cur)
        cur = _find_parent_id(graph, cur)
    return out


@dataclass(frozen=True)
class SaveResult:
    node_id: str
    chain: List[str]
    audits: Dict[str, Any]
    ok: bool
    preflight: Dict[str, Any]


def verbal_save(
    *,
    root_model_path: Path,
    node_id: str,
    propagate: bool = True,
    run_rough_checks: bool = True,
    require_git_clean: bool = True,
    require_up_to_date: bool = True,
    fetch_remotes: bool = False,
    neighbor_radius: int = 1,
) -> SaveResult:
    """"Let's save" implementation.

    Semantics:
    - captures contextual info (git branch if available)
    - optionally runs rough checks (attachment-closure + store index consistency)
    - writes a structured evidence blob onto the node (and optionally its parents)

    This is intentionally simple and safe: it never mutates structure, only evidence.
    """

    root_model_path = root_model_path.resolve()
    repo_dir = root_model_path.parent.parent

    # 1) Optional refresh for more accurate upstream checks.
    _maybe_git_fetch(repo_dir=repo_dir, enabled=fetch_remotes)

    # 2) Run rough checks first (these write evidence to modeled audit/check nodes).
    audits: Dict[str, Any] = {}
    if run_rough_checks:
        audits["attachment_closure"] = run_audit_root_store_attachment_closure(root_model_path)
        audits["root_store_index"] = run_audit_root_store_index_consistency(root_model_path)

    # 3) Reload graph for up-to-date provenance mapping.
    graph = load_merged_model(root_model_path)
    chain = parent_chain(graph, node_id)
    if not propagate and chain:
        chain = [chain[0]]

    now = _utc_now()
    git = _git_info(repo_dir)
    surrounding = _neighbors(graph=graph, node_id=node_id, radius=neighbor_radius)

    warnings: List[str] = []
    recommendations: List[str] = []
    if git.get("is_repo") is True:
        if require_git_clean and git.get("dirty") is True:
            warnings.append("git working tree is dirty")
            recommendations.append("If reality sources matter for this node, commit/stash changes before verification")
        upstream = git.get("upstream")
        behind = git.get("behind")
        if require_up_to_date:
            if isinstance(upstream, str) and upstream:
                if isinstance(behind, int) and behind > 0:
                    warnings.append(f"git branch behind upstream by {behind} commit(s)")
                    recommendations.append("Pull latest reality before running verification")
                elif behind is None:
                    recommendations.append("Unable to compute ahead/behind; run with --fetch for a fresher upstream check")
            else:
                recommendations.append("No upstream configured; cannot assert branch is up-to-date")
    else:
        # If we're not in a git repo, we cannot assert freshness; don't block.
        recommendations.append("No git repo detected for root model; freshness checks skipped")

    ok = True
    for a in audits.values():
        if isinstance(a, dict) and a.get("ok") is False:
            ok = False

    # Model is the truth: preflight is advisory. Save ok is governed by audits only.
    preflight_ok = True

    payload = {
        "saved_at": now,
        "node_id": node_id,
        "propagated": propagate,
        "ok": ok,
        "git": git,
        "preflight": {
            "ok": preflight_ok,
            "require_git_clean": require_git_clean,
            "require_up_to_date": require_up_to_date,
            "fetch_remotes": fetch_remotes,
            "warnings": warnings,
            "recommendations": recommendations,
            "surrounding": surrounding,
        },
        "rough_checks": {
            k: {"ok": v.get("ok")} if isinstance(v, dict) else {"ok": None}
            for k, v in audits.items()
        },
        "chain": chain,
    }

    def mk_update(current_id: str) -> Any:
        def _u(n: Dict[str, Any]) -> None:
            ev = n.get("evidence")
            if not isinstance(ev, dict):
                ev = {}
            iq = ev.get("integration_queue")
            if not isinstance(iq, dict):
                iq = {}
            # Always record the attempt and the save; verification is handled elsewhere.
            iq["last_attempt"] = payload
            iq["last_save"] = payload

            iq.update(
                {
                    "self": current_id,
                    "received_from": None if current_id == node_id else node_id,
                    "handoff_to": None,
                }
            )
            # Model the "turtles" handoff chain.
            idx = chain.index(current_id) if current_id in chain else -1
            if idx != -1 and idx + 1 < len(chain):
                iq["handoff_to"] = chain[idx + 1]
            ev["integration_queue"] = iq
            n["evidence"] = ev

        return _u

    updates = {cid: mk_update(cid) for cid in chain}
    apply_node_updates(graph=graph, default_model_file=root_model_path, updates=updates)

    return SaveResult(node_id=node_id, chain=chain, audits=audits, ok=ok, preflight=payload.get("preflight", {}))


def verbal_delete(
    *,
    root_model_path: Path,
    node_id: str,
    delete_source_files: bool = True,
    dry_run: bool = False,
    run_audits: bool = True,
) -> DeleteResult:
    """"Let's delete" implementation.

    The counterpart to verbal_save - removes a node and all its descendants
    from the model, and optionally deletes corresponding source files.

    Semantics:
    - Computes deletion closure (CONTAINS descendants + HAS_CHECK attachments)
    - Removes nodes and edges from model files
    - Deletes source files/folders from disk (unless disabled)
    - Optionally runs audits to verify consistency

    Args:
        root_model_path: Path to the root model file
        node_id: The node to delete (will include all descendants)
        delete_source_files: Whether to delete source files/folders (default: True)
        dry_run: If True, compute what would be deleted but don't actually delete
        run_audits: Whether to run consistency audits after deletion

    Returns:
        DeleteResult with summary of the operation
    """

    root_model_path = root_model_path.resolve()

    # Perform the deletion
    result = delete_nodes(
        root_model_path=root_model_path,
        seed_node_ids=[node_id],
        delete_source_files=delete_source_files,
        dry_run=dry_run,
    )

    # Run audits after deletion (unless dry run or disabled)
    if not dry_run and run_audits and result.ok:
        try:
            run_audit_root_store_attachment_closure(root_model_path)
            run_audit_root_store_index_consistency(root_model_path)
        except Exception:
            # Audits are advisory - don't fail the delete
            pass

    return result
