import unittest
from pathlib import Path

from hourei_mcp.egov.parser import parse_law_xml


FIXTURE_DIR = Path(__file__).parent / "fixtures"


class TestParser(unittest.TestCase):
    def test_parse_sample_law(self):
        xml_bytes = (FIXTURE_DIR / "sample_law.xml").read_bytes()
        chunks = parse_law_xml(xml_bytes, law_id="明治二十九年法律第八十九号")
        self.assertEqual(len(chunks), 4)
        self.assertEqual(chunks[0].law_title, "民法")
        self.assertEqual(chunks[0].article_num, "1")
        self.assertEqual(chunks[0].paragraph_num, "1")
        self.assertIn("公共の福祉", chunks[0].text)

    def test_heading_extracted(self):
        xml_bytes = (FIXTURE_DIR / "sample_law.xml").read_bytes()
        chunks = parse_law_xml(xml_bytes)
        self.assertEqual(chunks[0].heading, "（基本原則）")
        self.assertEqual(chunks[3].heading, "（解釈の基準）")

    def test_path_format(self):
        xml_bytes = (FIXTURE_DIR / "sample_law.xml").read_bytes()
        chunks = parse_law_xml(xml_bytes, law_id="test")
        self.assertEqual(chunks[0].path, "test#a1p1")
        self.assertEqual(chunks[2].path, "test#a1p3")
        self.assertEqual(chunks[3].path, "test#a2p1")


if __name__ == "__main__":
    unittest.main()
