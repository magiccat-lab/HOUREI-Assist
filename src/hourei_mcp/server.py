"""HOUREI-Assist MCP Server — FastMCP HTTP entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from mcp.server.fastmcp import FastMCP

from .config import Config
from .egov.client import EGovClient
from .index.store import LawStore
from .ndl.client import DietClient
from .rules.provider import RuleProvider
from .tools.debate import search_debate
from .tools.law import get_article, get_revision, search_law
from .tools.similar import similar_articles
from .tools.usage import search_usage

config = Config.from_env()

_egov: EGovClient | None = None
_store: LawStore | None = None
_diet: DietClient | None = None
_rules: RuleProvider | None = None
_embedder: object | None = None
_vstore: object | None = None
_vector_error: str | None = None


@asynccontextmanager
async def _lifespan(app: FastMCP) -> AsyncIterator[None]:
    global _egov, _store, _diet, _rules
    _egov = EGovClient(config)
    _diet = DietClient()
    _store = LawStore(config.fts_db_path)
    if config.fts_db_path.exists():
        _store.open()
    if config.notion_api_key and config.notion_rules_page_id:
        _rules = RuleProvider(
            config.notion_api_key,
            config.notion_rules_page_id,
            ttl=config.rules_cache_ttl,
            cache_dir=config.data_dir,
        )
    try:
        yield
    finally:
        if _rules:
            await _rules.close()
        if _vstore and hasattr(_vstore, "close"):
            _vstore.close()
        if _store:
            _store.close()
        if _diet:
            await _diet.close()
        if _egov:
            await _egov.close()


def _ensure_vector() -> str | None:
    """Lazy-load vector search. Returns error message or None on success."""
    global _embedder, _vstore, _vector_error
    if _vector_error is not None:
        return _vector_error
    if _embedder is not None and _vstore is not None:
        return None
    try:
        import faiss  # noqa: F401
    except ImportError:
        _vector_error = "ベクトル検索は未インストールです。`pip install hourei-mcp[vector]` を実行してください。"
        return _vector_error
    try:
        from .vector.store import VectorStore
        vs = VectorStore(config.data_dir / "vector")
        if not vs.exists():
            _vector_error = "ベクトルインデックスが未構築です。`hourei-mcp build-vector-index` を実行してください。"
            return _vector_error
        vs.open()
        _vstore = vs
    except Exception as e:
        _vector_error = f"ベクトルストア読込失敗: {e}"
        return _vector_error
    try:
        from .vector.embedder import RuriEmbedder
        _embedder = RuriEmbedder()
    except Exception as e:
        _vector_error = f"Ruri v3モデルロード失敗: {e}"
        return _vector_error
    return None


mcp = FastMCP(
    "hourei-assist",
    host=config.host,
    port=config.port,
    lifespan=_lifespan,
)


# --- Rules resource / prompt / tool ---


@mcp.resource("hourei://rules/current")
async def resource_rules() -> str:
    """現在の法令検索ルール(Notion SSoT)を返す。"""
    if not _rules:
        return "ルール未設定。NOTION_API_KEY と HOUREI_RULES_PAGE_ID を設定してください。"
    text = await _rules.get_rules()
    return text or "ルールページが空です。"


@mcp.prompt()
async def hourei_start() -> str:
    """法令調査・起草作業の開始時にルールを会話に注入する。"""
    if not _rules:
        return "法令検索ルールが未設定です。Notionページを設定してください。"
    text = await _rules.get_rules()
    if not text:
        return "法令検索ルールが空です。Notionページにルールを追加してください。"
    return f"以下の法令検索ルールに従って作業してください。\n\n---\n{text}\n---"


@mcp.tool()
async def tool_get_rules(force_refresh: bool = False) -> str:
    """現在の法令検索ルールを確認する。force_refresh=trueでNotionから再取得。"""
    if not _rules:
        return "ルール未設定。NOTION_API_KEY と HOUREI_RULES_PAGE_ID を環境変数に設定してください。"
    text = await _rules.get_rules(force=force_refresh)
    if not text:
        return "ルールページが空です。Notionページにルールを追加してください。"
    return text


# --- Law tools ---


@mcp.tool()
async def tool_search_law(keyword: str, category: int | None = None, limit: int = 20) -> str:
    """法令名で検索する。keyword: 検索キーワード, category: 法令種別(1=憲法,2=法律,3=政令,4=府省令), limit: 最大件数"""
    assert _egov is not None
    return await search_law(_egov, keyword, category=category, limit=limit)


@mcp.tool()
async def tool_get_article(law_id: str, article: str, paragraph: str = "") -> str:
    """条文を取得する。law_id: 法令ID(search_lawで取得), article: 条番号, paragraph: 項番号(省略可)"""
    assert _egov is not None
    return await get_article(_egov, law_id, article, paragraph=paragraph)


@mcp.tool()
async def tool_get_revision(law_id: str) -> str:
    """法令の改正履歴を取得する。law_id: 法令ID"""
    assert _egov is not None
    return await get_revision(_egov, law_id)


@mcp.tool()
async def tool_search_usage(phrase: str, limit: int = 20) -> str:
    """条文表現の用例を全法令から横断検索する(FTS5)。phrase: 検索する法令表現(例: 'の規定にかかわらず'), limit: 最大件数。インデックス未構築の場合はbuild-indexを先に実行してください。"""
    if not config.fts_db_path.exists():
        return "インデックスが未構築です。`hourei-mcp build-index` を実行してください。"
    if _store is not None and _store._conn is None:
        _store.open()
    if _store is None:
        return "サーバー初期化エラー。再起動してください。"
    return search_usage(_store, phrase, limit=limit)


@mcp.tool()
async def tool_keyword_search(keyword: str, limit: int = 100) -> str:
    """e-Gov全文検索API(/keyword)で法令本文を横断検索する。AND/OR/NOT/ワイルドカード対応。keyword: 検索式, limit: 最大件数(最大1000)"""
    assert _egov is not None
    results = await _egov.keyword_search(keyword, limit=limit)
    if not results:
        return f"「{keyword}」に該当する条文は見つかりませんでした。"
    lines = [f"## e-Gov全文検索: {keyword} ({len(results)}件)"]
    for r in results[:50]:
        lines.append(f"### {r.get('law_title', '?')} {r.get('article', '')}")
        lines.append(r.get("text", "")[:300])
        lines.append("")
    return "\n".join(lines)


@mcp.tool()
async def tool_search_debate(
    keyword: str,
    speaker: str = "",
    meeting: str = "",
    date_from: str = "",
    date_until: str = "",
    limit: int = 20,
) -> str:
    """国会議事録を検索する(立法経緯の確認)。keyword: 検索キーワード, speaker: 発言者名, meeting: 委員会名(例: '法務委員会'), date_from: 開始日(YYYY-MM-DD), date_until: 終了日, limit: 最大件数"""
    assert _diet is not None
    return await search_debate(
        _diet,
        keyword,
        speaker=speaker,
        meeting=meeting,
        date_from=date_from,
        date_until=date_until,
        limit=limit,
    )


@mcp.tool()
async def tool_similar_articles(query: str, limit: int = 10) -> str:
    """類似条文をベクトル検索する。query: 検索テキスト(条文や自然言語), limit: 最大件数。要: pip install hourei-mcp[vector] + build-vector-index"""
    err = _ensure_vector()
    if err:
        return err
    return await similar_articles(_embedder, _vstore, query, limit=limit)
