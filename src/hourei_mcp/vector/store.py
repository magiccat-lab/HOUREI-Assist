"""FAISS vector store + SQLite metadata for similar article search."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np

from ..models import SearchHit


class VectorStore:
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._index_path = data_dir / "articles.faiss"
        self._meta_path = data_dir / "articles_meta.db"
        self._index: Any = None
        self._meta_conn: sqlite3.Connection | None = None

    def exists(self) -> bool:
        return self._index_path.exists() and self._meta_path.exists()

    def open(self) -> None:
        import faiss

        self._index = faiss.read_index(str(self._index_path))
        self._meta_conn = sqlite3.connect(str(self._meta_path))
        self._meta_conn.row_factory = sqlite3.Row

    def close(self) -> None:
        if self._meta_conn:
            self._meta_conn.close()
            self._meta_conn = None
        self._index = None

    def build(self, embeddings: np.ndarray, metadata: list[dict[str, str]]) -> None:
        import faiss

        self._data_dir.mkdir(parents=True, exist_ok=True)

        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings.astype(np.float32))
        faiss.write_index(index, str(self._index_path))

        conn = sqlite3.connect(str(self._meta_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS article_meta (
                idx INTEGER PRIMARY KEY,
                law_id TEXT,
                law_title TEXT,
                article_num TEXT,
                paragraph_num TEXT,
                heading TEXT,
                text TEXT,
                path TEXT
            )
        """)
        conn.execute("DELETE FROM article_meta")
        for i, meta in enumerate(metadata):
            conn.execute(
                "INSERT INTO article_meta VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (i, meta.get("law_id", ""), meta.get("law_title", ""),
                 meta.get("article_num", ""), meta.get("paragraph_num", ""),
                 meta.get("heading", ""), meta.get("text", ""),
                 meta.get("path", "")),
            )
        conn.execute("""
            CREATE TABLE IF NOT EXISTS build_manifest (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.execute(
            "INSERT OR REPLACE INTO build_manifest VALUES (?, ?)",
            ("article_count", str(len(metadata))),
        )
        conn.execute(
            "INSERT OR REPLACE INTO build_manifest VALUES (?, ?)",
            ("dim", str(dim)),
        )
        conn.commit()
        conn.close()

    def search(self, query_embedding: np.ndarray, *, limit: int = 20) -> list[SearchHit]:
        if self._index is None or self._meta_conn is None:
            raise RuntimeError("VectorStore not opened")

        q = query_embedding.reshape(1, -1).astype(np.float32)
        scores, indices = self._index.search(q, limit)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            row = self._meta_conn.execute(
                "SELECT * FROM article_meta WHERE idx = ?", (int(idx),)
            ).fetchone()
            if row:
                results.append(SearchHit(
                    law_title=row["law_title"],
                    article_num=row["article_num"],
                    text=row["text"][:300],
                    context=row["heading"],
                    score=float(score),
                ))
        return results
