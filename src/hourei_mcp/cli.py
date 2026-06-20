"""CLI entrypoints: serve, build-index, check-index, smoke-test."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from .config import Config


def main() -> None:
    parser = argparse.ArgumentParser(prog="hourei-mcp", description="法令検索MCP Server")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("serve", help="MCP HTTP サーバーを起動")
    build_p = sub.add_parser("build-index", help="全法令XMLからFTS5インデックスを構築")
    build_p.add_argument("--xml-dir", type=Path, help="展開済みXMLディレクトリ")
    sub.add_parser("check-index", help="インデックスの整合性を確認")
    sub.add_parser("build-vector-index", help="FTS5インデックスからベクトルインデックスを構築(要[vector])")
    sub.add_parser("smoke-test", help="基本動作確認")

    args = parser.parse_args()

    if args.command == "serve":
        _cmd_serve()
    elif args.command == "build-index":
        asyncio.run(_cmd_build_index(args.xml_dir))
    elif args.command == "check-index":
        _cmd_check_index()
    elif args.command == "build-vector-index":
        _cmd_build_vector_index()
    elif args.command == "smoke-test":
        asyncio.run(_cmd_smoke_test())
    else:
        parser.print_help()
        sys.exit(1)


def _cmd_serve() -> None:
    from .server import mcp
    mcp.run(transport="streamable-http")


async def _cmd_build_index(xml_dir: Path | None) -> None:
    from .config import Config
    from .egov.parser import parse_law_xml
    from .index.store import LawStore

    config = Config.from_env()
    store = LawStore(config.fts_db_path)
    store.open()

    if xml_dir is None:
        xml_dir = config.data_dir / "xml"
    if not xml_dir.exists():
        print(f"XML directory not found: {xml_dir}")
        print("Download bulk XML from e-Gov first:")
        print("  curl -o laws.zip 'https://laws.e-gov.go.jp/bulkdownload?file_section=1&only_xml_flag=true'")
        print(f"  unzip laws.zip -d {xml_dir}")
        sys.exit(1)

    xml_files = sorted(xml_dir.glob("**/*.xml"))
    print(f"Found {len(xml_files)} XML files in {xml_dir}")
    total = 0
    for i, xml_path in enumerate(xml_files):
        try:
            chunks = parse_law_xml(xml_path.read_bytes())
            count = store.insert_chunks(chunks)
            total += count
        except Exception as e:
            print(f"  SKIP {xml_path.name}: {e}")
            continue
        if (i + 1) % 500 == 0:
            print(f"  {i + 1}/{len(xml_files)} processed, {total} chunks indexed")

    store.set_manifest("build_source", str(xml_dir))
    store.set_manifest("build_file_count", str(len(xml_files)))
    store.set_manifest("build_chunk_count", str(total))
    store.close()
    print(f"Done: {total} chunks from {len(xml_files)} files → {config.fts_db_path}")


def _cmd_check_index() -> None:
    from .config import Config
    from .index.store import LawStore

    config = Config.from_env()
    if not config.fts_db_path.exists():
        print(f"Index not found: {config.fts_db_path}")
        sys.exit(1)

    store = LawStore(config.fts_db_path)
    store.open()
    count = store.article_count()
    source = store.get_manifest("build_source") or "?"
    file_count = store.get_manifest("build_file_count") or "?"
    chunk_count = store.get_manifest("build_chunk_count") or "?"
    store.close()
    print(f"Index: {config.fts_db_path}")
    print(f"  Articles: {count}")
    print(f"  Source: {source}")
    print(f"  Files: {file_count}")
    print(f"  Chunks at build: {chunk_count}")


def _cmd_build_vector_index() -> None:
    try:
        from .vector.embedder import RuriEmbedder
        from .vector.store import VectorStore
    except ImportError:
        print("ベクトル検索の依存が未インストールです。")
        print("  pip install hourei-mcp[vector]")
        sys.exit(1)

    from .config import Config
    from .index.store import LawStore

    config = Config.from_env()
    if not config.fts_db_path.exists():
        print(f"FTS5インデックスが未構築です: {config.fts_db_path}")
        print("先に hourei-mcp build-index を実行してください。")
        sys.exit(1)

    fts = LawStore(config.fts_db_path)
    fts.open()
    count = fts.article_count()
    print(f"FTS5インデックス: {count} articles")

    rows = fts.conn.execute(
        "SELECT law_id, law_title, article_num, paragraph_num, heading, text, path FROM articles"
    ).fetchall()
    fts.close()

    texts = [row["text"] for row in rows]
    metadata = [dict(row) for row in rows]

    print(f"Embedding {len(texts)} articles with Ruri v3...")
    embedder = RuriEmbedder()
    embeddings = embedder.embed_documents(texts, batch_size=32)
    print(f"Embedding shape: {embeddings.shape}")

    vector_dir = config.data_dir / "vector"
    store = VectorStore(vector_dir)
    store.build(embeddings, metadata)
    print(f"Vector index built: {vector_dir}")


async def _cmd_smoke_test() -> None:
    from .egov.client import EGovClient

    config = Config.from_env()
    client = EGovClient(config)
    try:
        refs = await client.search_laws("民法", limit=3)
        print(f"search_law('民法'): {len(refs)} results")
        for ref in refs:
            print(f"  {ref.law_title} ({ref.law_num})")
        if refs:
            revs = await client.get_revisions(refs[0].law_id)
            print(f"get_revision: {len(revs)} revisions")
    finally:
        await client.close()
    print("Smoke test passed.")


if __name__ == "__main__":
    main()
