import tempfile
import unittest
from pathlib import Path

from hourei_mcp.egov.parser import parse_law_xml
from hourei_mcp.index.store import LawStore


FIXTURE_DIR = Path(__file__).parent / "fixtures"


class TestFTS(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "test.db"
        self.store = LawStore(self.db_path)
        self.store.open()
        xml_bytes = (FIXTURE_DIR / "sample_law.xml").read_bytes()
        chunks = parse_law_xml(xml_bytes, law_id="test_law")
        self.store.insert_chunks(chunks)

    def tearDown(self):
        self.store.close()
        self._tmp.cleanup()

    def test_search_finds_phrase(self):
        hits = self.store.search_fts("公共の福祉")
        self.assertGreaterEqual(len(hits), 1)
        self.assertIn("公共の福祉", hits[0].text)

    def test_search_returns_context_with_highlight(self):
        hits = self.store.search_fts("信義に従い")
        self.assertGreaterEqual(len(hits), 1)
        self.assertIn("<<", hits[0].context)

    def test_search_no_results(self):
        hits = self.store.search_fts("存在しないフレーズ12345")
        self.assertEqual(len(hits), 0)

    def test_article_count(self):
        count = self.store.article_count()
        self.assertEqual(count, 4)

    def test_manifest(self):
        self.store.set_manifest("test_key", "test_value")
        self.assertEqual(self.store.get_manifest("test_key"), "test_value")
        self.assertIsNone(self.store.get_manifest("nonexistent"))


if __name__ == "__main__":
    unittest.main()
