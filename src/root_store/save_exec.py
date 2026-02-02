from __future__ import annotations

import subprocess
import sys
import shlex
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .loader import load_merged_model
from .writeback import apply_node_updates


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class CommandResult:
    action_index: int
    ok: bool
    returncode: int | None
    cwd: str | None
    run: str | None
    argv: List[str] | None
    stdout: str | None
    stderr: str | None


@dataclass(frozen=True)
class SaveExecResult:
    node_id: str
    ok: bool
    used_fallback: bool
    results: List[CommandResult]


def _truncate(s: str | None, limit: int = 8000) -> str | None:
    if s is None:
        return None
    if len(s) <= limit:
        return s
    return s[:limit] + "\n...<truncated>"


def _run_command(*, action: Dict[str, Any]) -> CommandResult:
    cwd = action.get("cwd")
    cwd_str = cwd if isinstance(cwd, str) and cwd else None

    argv_val = action.get("argv")
    argv: List[str] | None = None
    if isinstance(argv_val, list) and all(isinstance(x, str) for x in argv_val):
        argv = list(argv_val)

    run_val = action.get("run")
    run_str = run_val if isinstance(run_val, str) and run_val else None

    if argv is None and run_str is None:
        return CommandResult(
            action_index=-1,
            ok=False,
            returncode=None,
            cwd=cwd_str,
            run=None,
            argv=None,
            stdout=None,
            stderr="Invalid command action: expected argv (list[str]) or run (str)",
        )

    def _normalize_run_to_argv(cmd: str) -> List[str] | None:
        """Convert a run string to argv when we can do so safely.

        Key goal: avoid PATH-dependent wrappers (e.g. `seed-core`) that may
        invoke a different Python environment than this process.
        """

        try:
            parts = shlex.split(cmd, posix=False)
        except Exception:
            return None
        if not parts:
            return None

        exe = parts[0].lower()
        if exe in {"seed-core", "seed-core.exe"}:
            return [sys.executable, "-m", "seed_core", *parts[1:]]

        return None

    try:
        if argv is not None:
            p = subprocess.run(
                argv,
                cwd=cwd_str,
                capture_output=True,
                text=True,
                shell=False,
                check=False,
            )
        else:
            normalized = _normalize_run_to_argv(run_str or "")
            if normalized is not None:
                p = subprocess.run(
                    normalized,
                    cwd=cwd_str,
                    capture_output=True,
                    text=True,
                    shell=False,
                    check=False,
                )
                # Keep run_str for evidence, but also record argv for transparency.
                argv = normalized
            else:
                # Best-effort shell execution for Windows-friendly command strings.
                p = subprocess.run(
                    run_str,  # type: ignore[arg-type]
                    cwd=cwd_str,
                    capture_output=True,
                    text=True,
                    shell=True,
                    check=False,
                )
        ok = p.returncode == 0
        return CommandResult(
            action_index=-1,
            ok=ok,
            returncode=p.returncode,
            cwd=cwd_str,
            run=run_str,
            argv=argv,
            stdout=_truncate(p.stdout),
            stderr=_truncate(p.stderr),
        )
    except Exception as e:
        return CommandResult(
            action_index=-1,
            ok=False,
            returncode=None,
            cwd=cwd_str,
            run=run_str,
            argv=argv,
            stdout=None,
            stderr=f"Exception while running command: {e}",
        )


def save_exec(
    *,
    root_model_path: Path,
    node_id: str,
    stop_on_error: bool = True,
) -> SaveExecResult:
    """Execute node-defined save behavior.

    Contract (v0):
    - Load merged model from root_model_path
    - Find node_id
    - If node has dict `save` with list `actions`, execute them sequentially
      - Supported action: {type:"command", cwd?:str, argv?:list[str], run?:str}
    - Record outcomes into node.evidence.save_exec

    This is deterministic execution glue so Spawnie workflows can just pass node_id.
    """

    root_model_path = root_model_path.resolve()
    graph = load_merged_model(root_model_path)
    node = graph.nodes.get(node_id)

    results: List[CommandResult] = []

    used_fallback = False
    ok = True

    save = node.get("save") if isinstance(node, dict) else None
    actions = save.get("actions") if isinstance(save, dict) else None

    if not (isinstance(actions, list) and all(isinstance(a, dict) for a in actions)):
        used_fallback = True
        # Fallback is a no-op here; callers can run `seed-core save` separately.
        ok = True
    else:
        for idx, action in enumerate(actions):
            if action.get("type") != "command":
                cr = CommandResult(
                    action_index=idx,
                    ok=False,
                    returncode=None,
                    cwd=None,
                    run=None,
                    argv=None,
                    stdout=None,
                    stderr=f"Unsupported save action type: {action.get('type')}",
                )
                results.append(cr)
                ok = False
                if stop_on_error:
                    break
                continue

            cr = _run_command(action=action)
            # Patch in index (helper returns -1 by default)
            cr = CommandResult(
                action_index=idx,
                ok=cr.ok,
                returncode=cr.returncode,
                cwd=cr.cwd,
                run=cr.run,
                argv=cr.argv,
                stdout=cr.stdout,
                stderr=cr.stderr,
            )
            results.append(cr)
            if not cr.ok:
                ok = False
                if stop_on_error:
                    break

    payload = {
        "ran_at": _utc_now(),
        "node_id": node_id,
        "ok": ok,
        "used_fallback": used_fallback,
        "results": [
            {
                "action_index": r.action_index,
                "ok": r.ok,
                "returncode": r.returncode,
                "cwd": r.cwd,
                "run": r.run,
                "argv": r.argv,
                "stdout": r.stdout,
                "stderr": r.stderr,
            }
            for r in results
        ],
    }

    def update(n: Dict[str, Any]) -> None:
        ev = n.get("evidence")
        if not isinstance(ev, dict):
            ev = {}
        se = ev.get("save_exec")
        if not isinstance(se, dict):
            se = {}
        se["last_run"] = payload
        ev["save_exec"] = se
        n["evidence"] = ev

    apply_node_updates(graph=graph, default_model_file=root_model_path, updates={node_id: update})

    return SaveExecResult(node_id=node_id, ok=ok, used_fallback=used_fallback, results=results)
