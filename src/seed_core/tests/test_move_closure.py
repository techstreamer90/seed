from __future__ import annotations

import json
from pathlib import Path

from root_store.loader import load_merged_model
from root_store.move import compute_move_closure, move_nodes_to_file


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_compute_move_closure_audit_check(tmp_path: Path) -> None:
    base = tmp_path / "base"
    root_model = base / "model" / "sketch.json"
    sub_model = base / "sub" / "model" / "sketch.json"

    _write_json(
        root_model,
        {
            "schema_version": "3.0",
            "nodes": [
                {
                    "id": "mount-sub",
                    "type": "Subsystem",
                    "model": {"_ref": "sub/model/sketch.json"},
                }
            ],
            "edges": [
                {"type": "HAS_CHECK", "from": "audit-1", "to": "check-1"},
            ],
        },
    )

    _write_json(
        sub_model,
        {
            "schema_version": "3.0",
            "nodes": [
                {"id": "audit-1", "type": "Audit"},
                {"id": "check-1", "type": "Check"},
            ],
            "edges": [],
        },
    )

    g = load_merged_model(root_model)

    assert compute_move_closure(g, ["audit-1"]) == {"audit-1", "check-1"}
    assert compute_move_closure(g, ["check-1"]) == {"audit-1", "check-1"}


def test_move_nodes_to_file_moves_closure(tmp_path: Path) -> None:
    base = tmp_path / "base"
    root_model = base / "model" / "sketch.json"
    sub_model = base / "sub" / "model" / "sketch.json"
    dest_model = base / "dest" / "model" / "sketch.json"

    _write_json(
        root_model,
        {
            "schema_version": "3.0",
            "nodes": [
                {
                    "id": "mount-sub",
                    "type": "Subsystem",
                    "model": {"_ref": "sub/model/sketch.json"},
                }
            ],
            "edges": [
                {"type": "HAS_CHECK", "from": "audit-1", "to": "check-1"},
            ],
        },
    )

    _write_json(
        sub_model,
        {
            "schema_version": "3.0",
            "nodes": [
                {"id": "audit-1", "type": "Audit", "status": "unknown"},
                {"id": "check-1", "type": "Check", "status": "unknown"},
            ],
            "edges": [],
        },
    )

    summary = move_nodes_to_file(
        root_model_path=root_model,
        seed_node_ids=["check-1"],
        dest_model_file=dest_model,
        include_closure=True,
    )

    assert set(summary.moved_node_ids) == {"audit-1", "check-1"}

    sub_after = _read_json(sub_model)
    dest_after = _read_json(dest_model)

    assert not any(n.get("id") == "audit-1" for n in sub_after["nodes"])
    assert not any(n.get("id") == "check-1" for n in sub_after["nodes"])

    assert any(n.get("id") == "audit-1" for n in dest_after["nodes"])
    assert any(n.get("id") == "check-1" for n in dest_after["nodes"])
