from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class QueryResult:
    rows: List[Dict[str, Any]]


class QueryEngine:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        row = self._conn.execute(
            "SELECT id, type, label, description, json, provenance_file FROM nodes WHERE id = ?",
            (node_id,),
        ).fetchone()
        return None if row is None else dict(row)

    def find_nodes(self, type: Optional[str] = None, text: Optional[str] = None, limit: int = 50) -> QueryResult:
        sql = "SELECT n.id, n.type, n.label, n.description, n.provenance_file FROM nodes n"
        args: List[Any] = []
        clauses: List[str] = []

        if text:
            sql += " JOIN node_text t ON t.id = n.id"
            clauses.append("t.text LIKE ?")
            args.append(f"%{text}%")
        if type:
            clauses.append("n.type = ?")
            args.append(type)

        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY n.id LIMIT ?"
        args.append(limit)

        rows = [dict(r) for r in self._conn.execute(sql, args).fetchall()]
        return QueryResult(rows=rows)

    def outgoing(self, from_id: str, edge_type: Optional[str] = None, limit: int = 200) -> QueryResult:
        if edge_type:
            rows = [
                dict(r)
                for r in self._conn.execute(
                    "SELECT type, from_id, to_id, provenance_file FROM edges WHERE from_id = ? AND type = ? LIMIT ?",
                    (from_id, edge_type, limit),
                ).fetchall()
            ]
        else:
            rows = [
                dict(r)
                for r in self._conn.execute(
                    "SELECT type, from_id, to_id, provenance_file FROM edges WHERE from_id = ? LIMIT ?",
                    (from_id, limit),
                ).fetchall()
            ]
        return QueryResult(rows=rows)

    def incoming(self, to_id: str, edge_type: Optional[str] = None, limit: int = 200) -> QueryResult:
        if edge_type:
            rows = [
                dict(r)
                for r in self._conn.execute(
                    "SELECT type, from_id, to_id, provenance_file FROM edges WHERE to_id = ? AND type = ? LIMIT ?",
                    (to_id, edge_type, limit),
                ).fetchall()
            ]
        else:
            rows = [
                dict(r)
                for r in self._conn.execute(
                    "SELECT type, from_id, to_id, provenance_file FROM edges WHERE to_id = ? LIMIT ?",
                    (to_id, limit),
                ).fetchall()
            ]
        return QueryResult(rows=rows)
