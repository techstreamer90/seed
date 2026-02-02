from __future__ import annotations

import json
from pathlib import Path
import sys

from root_store.save_exec import save_exec


def _write_minimal_model(path: Path, node: dict) -> None:
    model = {
        "schema_version": "3.0",
        "root": {
            "id": "root",
            "type": "Root",
            "label": "Root",
            "description": "Test model",
        },
        "nodes": [node],
        "edges": [],
    }
    path.write_text(json.dumps(model, indent=2, sort_keys=True), encoding="utf-8")


def test_save_exec_runs_command_and_writes_evidence(tmp_path: Path) -> None:
    model_path = tmp_path / "sketch.json"

    node_id = "node-with-save"
    node = {
        "id": node_id,
        "type": "Subsystem",
        "label": "Node With Save",
        "description": "Test node",
        "save": {
            "version": "v1",
            "actions": [
                {
                    "type": "command",
                    "argv": [sys.executable, "-c", "print('ok')"],
                    "cwd": str(tmp_path),
                }
            ],
        },
    }

    _write_minimal_model(model_path, node)

    result = save_exec(root_model_path=model_path, node_id=node_id)
    assert result.ok
    assert not result.used_fallback
    assert len(result.results) == 1

    updated = json.loads(model_path.read_text(encoding="utf-8"))
    updated_node = next(n for n in updated["nodes"] if n["id"] == node_id)
    assert "evidence" in updated_node
    assert "save_exec" in updated_node["evidence"]
    assert "last_run" in updated_node["evidence"]["save_exec"]
    assert updated_node["evidence"]["save_exec"]["last_run"]["ok"] is True


def test_save_exec_fallback_when_no_save(tmp_path: Path) -> None:
    model_path = tmp_path / "sketch.json"

    node_id = "node-no-save"
    node = {
        "id": node_id,
        "type": "Subsystem",
        "label": "Node No Save",
        "description": "Test node",
    }

    _write_minimal_model(model_path, node)

    result = save_exec(root_model_path=model_path, node_id=node_id)
    assert result.ok
    assert result.used_fallback
    assert len(result.results) == 0

    updated = json.loads(model_path.read_text(encoding="utf-8"))
    updated_node = next(n for n in updated["nodes"] if n["id"] == node_id)
    assert "evidence" in updated_node
    assert "save_exec" in updated_node["evidence"]
    assert "last_run" in updated_node["evidence"]["save_exec"]
    assert updated_node["evidence"]["save_exec"]["last_run"]["used_fallback"] is True
