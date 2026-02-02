"""
Seed Core CLI - Meta-model reality tracker.
"""

import sys
import json
from pathlib import Path
import threading

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.tree import Tree

from .registry import RealityRegistry
from .verification import verify_all_realities


console = Console()


def _default_root_model_path() -> Path:
    # Typical layout: <seed>/model/sketch.json
    cwd = Path.cwd()
    candidate = cwd / "model" / "sketch.json"
    if candidate.exists():
        return candidate
    # Fallback to common absolute path.
    return Path("C:/seed/model/sketch.json")


def _human_state(root_model_path: Path) -> str:
    # Root store is a sibling package in this repo.
    from root_store.translate import HumanStateConfig, render_human_state

    return render_human_state(HumanStateConfig(root_model_path=root_model_path))


def _assess_and_write_human_state(*, root_model_path: Path, out_path: Path | None = None) -> dict:
    from root_store.audits import run_audit_root_compliance, run_audit_root_store_index_consistency
    from root_store.translate import HumanStateConfig, write_human_state

    root_model_path = root_model_path.resolve()

    # Reassess (writes evidence back into model)
    store = run_audit_root_store_index_consistency(root_model_path)
    compliance = run_audit_root_compliance(root_model_path)

    # Write a human-readable snapshot
    if out_path is None:
        out_path = root_model_path.parent.parent / "output" / "root_state.txt"
    write_human_state(config=HumanStateConfig(root_model_path=root_model_path), out_path=out_path)

    return {"store": store, "compliance": compliance, "human_state": str(out_path)}


def get_registry():
    try:
        return RealityRegistry()
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}", file=sys.stderr)
        sys.exit(1)


@click.group()
@click.version_option(version="0.1.0", prog_name="seed-core")
def cli():
    """Seed Core - Meta-model reality tracker.

    A CLI tool for monitoring and managing multiple interconnected
    projects (realities) through a unified meta-model.

    Common workflows:
      seed-core status              # Quick overview of all realities
      seed-core pulse               # Health check all realities
      seed-core reality check Foo   # Inspect specific reality
      seed-core verify              # Detect drift from model
    """


@cli.command()
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.option("-v", "--verbose", is_flag=True, help="Show detailed information")
def status(json_output, verbose):
    """Show overall status of all realities.

    Examples:
      seed-core status                  # Show basic status table
      seed-core status --verbose        # Show detailed info with paths
      seed-core status --json           # Get JSON output
    """
    registry = get_registry()
    realities = registry.list_all()

    if json_output:
        output = {
            "total": len(realities),
            "realities": [
                {
                    "id": r.id,
                    "label": r.label,
                    "description": r.description,
                    "status": r.status,
                    "path": r.path,
                    "has_model": r.has_model,
                    "model_path": str(r.full_model_path) if r.full_model_path else None,
                }
                for r in realities
            ]
        }
        console.print_json(data=output)
        return

    table = Table(title="Seed Meta-Model Status", box=box.ROUNDED)
    table.add_column("Reality", style="cyan bold")
    table.add_column("Status", style="yellow")
    table.add_column("Model", style="green")

    if verbose:
        table.add_column("Path", style="blue")
        table.add_column("Description", style="dim")

    for reality in realities:
        status_text = reality.status or "active"
        
        if reality.has_model:
            model_text = "[green]+ present[/green]"
        elif reality.model_path:
            model_text = "[red]x missing[/red]"
        else:
            model_text = "[dim]- none[/dim]"

        row = [reality.label, status_text, model_text]
        
        if verbose:
            row.append(reality.path or "-")
            desc = reality.description
            row.append(desc[:50] + "..." if len(desc) > 50 else desc)

        table.add_row(*row)

    console.print(table)
    console.print(f"\n[dim]Total realities: {len(realities)}[/dim]")


