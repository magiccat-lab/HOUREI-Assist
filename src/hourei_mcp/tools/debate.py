"""MCP tool: search_debate — 国会議事録検索."""

from __future__ import annotations

from ..ndl.client import DietClient


async def search_debate(
    client: DietClient,
    keyword: str,
    *,
    speaker: str = "",
    meeting: str = "",
    date_from: str = "",
    date_until: str = "",
    limit: int = 20,
) -> str:
    total, records = await client.search_speeches(
        keyword,
        speaker=speaker,
        meeting=meeting,
        date_from=date_from,
        date_until=date_until,
        limit=limit,
    )
    if not records:
        return f"「{keyword}」に該当する国会審議は見つかりませんでした。"

    lines = [f"## 国会議事録検索: {keyword} ({total}件中{len(records)}件表示)"]
    for rec in records:
        position = f" ({rec.speaker_position})" if rec.speaker_position else ""
        group = f" [{rec.speaker_group}]" if rec.speaker_group else ""
        lines.append(f"### {rec.date} {rec.house} {rec.meeting} {rec.issue}")
        lines.append(f"**{rec.speaker}**{position}{group}")
        excerpt = rec.speech.replace("\r\n", " ").replace("\n", " ")[:300]
        lines.append(excerpt)
        if rec.speech_url:
            lines.append(f"[全文]({rec.speech_url})")
        lines.append("")
    return "\n".join(lines)
