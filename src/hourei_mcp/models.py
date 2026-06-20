"""Shared domain models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LawRef:
    law_id: str
    law_num: str
    law_title: str
    law_type: str = ""
    promulgation_date: str = ""


@dataclass(frozen=True)
class ArticleChunk:
    law_id: str
    law_title: str
    article_num: str
    paragraph_num: str = ""
    item_num: str = ""
    heading: str = ""
    text: str = ""
    path: str = ""


@dataclass(frozen=True)
class SearchHit:
    law_title: str
    article_num: str
    text: str
    context: str = ""
    score: float = 0.0


@dataclass(frozen=True)
class EvidenceBundle:
    query: str
    similar_articles: list[SearchHit] = field(default_factory=list)
    usage_examples: list[SearchHit] = field(default_factory=list)
    revision_history: list[dict] = field(default_factory=list)