@cli.command()
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def pulse(json_output):
    """Run health check on all realities.

    Performs comprehensive health checks including:
    - Path verification
    - Model file existence and readability
    - Overall health status

    Examples:
      seed-core pulse                   # Run pulse check with table output
      seed-core pulse --json            # Get JSON output
    """
    registry = get_registry()
    realities = registry.list_all()

    results = {}
    total_ok = 0
    total_issues = 0

    for reality in realities:
        checks = {
            'has_path': reality.path is not None,
            'has_model': reality.has_model,
            'model_readable': False,
        }

        if reality.has_model:
            try:
                with open(reality.full_model_path, 'r', encoding='utf-8') as f:
                    json.load(f)
                checks['model_readable'] = True
            except Exception:
                checks['model_readable'] = False

        issues = sum(1 for v in checks.values() if v is False)
        if issues == 0:
            total_ok += 1
        else:
            total_issues += 1

        results[reality.id] = {
            'label': reality.label,
            'checks': checks,
            'health': 'ok' if issues == 0 else 'issues'
        }

    if json_output:
        output = {
            'summary': {
                'total': len(realities),
                'ok': total_ok,
                'issues': total_issues
            },
            'results': results
        }
        console.print_json(data=output)
        return

    console.print(Panel.fit(
        f"[bold]Pulse Check Results[/bold]\n\n"
        f"Total: {len(realities)}\n"
        f"[green]OK: {total_ok}[/green]\n"
        f"[red]Issues: {total_issues}[/red]",
        border_style="green" if total_issues == 0 else "yellow"
    ))

    table = Table(box=box.SIMPLE)
    table.add_column("Reality", style="cyan")
    table.add_column("Path", style="blue")
    table.add_column("Model", style="green")
    table.add_column("Health", style="yellow")

    for reality_id, result in results.items():
        checks = result['checks']
        label = result['label']
        health = result['health']

        path_status = "+" if checks['has_path'] else "x"
        model_status = "+" if checks['has_model'] and checks['model_readable'] else "x"
        health_display = "[green]OK[/green]" if health == 'ok' else "[yellow]Issues[/yellow]"

        table.add_row(label, path_status, model_status, health_display)

    console.print("\n", table)


