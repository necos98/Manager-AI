"""LanceDB vector store for embedding-based search.

This module provides the LanceDB connection and table definitions.
Tables are created lazily on first use. Currently a placeholder for
future AI/embedding features.
"""

from pathlib import Path

import lancedb

from app.config import settings

_db = None


def get_lancedb():
    """Get or create the LanceDB connection."""
    global _db
    if _db is None:
        path = Path(settings.lancedb_path)
        path.mkdir(parents=True, exist_ok=True)
        _db = lancedb.connect(str(path))
    return _db


# Table schemas for future use:
# - "project_embeddings": id (str), vector (1536-dim), text (str)
# - "task_embeddings": id (str), field (str), vector (1536-dim), text (str)
