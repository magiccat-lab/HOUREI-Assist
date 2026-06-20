"""SQLite metadata store + FTS5 trigram search."""

from __future__ import annotations

import sqlite3
from importlib.resources import files
from pathlib import Path

from ..models import ArticleChunk, SearchHit


class LawStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def open(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        schema_sql = (files("hourei_mcp.index") / "schema.sql").read_text()
        self._conn.executescript(schema_sql)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Store not opened")
        return self._conn

    def insert_chunks(self, chunks: list[ArticleChunk]) -> int:
        inserted = 0
        for chunk in chunks:
            try:
                self.conn.execute(
                    "INSERT OR REPLACE INTO articles (law_id, law_title, article_num, paragraph_num, item_num, heading, text, path) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (chunk.law_id, chunk.law_title, chunk.article_num, chunk.paragraph_num, chunk.item_num, chunk.heading, chunk.text, chunk.path),
                )
                inserted += 1
            except sqlite3.Error:
                continue
        self.conn.commit()
        return inserted

    def search_fts(self, query: str, *, limit: int = 20) -> list[SearchHit]:
        rows = self.conn.execute(
            "SELECT a.law_title, a.article_num, a.text, "
            "highlight(articles_fts, 2, '<<', '>>') AS context "
            "FROM articles_fts f "
            "JOIN articles a ON a.id = f.rowid "
            "WHERE articles_fts MATCH ? "
            "ORDER BY rank "
            "LIMIT ?",
            (_fts5_escape(query), limit),
        ).fetchall()
        return [
            SearchHit(
                law_title=row["law_title"],
                article_num=row["article_num"],
                text=row["text"],
                context=row["context"],
            )
            for row in rows
        ]

    def get_manifest(self, key: str) -> str | None:
        row = self.conn.execute("SELECT value FROM manifest WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    def set_manifest(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO manifest (key, value) VALUES (?, ?)",
            (key, value),
        )
        self.conn.commit()

    def article_count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS cnt FROM articles").fetchone()
        return row["cnt"]


def _fts5_escape(query: str) -> str:
    return '"' + query.replace('"', '""') + '"'
