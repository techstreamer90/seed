from __future__ import annotations

import json
from pathlib import Path

from root_store.integration import verbal_save


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_verbal_save_writes_evidence_and_propagates(tmp_path: Path) -> None:
    base = tmp_path / "base"
    root_model = base / "model" / "sketch.json"
    sub_model = base / "sub" / "model" / "sketch.json"

    _write_json(
        root_model,
        {
            "schema_version": "3.0",
            "nodes": [
                {"id": "parent", "type": "Subsystem"},
                {"id": "mount-sub", "type": "Subsystem", "parent": "parent", "model": {"_ref": "sub/model/sketch.json"}},
            ],
            "edges": [
                {"type": "CONTAINS", "from": "parent", "to": "mount-sub"},
                {"type": "CONTAINS", "from": "mount-sub", "to": "child"},
            ],
        },
    )

    _write_json(
        sub_model,
        {
            "schema_version": "3.0",
            "nodes": [
                {"id": "child", "type": "Module"},
            ],
            "edges": [],
        },
    )

    res = verbal_save(root_model_path=root_model, node_id="child", propagate=True, run_rough_checks=False)
    assert res.chain == ["child", "mount-sub", "parent"]

    root_after = _read_json(root_model)
    sub_after = _read_json(sub_model)

    child = next(n for n in sub_after["nodes"] if n["id"] == "child")
    assert "evidence" in child and "integration_queue" in child["evidence"]
    # Always record at least an attempt; last_save may be absent if preflight blocks.
    iq = child["evidence"]["integration_queue"]
    assert "last_attempt" in iq

    parent = next(n for n in root_after["nodes"] if n["id"] == "parent")
    assert "evidence" in parent and "integration_queue" in parent["evidence"]
