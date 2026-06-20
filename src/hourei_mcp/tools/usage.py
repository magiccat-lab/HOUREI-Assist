"""MCP tools: search_usage (FTS5 trigram full-text search)."""

from __future__ import annotations

from ..index.store import LawStore


def search_usage(store: LawStore, phrase: str, *, limit: int = 20) -> str:
    hits = store.search_fts(phrase, limit=limit)
    if not hits:
        return f"「{phrase}」の用例は見つかりませんでした。"
    lines = [f"## 用例検索: {phrase} ({len(hits)}件)"]
    for hit in hits:
        lines.append(f"### {hit.law_title} 第{hit.article_num}条")
        lines.append(hit.context or hit.text[:200])
        lines.append("")
    return "\n".join(lines)
