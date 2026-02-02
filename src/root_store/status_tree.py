from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from rich.text import Text
from rich.tree import Tree

from .loader import load_merged_model


@dataclass(frozen=True)
class StatusTreeConfig:
    root_model_path: Path
    root_id: str = "reality-seed"
    max_depth: int = 6
    max_children: int = 200
    show_ids: bool = False
    show_provenance: bool = False
    include_edges: Tuple[str, ...] = ("CONTAINS", "USES", "NEEDS")
    include_orphans: bool = True
    orphans_mode: str = "issues"  # "issues" | "all"


def _safe_str(x: Any) -> str:
    return str(x) if x is not None else ""


def _pick_label(n: Dict[str, Any]) -> str:
    return _safe_str(n.get("label") or n.get("id") or "(unknown)")


def _bucket(status: str) -> str:
    s = (status or "").strip().lower()
    if s in {"pass", "ok", "green"}:
        return "good"
    if s in {"fail", "error", "red"}:
        return "bad"
    if s in {"warn", "warning", "yellow"}:
        return "warning"
    if s in {"planned", "ready", "proposed", "in-progress", "pending", "active", "vision", "ongoing"}:
        return "neutral"
    if s == "":
        return "neutral"
    return "neutral"


def _severity(bucket: str) -> int:
    return {"good": 0, "neutral": 1, "warning": 2, "bad": 3}.get(bucket, 1)


def _style_for(bucket: str) -> Tuple[str, str]:
    if bucket == "good":
        return ("[green]✓[/green]", "green")
    if bucket == "warning":
        return ("[yellow]![/yellow]", "yellow")
    if bucket == "bad":
        return ("[red]✗[/red]", "red")
    return ("[dim]•[/dim]", "dim")


def _node_bucket(n: Dict[str, Any]) -> str:
    # Prefer explicit status.
    st = n.get("status")
    if isinstance(st, str) and st.strip():
        return _bucket(st)

    # Derive from save-exec evidence if present.
    ev = n.get("evidence")
    if isinstance(ev, dict):
        se = ev.get("save_exec")
        if isinstance(se, dict):
            lr = se.get("last_run")
            if isinstance(lr, dict):
                ok = lr.get("ok")
                if ok is True:
                    return "good"
                if ok is False:
                    return "bad"

    return "neutral"


def _format_evidence(n: Dict[str, Any]) -> str:
    ev = n.get("evidence")
    if not isinstance(ev, dict):
        return ""

    parts: List[str] = []

    iq = ev.get("integration_queue")
    if isinstance(iq, dict):
        ls = iq.get("last_save")
        la = iq.get("last_attempt")
        if isinstance(ls, dict) and isinstance(ls.get("at"), str):
            parts.append(f"saved@{ls['at']}")
        elif isinstance(la, dict) and isinstance(la.get("at"), str):
            parts.append(f"attempt@{la['at']}")

    se = ev.get("save_exec")
    if isinstance(se, dict):
        lr = se.get("last_run")
        if isinstance(lr, dict) and isinstance(lr.get("ran_at"), str):
            ok = lr.get("ok")
            stamp = "ok" if ok is True else "fail" if ok is False else "?"
            parts.append(f"save-exec:{stamp}@{lr['ran_at']}")

    return ", ".join(parts)


