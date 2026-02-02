from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

from .loader import LoadedGraph, load_merged_model, load_merged_models


DEFAULT_DB_PATH = Path(__file__).parent / "root_store.db"


def open_db(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=OFF")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta(
          key TEXT PRIMARY KEY,
          value TEXT
        );

        CREATE TABLE IF NOT EXISTS nodes(
          id TEXT PRIMARY KEY,
          type TEXT,
          label TEXT,
          description TEXT,
          json TEXT NOT NULL,
          provenance_file TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS edges(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          type TEXT,
          from_id TEXT,
          to_id TEXT,
          json TEXT NOT NULL,
          provenance_file TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS node_text(
          id TEXT PRIMARY KEY,
          text TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS nodes_type_idx ON nodes(type);
        CREATE INDEX IF NOT EXISTS edges_from_idx ON edges(from_id);
        CREATE INDEX IF NOT EXISTS edges_to_idx ON edges(to_id);
        CREATE INDEX IF NOT EXISTS edges_type_idx ON edges(type);
        """
    )


def clear_index(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DELETE FROM meta;
        DELETE FROM node_text;
        DELETE FROM edges;
        DELETE FROM nodes;
        """
    )


def _node_text(n: Dict[str, Any]) -> str:
    parts = [
        n.get("id", ""),
        n.get("type", ""),
        n.get("label", ""),
        n.get("description", ""),
    ]
    return "\n".join([p for p in parts if isinstance(p, str)])


def index_graph(conn: sqlite3.Connection, graph: LoadedGraph) -> None:
    init_schema(conn)
    clear_index(conn)

    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)",
        ("schema_version", "v0"),
    )

    for node_id, node in graph.nodes.items():
        prov = graph.provenance_by_node_id.get(node_id)
        if prov is None:
            continue
        conn.execute(
            "INSERT OR REPLACE INTO nodes(id, type, label, description, json, provenance_file) VALUES(?, ?, ?, ?, ?, ?)",
            (
                node_id,
                node.get("type"),
                node.get("label"),
                node.get("description"),
                json.dumps(node, ensure_ascii=False),
                prov.file,
            ),
        )
        conn.execute(
            "INSERT OR REPLACE INTO node_text(id, text) VALUES(?, ?)",
            (node_id, _node_text(node)),
        )

    for idx, edge in enumerate(graph.edges):
        prov = graph.provenance_by_edge_index.get(idx)
        if prov is None:
            continue
        conn.execute(
            "INSERT INTO edges(type, from_id, to_id, json, provenance_file) VALUES(?, ?, ?, ?, ?)",
            (
                edge.get("type"),
                edge.get("from"),
                edge.get("to"),
                json.dumps(edge, ensure_ascii=False),
                prov.file,
            ),
        )


def rebuild_index(
    root_model_path: Path,
    db_path: Path = DEFAULT_DB_PATH,
) -> Path:
    """Rebuild the derived SQLite index from the canonical JSON model."""

    graph = load_merged_model(root_model_path)
    with open_db(db_path) as conn:
        index_graph(conn, graph)
        conn.commit()
    return db_path


def rebuild_index_multi(
    root_model_paths: list[Path],
    db_path: Path = DEFAULT_DB_PATH,
) -> Path:
    """Rebuild the derived SQLite index from multiple root entry models."""

    graph = load_merged_models(root_model_paths)
    with open_db(db_path) as conn:
        index_graph(conn, graph)
        conn.commit()
    return db_path


def get_meta(conn: sqlite3.Connection, key: str) -> Optional[str]:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return None if row is None else str(row["value"])
