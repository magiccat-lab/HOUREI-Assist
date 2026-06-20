"""e-Gov 法令API v2 client."""

from __future__ import annotations

from typing import Any

import httpx
from lxml import etree

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
        return _parse_law_list(resp.content)

    async def keyword_search(self, keyword: str, *, limit: int = 100) -> list[dict[str, str]]:
        params = {"keyword": keyword, "limit": str(min(limit, 1000))}
        resp = await self._http.get("/keyword", params=params)
        resp.raise_for_status()
        return _parse_keyword_results(resp.content)

    async def get_law_data(self, law_id: str) -> bytes:
        resp = await self._http.get(f"/laws/{law_id}")
        resp.raise_for_status()
        return resp.content

    async def get_article(self, law_id: str, article: str, *, paragraph: str = "") -> str:
        xml_bytes = await self.get_law_data(law_id)
        return _extract_article(xml_bytes, article, paragraph)

    async def get_revisions(self, law_id: str) -> list[dict[str, str]]:
        resp = await self._http.get(f"/law_revisions/{law_id}")
        resp.raise_for_status()
        return _parse_revisions(resp.content)


def _parse_law_list(xml_bytes: bytes) -> list[LawRef]:
    root = etree.fromstring(xml_bytes)
    results = []
    for law in root.iter("LawNameListInfo"):
        law_id = _text(law, "LawId")
        law_num = _text(law, "LawNo")
        law_title = _text(law, "LawName")
        law_type = _text(law, "LawType")
        promulgation_date = _text(law, "PromulgationDate")
        if law_id and law_title:
            results.append(LawRef(
                law_id=law_id,
                law_num=law_num,
                law_title=law_title,
                law_type=law_type,
                promulgation_date=promulgation_date,
            ))
    return results


def _parse_keyword_results(xml_bytes: bytes) -> list[dict[str, str]]:
    root = etree.fromstring(xml_bytes)
    results = []
    for item in root.iter("Result"):
        results.append({
            "law_id": _text(item, "LawId"),
            "law_title": _text(item, "LawName"),
            "article": _text(item, "Article"),
            "text": _text(item, "Text"),
        })
    return results


def _extract_article(xml_bytes: bytes, article_num: str, paragraph_num: str) -> str:
    root = etree.fromstring(xml_bytes)
    lines: list[str] = []
    for article in root.iter("Article"):
        num = article.get("Num", "")
        if num != article_num:
            continue
        if paragraph_num:
            for para in article.iter("Paragraph"):
                if para.get("Num", "") == paragraph_num:
                    lines.append(_collect_text(para))
        else:
            lines.append(_collect_text(article))
        break
    return "\n".join(lines) if lines else f"Article {article_num} not found"


def _parse_revisions(xml_bytes: bytes) -> list[dict[str, str]]:
    root = etree.fromstring(xml_bytes)
    results = []
    for rev in root.iter("LawRevisionInfo"):
        results.append({
            "revision_id": _text(rev, "LawRevisionId"),
            "amendment_law": _text(rev, "AmendmentLawName"),
            "amendment_date": _text(rev, "AmendmentPromulgateDate"),
        })
    return results


def _text(elem: etree._Element, tag: str) -> str:
    child = elem.find(f".//{tag}")
    return (child.text or "").strip() if child is not None else ""


def _collect_text(elem: etree._Element) -> str:
    return "".join(elem.itertext()).strip()
