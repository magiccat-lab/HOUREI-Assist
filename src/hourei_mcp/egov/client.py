"""e-Gov 法令API v2 client — JSON responses."""

from __future__ import annotations

import re
from typing import Any

import httpx

from ..config import Config
from ..models import LawRef


class EGovClient:
    def __init__(self, config: Config | None = None) -> None:
        self._config = config or Config()
        self._http = httpx.AsyncClient(
            base_url=self._config.egov_base_url,
            timeout=self._config.egov_timeout,
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def search_laws(self, keyword: str, *, category: int | None = None, limit: int = 20) -> list[LawRef]:
        params: dict[str, Any] = {"keyword": keyword, "limit": str(min(limit, 100))}
        if category is not None:
            params["category"] = str(category)
        resp = await self._http.get("/laws", params=params)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for entry in data.get("laws", []):
            li = entry.get("law_info", {})
            ri = entry.get("revision_info", {})
            law_id = li.get("law_id", "")
            law_title = ri.get("law_title", "")
            if law_id and law_title:
                results.append(LawRef(
                    law_id=law_id,
                    law_num=li.get("law_num", ""),
                    law_title=law_title,
                    law_type=li.get("law_type", ""),
                    promulgation_date=li.get("promulgation_date", ""),
                ))
        return results

    async def keyword_search(self, keyword: str, *, limit: int = 100) -> list[dict[str, str]]:
        params = {"keyword": keyword, "limit": str(min(limit, 1000))}
        resp = await self._http.get("/keyword", params=params)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("items", []):
            ri = item.get("revision_info", {})
            for sentence in item.get("sentences", []):
                text = _strip_html(sentence.get("text", ""))
                results.append({
                    "law_id": item.get("law_info", {}).get("law_id", ""),
                    "law_title": ri.get("law_title", ""),
                    "article": sentence.get("position", ""),
                    "text": text,
                })
        return results

    async def get_law_data(self, law_id: str) -> dict[str, Any]:
        revisions = await self.get_revisions(law_id)
        if not revisions:
            raise ValueError(f"No revisions found for {law_id}")
        revision_id = revisions[0]["revision_id"]
        resp = await self._http.get(f"/law_data/{revision_id}")
        resp.raise_for_status()
        return resp.json()

    async def get_article(self, law_id: str, article: str, *, paragraph: str = "") -> str:
        data = await self.get_law_data(law_id)
        tree = data.get("law_full_text", {})
        return _extract_article_from_tree(tree, article, paragraph)

    async def get_revisions(self, law_id: str) -> list[dict[str, str]]:
        resp = await self._http.get(f"/law_revisions/{law_id}")
        resp.raise_for_status()
        data = resp.json()
        results = []
        for rev in data.get("revisions", []):
            results.append({
                "revision_id": rev.get("law_revision_id", ""),
                "amendment_law": rev.get("amendment_law_title") or rev.get("law_title", ""),
                "amendment_date": rev.get("amendment_promulgate_date", ""),
            })
        return results


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def _collect_text(node: dict | str | list) -> str:
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(_collect_text(c) for c in node)
    if isinstance(node, dict):
        parts = []
        for child in node.get("children", []):
            parts.append(_collect_text(child))
        return "".join(parts)
    return ""


def _find_nodes(node: dict, tag: str) -> list[dict]:
    found = []
    if isinstance(node, dict):
        if node.get("tag") == tag:
            found.append(node)
        for child in node.get("children", []):
            if isinstance(child, dict):
                found.extend(_find_nodes(child, tag))
    return found


def _extract_article_from_tree(tree: dict, article_num: str, paragraph_num: str) -> str:
    articles = _find_nodes(tree, "Article")
    for article in articles:
        num = (article.get("attr") or {}).get("Num", "")
        if num != article_num:
            continue
        if paragraph_num:
            for para in _find_nodes(article, "Paragraph"):
                if (para.get("attr") or {}).get("Num", "") == paragraph_num:
                    return _collect_text(para)
        else:
            return _collect_text(article)
        break
    return f"Article {article_num} not found"
