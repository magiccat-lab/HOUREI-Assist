"""Tests for rules.provider — Notion block parsing and cache."""

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from hourei_mcp.rules.provider import RuleProvider, _extract_block_text


class TestExtractBlockText(unittest.TestCase):
    def test_paragraph(self):
        block = {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "テスト"}]}}
        assert _extract_block_text(block) == "テスト"

    def test_heading_1(self):
        block = {"type": "heading_1", "heading_1": {"rich_text": [{"plain_text": "見出し"}]}}
        assert _extract_block_text(block) == "# 見出し"

    def test_heading_2(self):
        block = {"type": "heading_2", "heading_2": {"rich_text": [{"plain_text": "中見出し"}]}}
        assert _extract_block_text(block) == "## 中見出し"

    def test_bulleted_list(self):
        block = {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"plain_text": "項目"}]}}
        assert _extract_block_text(block) == "- 項目"

    def test_numbered_list(self):
        block = {"type": "numbered_list_item", "numbered_list_item": {"rich_text": [{"plain_text": "手順"}]}}
        assert _extract_block_text(block) == "1. 手順"

    def test_to_do_unchecked(self):
        block = {"type": "to_do", "to_do": {"rich_text": [{"plain_text": "やること"}], "checked": False}}
        assert _extract_block_text(block) == "- [ ] やること"

    def test_to_do_checked(self):
        block = {"type": "to_do", "to_do": {"rich_text": [{"plain_text": "済み"}], "checked": True}}
        assert _extract_block_text(block) == "- [x] 済み"

    def test_quote(self):
        block = {"type": "quote", "quote": {"rich_text": [{"plain_text": "引用"}]}}
        assert _extract_block_text(block) == "> 引用"

    def test_divider(self):
        block = {"type": "divider", "divider": {}}
        assert _extract_block_text(block) == "---"

    def test_code(self):
        block = {"type": "code", "code": {"rich_text": [{"plain_text": "x = 1"}], "language": "python"}}
        assert _extract_block_text(block) == "```python\nx = 1\n```"

    def test_unknown_type(self):
        block = {"type": "table", "table": {}}
        assert _extract_block_text(block) is None

    def test_multi_rich_text(self):
        block = {"type": "paragraph", "paragraph": {"rich_text": [
            {"plain_text": "前半"},
            {"plain_text": "後半"},
        ]}}
        assert _extract_block_text(block) == "前半後半"


class TestRuleCache(unittest.TestCase):
    def test_local_cache_roundtrip(self, tmp_path=None):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            cache_dir = Path(td)
            cache_path = cache_dir / "rules_cache.json"
            cache_path.write_text(json.dumps({
                "text": "# ルール\n- テスト",
                "fetched_at": 1000.0,
                "page_id": "abc123",
                "last_edited": "",
            }))
            provider = RuleProvider("fake_key", "abc123", cache_dir=cache_dir)
            assert provider._cache.text == "# ルール\n- テスト"
            assert provider._cache.fetched_at == 1000.0

    def test_missing_cache_file(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            provider = RuleProvider("fake_key", "abc123", cache_dir=Path(td))
            assert provider._cache.text == ""

    def test_no_api_key_returns_empty(self):
        import asyncio
        provider = RuleProvider("", "", cache_dir=None)
        result = asyncio.run(provider.get_rules())
        assert result == ""