@cli.command()
@click.option("--root-model", "root_model", type=click.Path(exists=True), help="Path to Root model sketch.json")
@click.option("--write", "write_path", type=click.Path(), help="Write the snapshot to a file")
def describe(root_model, write_path):
    """Describe the system in plain human language.

    This is a translation layer: it reads the model and prints a short,
    plain-English snapshot of what's going on.
    """

    root_model_path = Path(root_model) if root_model else _default_root_model_path()
    text = _human_state(root_model_path)

    if write_path:
        out = Path(write_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        console.print(f"[green]Wrote[/green] {out}")
    console.print(Panel(text, title="Root", border_style="cyan"))


@cli.command(name="status-tree")
@click.option("--root-model", "root_model", type=click.Path(exists=True), help="Path to Root model sketch.json")
@click.option("--root-id", default="reality-seed", show_default=True, help="Node id to render as tree root")
@click.option("--max-depth", default=6, show_default=True, type=int, help="Max depth to render")
@click.option("--max-children", default=200, show_default=True, type=int, help="Max children per node")
@click.option(
    "--edges",
    default="CONTAINS,USES,NEEDS",
    show_default=True,
    help="Comma-separated edge types to expand in the tree",
)
@click.option("--include-orphans/--no-include-orphans", default=True, show_default=True, help="Show status nodes not connected in the selected edge view")
@click.option(
    "--orphans",
    type=click.Choice(["issues", "all"], case_sensitive=False),
    default="issues",
    show_default=True,
    help="Which orphan nodes to show",
)
@click.option("--show-ids", is_flag=True, help="Show node ids")
@click.option("--show-provenance", is_flag=True, help="Show which model file defined each node")
def status_tree_cmd(root_model, root_id, max_depth, max_children, edges, include_orphans, orphans, show_ids, show_provenance):
    """Show hierarchical status of model nodes.

    This renders the model as a CONTAINS/parent tree and annotates nodes with
    status + key evidence (e.g. save timestamps).
    """

    from root_store.status_tree import StatusTreeConfig, render_status_tree

    root_model_path = Path(root_model) if root_model else _default_root_model_path()
    include_edges = tuple(e.strip() for e in str(edges).split(",") if e.strip())

    tree: Tree = render_status_tree(
        StatusTreeConfig(
            root_model_path=root_model_path,
            root_id=root_id,
            max_depth=max_depth,
            max_children=max_children,
            show_ids=show_ids,
            show_provenance=show_provenance,
            include_edges=include_edges,
            include_orphans=include_orphans,
            orphans_mode=str(orphans).lower(),
        )
    )
    console.print(tree)


@cli.command()
@click.option("--root-model", "root_model", type=click.Path(exists=True), help="Path to Root model sketch.json")
@click.option("--poll", default=1.0, type=float, help="Polling interval in seconds")
@click.option("--write", "write_path", type=click.Path(), help="Write the snapshot to a file (default: output/root_state.txt)")
def watch(root_model, poll, write_path):
    """Watch input model files and continuously reassess impacts.

    When a model file changes, a background assessment runs:
    - rebuild/index consistency
    - root compliance
    - write a human-readable snapshot
    """

    from root_store.watch import WatchConfig, run_watch_loop

    root_model_path = Path(root_model) if root_model else _default_root_model_path()
    out_path = Path(write_path) if write_path else None

    lock = threading.Lock()
    running = {"active": False, "pending": False}

    def do_assess() -> None:
        with lock:
            if running["active"]:
                running["pending"] = True
                return
            running["active"] = True
            running["pending"] = False

        def _run() -> None:
            try:
                res = _assess_and_write_human_state(root_model_path=root_model_path, out_path=out_path)
                text = _human_state(root_model_path)
                console.print(Panel(text, title="Root (updated)", border_style="cyan"))
                console.print(f"[dim]Snapshot:[/dim] {res['human_state']}")
            except Exception as e:
                console.print(f"[red]Assessment failed:[/red] {e}")
            finally:
                with lock:
                    running["active"] = False
                    pending = running["pending"]
                    running["pending"] = False
                if pending:
                    do_assess()

        threading.Thread(target=_run, daemon=True).start()

    console.print(f"[cyan]Watching[/cyan] {root_model_path} (poll={poll}s)")
    run_watch_loop(WatchConfig(root_model_path=root_model_path, poll_seconds=poll), do_assess)


@cli.command()
@click.argument("node_id")
@click.option("--root-model", "root_model", type=click.Path(exists=True), help="Path to Root model sketch.json")
@click.option("--no-propagate", is_flag=True, help="Only save the node itself, not its parents")
@click.option("--no-checks", is_flag=True, help="Skip rough checks (audits) during save")
@click.option("--no-preflight", is_flag=True, help="Skip git/neighborhood preflight (not recommended)")
@click.option("--no-git-clean", is_flag=True, help="Do not require a clean git working tree")
@click.option("--no-up-to-date", is_flag=True, help="Do not require branch to be up-to-date with upstream")
@click.option("--fetch", "fetch_remotes", is_flag=True, help="Fetch remotes before checking upstream status")
@click.option("--radius", default=1, type=int, show_default=True, help="Neighborhood radius to evaluate around the node")
@click.option("--write", "write_path", type=click.Path(), help="Write the updated human snapshot to a file")
def save(node_id, root_model, no_propagate, no_checks, no_preflight, no_git_clean, no_up_to_date, fetch_remotes, radius, write_path):
    """Verbal save: enqueue integration for the current node.

    This is the command behind the conversational cue "let's save".

    It:
    - captures context (best-effort git branch)
    - runs rough checks (store audits) unless disabled
    - writes structured evidence onto the node and propagates to parents
    """

    from root_store.integration import verbal_save
    from root_store.translate import HumanStateConfig, write_human_state

    root_model_path = Path(root_model) if root_model else _default_root_model_path()
    res = verbal_save(
        root_model_path=root_model_path,
        node_id=node_id,
        propagate=(not no_propagate),
        run_rough_checks=(not no_checks),
        require_git_clean=(not no_git_clean) if (not no_preflight) else False,
        require_up_to_date=(not no_up_to_date) if (not no_preflight) else False,
        fetch_remotes=fetch_remotes if (not no_preflight) else False,
        neighbor_radius=0 if no_preflight else radius,
    )

    pf = res.preflight or {}
    warnings = pf.get("warnings") if isinstance(pf.get("warnings"), list) else []
    warnings_text = ""
    if warnings:
        warnings_text = f"\nPreflight warnings: {len(warnings)} (e.g., {warnings[0]})"

    console.print(
        Panel.fit(
            f"[bold]{'Saved' if res.ok else 'Save Attempt'}[/bold] {res.node_id}\n"
            f"Chain: {' -> '.join(res.chain)}\n"
            f"Preflight: {'ok' if pf else 'skipped'}{warnings_text}\n"
            f"Rough checks: {', '.join(res.audits.keys()) if res.audits else 'skipped'}",
            border_style="green" if res.ok else "yellow",
        )
    )

    if write_path:
        out = Path(write_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        write_human_state(config=HumanStateConfig(root_model_path=root_model_path), out_path=out)
        console.print(f"[green]Wrote[/green] {out}")


@cli.command(name="save-exec")
@click.argument("node_id")
@click.option("--root-model", "root_model", type=click.Path(exists=True), help="Path to Root model sketch.json")
@click.option("--stop-on-error/--continue-on-error", default=True, show_default=True, help="Stop on first failing save action")
@click.option("--no-fallback", is_flag=True, help="If node has no save definition, do not fall back to seed-core save")
def save_exec_cmd(node_id, root_model, stop_on_error, no_fallback):
    """Execute node-defined save behavior (model-driven).

    This is intended to be called by Spawnie workflows.
    """

    from root_store.save_exec import save_exec
    from root_store.integration import verbal_save

    root_model_path = Path(root_model) if root_model else _default_root_model_path()
    res = save_exec(root_model_path=root_model_path, node_id=node_id, stop_on_error=stop_on_error)

    # If the node didn't define save actions, fall back to a minimal model-first save evidence stamp.
    if res.used_fallback and not no_fallback:
        verbal_save(root_model_path=root_model_path, node_id=node_id, propagate=True, run_rough_checks=False)

    failures = [r for r in res.results if not r.ok]
    summary = f"[bold]{'OK' if res.ok else 'FAILED'}[/bold] save-exec {res.node_id}\n"
    summary += f"Used fallback: {res.used_fallback}\n"
    summary += f"Actions run: {len(res.results)}\n"
    if failures:
        summary += f"First failure: action[{failures[0].action_index}]"

    console.print(Panel.fit(summary.strip(), border_style="green" if res.ok else "red"))


@cli.command()
@click.argument("node_id")
@click.option("--root-model", "root_model", type=click.Path(exists=True), help="Path to Root model sketch.json")
@click.option("--dry-run", is_flag=True, help="Show what would be deleted without actually deleting")
@click.option("--no-source-files", is_flag=True, help="Only remove from model, keep source files on disk")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def delete(node_id, root_model, dry_run, no_source_files, force, json_output):
    """Delete a node and all its descendants (turtles all the way down).

    This is the "delete button" - the counterpart to the "save button".
    It removes a node from the model AND deletes the corresponding source
    files/folders, keeping model and reality in sync.

    Deletion is recursive:
    - Deleting a Reality/Subsystem deletes all CONTAINS descendants
    - Deleting an Audit deletes its Checks (HAS_CHECK bidirectional)
    - Each deleted node's source files/folders are removed from disk

    Examples:
      seed-core delete mod-monitor                    # Delete a module
      seed-core delete mod-monitor --dry-run          # Preview what would be deleted
      seed-core delete subsystem-foo --no-source-files # Remove from model only
      seed-core delete reality-old --force            # Skip confirmation
    """
    from root_store.integration import verbal_delete
    from root_store.delete import compute_delete_closure, resolve_source_paths
    from root_store.loader import load_merged_model

    root_model_path = Path(root_model) if root_model else _default_root_model_path()

    # Load model to show preview
    graph = load_merged_model(root_model_path)

    if node_id not in graph.nodes:
        console.print(f"[red]Error:[/red] Node not found: {node_id}", file=sys.stderr)
        sys.exit(1)

    # Compute what will be deleted
    closure = compute_delete_closure(graph, [node_id])
    source_paths = resolve_source_paths(graph, closure, root_model_path)
    existing_paths = [str(p) for p in source_paths.values() if p.exists()]

    if json_output and dry_run:
        output = {
            "dry_run": True,
            "seed_node": node_id,
            "nodes_to_delete": sorted(closure),
            "source_paths_to_delete": existing_paths,
            "delete_source_files": not no_source_files,
        }
        console.print_json(data=output)
        return

    # Show preview
    if not force or dry_run:
        console.print(f"\n[bold]{'[DRY RUN] ' if dry_run else ''}Delete Preview[/bold]")
        console.print(f"Seed node: [cyan]{node_id}[/cyan]")
        console.print(f"\nNodes to delete ({len(closure)}):")
        for nid in sorted(closure):
            node = graph.nodes.get(nid, {})
            node_type = node.get("type", "?")
            label = node.get("label", nid)
            console.print(f"  [dim]{node_type}[/dim] {label} ({nid})")

        if existing_paths and not no_source_files:
            console.print(f"\nSource files/folders to delete ({len(existing_paths)}):")
            for p in sorted(existing_paths):
                console.print(f"  [red]{p}[/red]")
        elif no_source_files:
            console.print(f"\n[dim]Source files will be kept (--no-source-files)[/dim]")
        else:
            console.print(f"\n[dim]No source files to delete[/dim]")

    if dry_run:
        console.print(f"\n[yellow]Dry run complete. No changes made.[/yellow]")
        return

    # Confirm unless --force
    if not force:
        console.print("")
        if not click.confirm("Proceed with deletion?"):
            console.print("[dim]Cancelled.[/dim]")
            return

    # Perform deletion
    res = verbal_delete(
        root_model_path=root_model_path,
        node_id=node_id,
        delete_source_files=not no_source_files,
        dry_run=False,
    )

    if json_output:
        output = {
            "ok": res.ok,
            "seed_node": res.seed_node_id,
            "deleted_nodes": res.deleted_node_ids,
            "deleted_source_paths": res.deleted_source_paths,
            "removed_edge_count": res.removed_edge_count,
            "model_files_updated": res.model_files_updated,
            "errors": res.errors,
        }
        console.print_json(data=output)
        return

    if res.ok:
        console.print(Panel.fit(
            f"[bold green]Deleted[/bold green] {res.seed_node_id}\n\n"
            f"Nodes removed: {len(res.deleted_node_ids)}\n"
            f"Source paths deleted: {len(res.deleted_source_paths)}\n"
            f"Edges removed: {res.removed_edge_count}\n"
            f"Model files updated: {len(res.model_files_updated)}",
            border_style="green"
        ))
    else:
        console.print(Panel.fit(
            f"[bold red]Delete failed[/bold red] {res.seed_node_id}\n\n"
            f"Errors:\n" + "\n".join(f"  - {e}" for e in res.errors),
            border_style="red"
        ))
        sys.exit(1)


@cli.group()
def reality():
    """Manage individual realities."""
    pass


@reality.command('list')
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def reality_list(json_output):
    """List all realities.

    Shows a simple list of all realities tracked in the seed model.
    Green + indicates model is present, gray - indicates no model.

    Examples:
      seed-core reality list            # List all realities
      seed-core reality list --json     # Get JSON output
    """
    registry = get_registry()
    realities = registry.list_all()

    if json_output:
        output = [
            {
                'id': r.id,
                'label': r.label,
                'status': r.status,
                'has_model': r.has_model,
            }
            for r in realities
        ]
        console.print_json(data=output)
        return

    for reality in realities:
        model_indicator = "[green]+[/green]" if reality.has_model else "[dim]-[/dim]"
        console.print(f"{model_indicator} [cyan]{reality.label}[/cyan] ({reality.id})")


@reality.command('check')
@click.argument('reality_id')
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def reality_check(reality_id, json_output):
    """Check specific reality.

    REALITY_ID can be either the full reality ID (e.g. 'reality-spawnie')
    or the label (e.g. 'Spawnie').

    Examples:
      seed-core reality check Spawnie       # Check by label
      seed-core reality check reality-seed  # Check by ID
      seed-core reality check Seed --json   # Get JSON output
    """
    registry = get_registry()
    reality = registry.get(reality_id) or registry.find_by_label(reality_id)

    if not reality:
        console.print(f"[red]Reality not found:[/red] {reality_id}", file=sys.stderr)
        sys.exit(1)

    if json_output:
        output = {
            'id': reality.id,
            'label': reality.label,
            'description': reality.description,
            'status': reality.status,
            'path': reality.path,
            'model_path': str(reality.full_model_path) if reality.full_model_path else None,
            'has_model': reality.has_model,
            'model_summary': reality.model_summary,
        }
        console.print_json(data=output)
        return

    info = f"""[bold cyan]{reality.label}[/bold cyan]
ID: {reality.id}
Status: {reality.status or 'active'}
Path: {reality.path or '-'}
Model: {reality.full_model_path if reality.has_model else '[red]not found[/red]'}

Description:
{reality.description}"""

    console.print(Panel(info.strip(), title="Reality Details", border_style="cyan"))

    if reality.model_summary:
        console.print("\n[bold]Model Summary:[/bold]")
        console.print_json(data=reality.model_summary)


@cli.command()
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.option("-v", "--verbose", is_flag=True, help="Show detailed verification results")
def verify(json_output, verbose):
    """Verify all hashes to detect drift.

    Checks source file hashes against the model to detect when
    reality has diverged from the model (drift detection).

    Examples:
      seed-core verify                  # Run hash verification
      seed-core verify --verbose        # Show detailed results
      seed-core verify --json           # Get JSON output
    """
    registry = get_registry()
    results = verify_all_realities(registry)

    total_checks = 0
    total_ok = 0
    total_mismatch = 0
    total_missing = 0
    total_errors = 0

    for reality_checks in results.values():
        for check in reality_checks:
            total_checks += 1
            if check.status == "ok":
                total_ok += 1
            elif check.status == "mismatch":
                total_mismatch += 1
            elif check.status == "missing":
                total_missing += 1
            elif check.status == "error":
                total_errors += 1

    if json_output:
        output = {
            'summary': {
                'total_checks': total_checks,
                'ok': total_ok,
                'mismatch': total_mismatch,
                'missing': total_missing,
                'errors': total_errors,
            },
            'results': {
                reality_id: [
                    {
                        'node_id': check.node_id,
                        'source_path': check.source_path,
                        'expected_hash': check.expected_hash,
                        'actual_hash': check.actual_hash,
                        'status': check.status,
                        'error': check.error,
                    }
                    for check in checks
                ]
                for reality_id, checks in results.items()
            }
        }
        console.print_json(data=output)
        return

    total_issues = total_mismatch + total_missing + total_errors
    border_style = "green" if total_issues == 0 else "red"

    summary = f"""[bold]Hash Verification Results[/bold]

Total Checks: {total_checks}
[green]+ OK: {total_ok}[/green]
[red]x Mismatch: {total_mismatch}[/red]
[yellow]? Missing: {total_missing}[/yellow]
[red]! Errors: {total_errors}[/red]"""

    console.print(Panel(summary.strip(), border_style=border_style))

    if verbose:
        console.print("\n[bold]Detailed Results:[/bold]\n")

        for reality_id, checks in results.items():
            reality = registry.get(reality_id)
            console.print(f"[cyan]{reality.label if reality else reality_id}[/cyan]")

            for check in checks:
                status_icon = {
                    'ok': '[green]+[/green]',
                    'mismatch': '[red]x[/red]',
                    'missing': '[yellow]?[/yellow]',
                    'error': '[red]![/red]'
                }.get(check.status, '?')

                console.print(f"  {status_icon} {check.node_id}: {check.source_path}")

                if check.error:
                    console.print(f"     [dim]{check.error}[/dim]")

            console.print()


def main():
    cli()


if __name__ == "__main__":
    main()
