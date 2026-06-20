"""Notion-backed rule provider with TTL cache."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx


@dataclass
class RuleCache:
    text: str = ""
    fetched_at: float = 0.0
    page_id: str = ""
    last_edited: str = ""


class RuleProvider:
    def __init__(
        self,
        notion_api_key: str,
        page_id: str,
        *,
        ttl: int = 300,
        cache_dir: Path | None = None,
    ) -> None:
        self._api_key = notion_api_key
        self._page_id = page_id
        self._ttl = ttl
        self._cache = RuleCache()
        self._cache_path = (cache_dir / "rules_cache.json") if cache_dir else None
        self._http = httpx.AsyncClient(
            base_url="https://api.notion.com/v1",
            headers={
                "Authorization": f"Bearer {notion_api_key}",
                "Notion-Version": "2022-06-28",
            },
            timeout=15.0,
        )
        self._load_local_cache()

    def _load_local_cache(self) -> None:
        if not self._cache_path or not self._cache_path.exists():
            return
        try:
            data = json.loads(self._cache_path.read_text())
            self._cache = RuleCache(
                text=data.get("text", ""),
                fetched_at=data.get("fetched_at", 0.0),
                page_id=data.get("page_id", ""),
                last_edited=data.get("last_edited", ""),
            )
        except (json.JSONDecodeError, OSError):
            pass

    def _save_local_cache(self) -> None:
        if not self._cache_path:
            return
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_path.write_text(json.dumps({
            "text": self._cache.text,
            "fetched_at": self._cache.fetched_at,
            "page_id": self._cache.page_id,
            "last_edited": self._cache.last_edited,
        }, ensure_ascii=False))

    async def get_rules(self, *, force: bool = False) -> str:
        if not self._api_key or not self._page_id:
            return ""

        now = time.time()
        if not force and self._cache.text and (now - self._cache.fetched_at) < self._ttl:
            return self._cache.text

        try:
            text = await self._fetch_page_blocks()
            self._cache = RuleCache(
                text=text,
                fetched_at=now,
                page_id=self._page_id,
            )
            self._save_local_cache()
            return text
        except Exception:
            if self._cache.text:
                return self._cache.text
            return ""

    async def _fetch_page_blocks(self) -> str:
        blocks: list[str] = []
        cursor: str | None = None

        while True:
            params: dict[str, str] = {"page_size": "100"}
            if cursor:
                params["start_cursor"] = cursor

            resp = await self._http.get(
                f"/blocks/{self._page_id}/children",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

            for block in data.get("results", []):
                text = _extract_block_text(block)
                if text is not None:
                    blocks.append(text)

            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")

        return "\n".join(blocks)

    async def close(self) -> None:
        await self._http.aclose()


def _extract_block_text(block: dict) -> str | None:
    btype = block.get("type", "")

    if btype in ("paragraph", "bulleted_list_item", "numbered_list_item", "to_do", "toggle", "quote", "callout"):
        rich = block.get(btype, {}).get("rich_text", [])
        text = "".join(rt.get("plain_text", "") for rt in rich)
        if btype == "bulleted_list_item":
            return f"- {text}"
        if btype == "numbered_list_item":
            return f"1. {text}"
        if btype == "to_do":
            checked = block.get(btype, {}).get("checked", False)
            return f"- [{'x' if checked else ' '}] {text}"
        if btype == "quote":
            return f"> {text}"
        return text

    if btype.startswith("heading_"):
        level = btype[-1]
        rich = block.get(btype, {}).get("rich_text", [])
        text = "".join(rt.get("plain_text", "") for rt in rich)
        return f"{'#' * int(level)} {text}"

    if btype == "divider":
        return "---"

    if btype == "code":
        rich = block.get("code", {}).get("rich_text", [])
        text = "".join(rt.get("plain_text", "") for rt in rich)
        lang = block.get("code", {}).get("language", "")
        return f"```{lang}\n{text}\n```"

    return None