def _build_edge_map(
    nodes: Dict[str, Dict[str, Any]],
    edges: List[Dict[str, Any]],
    include_edges: Iterable[str],
) -> Dict[str, Dict[str, List[str]]]:
    """Return mapping: from_node_id -> edge_type -> [to_node_id...]."""

    allowed = {e.strip() for e in include_edges if isinstance(e, str) and e.strip()}
    out: Dict[str, Dict[str, List[str]]] = {nid: {} for nid in nodes.keys()}

    for e in edges:
        if not isinstance(e, dict):
            continue
        et = e.get("type")
        if not (isinstance(et, str) and et in allowed):
            continue
        frm = e.get("from")
        to = e.get("to")
        if isinstance(frm, str) and isinstance(to, str) and frm in nodes and to in nodes:
            out.setdefault(frm, {}).setdefault(et, []).append(to)

    # Secondary: node.parent field becomes CONTAINS (only if enabled)
    if "CONTAINS" in allowed:
        linked: Set[Tuple[str, str]] = set()
        for p, buckets in out.items():
            for kids in buckets.values():
                for k in kids:
                    linked.add((p, k))

        for nid, n in nodes.items():
            parent = n.get("parent")
            if isinstance(parent, str) and parent in nodes and (parent, nid) not in linked:
                out.setdefault(parent, {}).setdefault("CONTAINS", []).append(nid)

    def sort_key(cid: str) -> Tuple[str, str]:
        c = nodes.get(cid, {})
        return (_pick_label(c).lower(), cid)

    # Stable order + de-dupe
    for p, buckets in list(out.items()):
        for et, kids in list(buckets.items()):
            buckets[et] = sorted(set(kids), key=sort_key)

    return out


