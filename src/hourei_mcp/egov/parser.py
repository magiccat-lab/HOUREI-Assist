"""Parse e-Gov law XML into ArticleChunk records for indexing."""

from __future__ import annotations

from lxml import etree

from ..models import ArticleChunk


def parse_law_xml(xml_bytes: bytes, *, law_id: str = "", law_title: str = "") -> list[ArticleChunk]:
    root = etree.fromstring(xml_bytes)
    if not law_title:
        title_el = root.find(".//LawTitle")
        law_title = (title_el.text or "").strip() if title_el is not None else ""
    if not law_id:
        law_num_el = root.find(".//LawNum")
        law_id = (law_num_el.text or "").strip() if law_num_el is not None else ""

    chunks: list[ArticleChunk] = []
    for article in root.iter("Article"):
        article_num = article.get("Num", "")
        article_caption = _caption(article)
        for paragraph in article.iter("Paragraph"):
            para_num = paragraph.get("Num", "")
            text = _normalize_text(_collect_text(paragraph))
            if not text:
                continue
            chunks.append(ArticleChunk(
                law_id=law_id,
                law_title=law_title,
                article_num=article_num,
                paragraph_num=para_num,
                heading=article_caption,
                text=text,
                path=f"{law_id}#a{article_num}p{para_num}",
            ))
        if not list(article.iter("Paragraph")):
            text = _normalize_text(_collect_text(article))
            if text:
                chunks.append(ArticleChunk(
                    law_id=law_id,
                    law_title=law_title,
                    article_num=article_num,
                    heading=article_caption,
                    text=text,
                    path=f"{law_id}#a{article_num}",
                ))
    return chunks


def _caption(article: etree._Element) -> str:
    cap = article.find("ArticleCaption")
    return (cap.text or "").strip() if cap is not None else ""


def _collect_text(elem: etree._Element) -> str:
    return "".join(elem.itertext())


def _normalize_text(text: str) -> str:
    return " ".join(text.split())
