from __future__ import annotations

import json
import logging
from pathlib import Path

import lancedb
import pyarrow as pa

logger = logging.getLogger(__name__)

TABLE_NAME = "project_context_chunks"


def _sql_literal(value: str) -> str:
    """Quote a value as a SQL string literal, escaping embedded single quotes.

    LanceDB 0.30 does not expose parameter binding on `.where()`, so all
    user- or caller-supplied identifiers must be escaped before interpolation.
    """
    if not isinstance(value, str):
        value = str(value)
    return "'" + value.replace("'", "''") + "'"


class VectorStore:
    """LanceDB wrapper for chunk storage, search, and retrieval."""

    def __init__(self, db_path: str, dimension: int = 384):
        path = Path(db_path)
        path.mkdir(parents=True, exist_ok=True)
        self._db = lancedb.connect(str(path))
        self._dimension = dimension
        self._table = None

    def _get_schema(self) -> pa.Schema:
        return pa.schema([
            pa.field("id", pa.string()),
            pa.field("project_id", pa.string()),
            pa.field("chunk_text", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), self._dimension)),
            pa.field("source_type", pa.string()),
            pa.field("source_id", pa.string()),
            pa.field("title", pa.string()),
            pa.field("chunk_index", pa.int32()),
            pa.field("total_chunks", pa.int32()),
            pa.field("metadata", pa.string()),
            pa.field("created_at", pa.string()),
        ])

    def _get_table(self):
        if self._table is None:
            try:
                self._table = self._db.open_table(TABLE_NAME)
            except Exception:
                self._table = self._db.create_table(
                    TABLE_NAME, schema=self._get_schema()
                )
        return self._table

    def add(self, records: list[dict]):
        table = self._get_table()
        table.add(records)

    def delete_by_source(self, source_id: str):
        table = self._get_table()
        table.delete(f"source_id = {_sql_literal(source_id)}")

    VALID_SOURCE_TYPES = {"file", "issue"}

    def search(
        self,
        query_vector: list[float],
        project_id: str,
        source_type: str | None = None,
        limit: int = 5,
    ) -> list[dict]:
        table = self._get_table()
        where = f"project_id = {_sql_literal(project_id)}"
        if source_type:
            if source_type not in self.VALID_SOURCE_TYPES:
                return []
            where += f" AND source_type = {_sql_literal(source_type)}"

        try:
            results = (
                table.search(query_vector)
                .where(where)
                .metric("cosine")
                .limit(limit)
                .to_list()
            )
        except Exception:
            return []

        return [
            {
                "chunk_id": r["id"],
                "title": r["title"],
                "source_type": r["source_type"],
                "source_id": r["source_id"],
                "project_id": r["project_id"],
                "score": round(1 - r.get("_distance", 0), 4),
                "preview": r["chunk_text"][:200],
            }
            for r in results
        ]

    def get_chunk(self, chunk_id: str, project_id: str) -> dict | None:
        table = self._get_table()
        try:
            results = (
                table.search()
                .where(
                    f"id = {_sql_literal(chunk_id)} "
                    f"AND project_id = {_sql_literal(project_id)}"
                )
                .limit(1)
                .to_list()
            )
        except Exception:
            # Fallback: scan all rows
            try:
                import pandas as pd
                df = table.to_pandas()
                mask = (df["id"] == chunk_id) & (df["project_id"] == project_id)
                filtered = df[mask]
                if filtered.empty:
                    return None
                results = filtered.to_dict(orient="records")
            except Exception:
                return None

        if not results:
            return None

        row = results[0]
        source_id = row["source_id"]

        # Find adjacent chunks
        previous_id = None
        next_id = None
        try:
            siblings = (
                table.search()
                .where(f"source_id = {_sql_literal(source_id)}")
                .limit(1000)
                .to_list()
            )
            siblings.sort(key=lambda r: r["chunk_index"])
            for i, s in enumerate(siblings):
                if s["id"] == chunk_id:
                    if i > 0:
                        previous_id = siblings[i - 1]["id"]
                    if i < len(siblings) - 1:
                        next_id = siblings[i + 1]["id"]
                    break
        except Exception:
            pass

        metadata = row.get("metadata", "{}")
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}

        return {
            "chunk_id": row["id"],
            "chunk_text": row["chunk_text"],
            "source_type": row["source_type"],
            "source_id": source_id,
            "title": row["title"],
            "chunk_index": row["chunk_index"],
            "total_chunks": row["total_chunks"],
            "metadata": metadata,
            "adjacent_chunks": {
                "previous": previous_id,
                "next": next_id,
            },
        }
