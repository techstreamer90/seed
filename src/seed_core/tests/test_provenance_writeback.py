from __future__ import annotations

import json
from pathlib import Path

from root_store.loader import load_merged_model
from root_store.writeback import apply_node_updates


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_apply_node_updates_writes_to_provenance_file(tmp_path: Path) -> None:
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
                    "type": "Reality",
                    "model": {"_ref": "sub/model/sketch.json"},
                },
                {"id": "check-root", "type": "Check", "status": "unknown"},
            ],
            "edges": [],
        },
    )

    _write_json(
        sub_model,
        {
            "schema_version": "3.0",
            "nodes": [
                {"id": "check-1", "type": "Check", "status": "unknown"},
            ],
            "edges": [],
        },
    )

    graph = load_merged_model(root_model)

    def set_pass(n: dict) -> None:
        n["status"] = "pass"

    results = apply_node_updates(
        graph=graph,
        default_model_file=root_model,
        updates={"check-1": set_pass, "check-root": set_pass},
    )

    assert results["check-1"] is True
    assert results["check-root"] is True

    sub_after = _read_json(sub_model)
    root_after = _read_json(root_model)

    assert next(n for n in sub_after["nodes"] if n["id"] == "check-1")["status"] == "pass"
    assert next(n for n in root_after["nodes"] if n["id"] == "check-root")["status"] == "pass"