def render_status_tree(config: StatusTreeConfig) -> Tree:
    root_model_path = config.root_model_path.resolve()
    graph = load_merged_model(root_model_path)
    nodes = graph.nodes

    edge_map = _build_edge_map(nodes, graph.edges, config.include_edges)

    # For audit->check expansion in orphan view.
    has_check_map = _build_edge_map(nodes, graph.edges, ("HAS_CHECK",))

    def subtree_severity(node_id: str, visiting: Set[str], memo: Dict[str, int]) -> int:
        if node_id in memo:
            return memo[node_id]
        if node_id in visiting:
            # Cycle: treat as warning.
            memo[node_id] = _severity("warning")
            return memo[node_id]
        visiting.add(node_id)
        n = nodes.get(node_id, {})
        own = _severity(_node_bucket(n if isinstance(n, dict) else {}))
        worst = own
        buckets = edge_map.get(node_id, {})
        for kids in buckets.values():
            for cid in kids:
                worst = max(worst, subtree_severity(cid, visiting, memo))
        visiting.remove(node_id)
        memo[node_id] = worst
        return worst

    memo: Dict[str, int] = {}
    if config.root_id not in nodes:
        title = Text(f"Root id not found: {config.root_id}", style="red")
        return Tree(title)

    # Header node line
    root_node = nodes[config.root_id]
    root_label = _pick_label(root_node)
    derived = subtree_severity(config.root_id, set(), memo)
    derived_bucket = {0: "good", 1: "neutral", 2: "warning", 3: "bad"}.get(derived, "neutral")
    icon, icon_style = _style_for(derived_bucket)

    header = Text.from_markup(f"{icon} {root_label}")
    header.stylize(icon_style)
    tree = Tree(header)

    def add_children(parent_tree: Tree, parent_id: str, depth: int, path: Set[str]) -> None:
        if depth >= config.max_depth:
            return
        if parent_id in path:
            parent_tree.add(Text("(cycle)", style="yellow"))
            return

        path2 = set(path)
        path2.add(parent_id)

        buckets = edge_map.get(parent_id, {})
        # Render edge buckets in a stable, human-friendly order.
        edge_order = ["CONTAINS", "USES", "NEEDS", "IMPLEMENTS", "EMBODIES"]
        ordered = [et for et in edge_order if et in buckets] + [et for et in buckets.keys() if et not in edge_order]

        for et in ordered:
            kids = buckets.get(et, [])
            if not kids:
                continue

            group = parent_tree.add(Text.from_markup(f"[dim]{et}[/dim]"))
            if len(kids) > config.max_children:
                shown = kids[: config.max_children]
                hidden = len(kids) - len(shown)
            else:
                shown = kids
                hidden = 0

            for cid in shown:
                n = nodes.get(cid)
                if not isinstance(n, dict):
                    continue

                derived = memo.get(cid, _severity("neutral"))
                derived_bucket = {0: "good", 1: "neutral", 2: "warning", 3: "bad"}.get(derived, "neutral")
                icon, _ = _style_for(derived_bucket)

                label = _pick_label(n)
                ntype = _safe_str(n.get("type") or "")
                own_status = _safe_str(n.get("status") or "")
                ev = _format_evidence(n)

                pieces: List[str] = [f"{icon} {label}"]
                if ntype:
                    pieces.append(f"[dim]{ntype}[/dim]")
                if own_status:
                    pieces.append(f"status={own_status}")
                if ev:
                    pieces.append(f"[dim]{ev}[/dim]")
                if config.show_ids:
                    pieces.append(f"[dim]id={cid}[/dim]")
                if config.show_provenance:
                    prov = graph.provenance_by_node_id.get(cid)
                    if prov:
                        pieces.append(f"[dim]{prov.file}[/dim]")

                child_tree = group.add(Text.from_markup("  ".join(pieces)))
                add_children(child_tree, cid, depth + 1, path2)

            if hidden:
                group.add(Text.from_markup(f"[dim]… {hidden} more (use --max-children)[/dim]"))

    add_children(tree, config.root_id, 0, set())

    if config.include_orphans:
        # Find nodes reachable from root via configured edges.
        reachable: Set[str] = set()
        queue: List[str] = [config.root_id]
        while queue:
            cur = queue.pop(0)
            if cur in reachable:
                continue
            reachable.add(cur)
            buckets = edge_map.get(cur, {})
            for kids in buckets.values():
                for cid in kids:
                    if cid not in reachable:
                        queue.append(cid)

        # Build orphan groups by type.
        def want_node(n: Dict[str, Any]) -> bool:
            mode = (config.orphans_mode or "issues").strip().lower()
            if mode == "all":
                return True
            # issues-only
            b = _node_bucket(n)
            return b in {"warning", "bad"}

        orphan_types = ["Audit", "Check", "Policy", "Proof"]
        orphan_group = tree.add(Text.from_markup("[dim]ORPHANS (not connected in the selected edge view)[/dim]"))
        any_added = False

        for t in orphan_types:
            candidates: List[str] = []
            for nid, n in nodes.items():
                if nid in reachable:
                    continue
                if not isinstance(n, dict):
                    continue
                if n.get("type") != t:
                    continue
                if not want_node(n):
                    continue
                candidates.append(nid)

            if not candidates:
                continue

            any_added = True
            type_group = orphan_group.add(Text.from_markup(f"[dim]{t}s[/dim]"))
            for nid in sorted(candidates, key=lambda x: (_pick_label(nodes[x]).lower(), x)):
                n = nodes[nid]
                derived_bucket = _node_bucket(n)
                icon, _ = _style_for(derived_bucket)
                label = _pick_label(n)
                own_status = _safe_str(n.get("status") or "")
                ev = _format_evidence(n)

                pieces: List[str] = [f"{icon} {label}"]
                if own_status:
                    pieces.append(f"status={own_status}")
                if ev:
                    pieces.append(f"[dim]{ev}[/dim]")
                if config.show_ids:
                    pieces.append(f"[dim]id={nid}[/dim]")
                if config.show_provenance:
                    prov = graph.provenance_by_node_id.get(nid)
                    if prov:
                        pieces.append(f"[dim]{prov.file}[/dim]")

                audit_tree = type_group.add(Text.from_markup("  ".join(pieces)))

                # Expand checks for audits, regardless of selected edge types.
                if t == "Audit":
                    checks = has_check_map.get(nid, {}).get("HAS_CHECK", [])
                    if checks:
                        cg = audit_tree.add(Text.from_markup("[dim]HAS_CHECK[/dim]"))
                        for cid in checks[: config.max_children]:
                            cn = nodes.get(cid)
                            if not isinstance(cn, dict):
                                continue
                            cb = _node_bucket(cn)
                            cicon, _ = _style_for(cb)
                            clabel = _pick_label(cn)
                            cstatus = _safe_str(cn.get("status") or "")
                            cg.add(Text.from_markup(f"{cicon} {clabel}  [dim]{cn.get('type','')}[/dim]  status={cstatus}"))

        if not any_added:
            orphan_group.add(Text.from_markup("[dim](none)[/dim]"))

    return tree
