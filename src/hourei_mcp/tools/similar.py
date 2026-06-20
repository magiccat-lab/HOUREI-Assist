"""MCP tool: similar_articles — ベクトル類似条文検索."""

from __future__ import annotations

from ..models import SearchHit


async def similar_articles(
    embedder: object,
    store: object,
    query: str,
    *,
    limit: int = 10,
) -> str:
    from ..vector.embedder import RuriEmbedder
    from ..vector.store import VectorStore

    assert isinstance(embedder, RuriEmbedder)
    assert isinstance(store, VectorStore)

    q_emb = embedder.embed_query(query)
    hits = store.search(q_emb, limit=limit)

    if not hits:
        return f"「{query}」に類似する条文は見つかりませんでした。"

    lines = [f"## 類似条文検索: {query} ({len(hits)}件)"]
    for hit in hits:
        score_pct = f"{hit.score * 100:.1f}%"
        heading = f" {hit.context}" if hit.context else ""
        lines.append(f"### {hit.law_title} 第{hit.article_num}条{heading} (類似度: {score_pct})")
        lines.append(hit.text)
        lines.append("")
    return "\n".join(lines)
