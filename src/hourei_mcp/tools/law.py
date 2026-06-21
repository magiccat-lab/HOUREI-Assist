"""MCP tools: search_law, get_article, get_revision."""

from __future__ import annotations

from ..egov.client import EGovClient


async def search_law(client: EGovClient, keyword: str, *, category: int | None = None, limit: int = 20) -> str:
    refs = await client.search_laws(keyword, category=category, limit=limit)
    if not refs:
        return f"「{keyword}」に該当する法令は見つかりませんでした。"
    lines = [f"## 法令検索結果: {keyword} ({len(refs)}件)"]
    for ref in refs:
        lines.append(f"- **{ref.law_title}** ({ref.law_num}) [ID: {ref.law_id}]")
    return "\n".join(lines)


async def get_article(client: EGovClient, law_id: str, article: str, *, paragraph: str = "") -> str:
    text = await client.get_article(law_id, article, paragraph=paragraph)
    loc = f"第{article}条"
    if paragraph:
        loc += f"第{paragraph}項"
    return f"## {loc}\n\n{text}"


async def get_revision(client: EGovClient, law_id: str) -> str:
    revisions = await client.get_revisions(law_id)
    if not revisions:
        return "改正履歴は見つかりませんでした。"
    lines = ["## 改正履歴"]
    for rev in revisions:
        date = rev.get('amendment_date', '?')
        law = rev.get('amendment_law', '?')
        rid = rev.get('revision_id', '')
        lines.append(f"- {date} {law} [rev: {rid}]")
    return "\n".join(lines)
