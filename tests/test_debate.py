import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from hourei_mcp.ndl.client import DietClient, SpeechRecord
from hourei_mcp.tools.debate import search_debate


def _make_response(data):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = data
    resp.raise_for_status.return_value = None
    return resp


SAMPLE_RESPONSE = {
    "numberOfRecords": 42,
    "numberOfReturn": 2,
    "startRecord": 1,
    "nextRecordPosition": 3,
    "speechRecord": [
        {
            "speechID": "test-001",
            "date": "2026-04-21",
            "nameOfHouse": "参議院",
            "nameOfMeeting": "法務委員会",
            "issue": "第6号",
            "speaker": "テスト太郎",
            "speakerGroup": "テスト党",
            "speakerPosition": "大臣",
            "speech": "本改正案について申し上げます。民法第七百七十条の規定を改正し...",
            "speechURL": "https://kokkai.ndl.go.jp/test001",
            "speakerYomi": "",
            "speakerRole": None,
            "issueID": "",
            "imageKind": "",
            "searchObject": 1,
            "session": 221,
            "closing": None,
            "speechOrder": 1,
            "startPage": 1,
            "meetingURL": "",
            "pdfURL": "",
        },
        {
            "speechID": "test-002",
            "date": "2026-03-15",
            "nameOfHouse": "衆議院",
            "nameOfMeeting": "本会議",
            "issue": "第10号",
            "speaker": "テスト花子",
            "speakerGroup": "",
            "speakerPosition": None,
            "speech": "質問いたします。",
            "speechURL": "",
            "speakerYomi": "",
            "speakerRole": None,
            "issueID": "",
            "imageKind": "",
            "searchObject": 2,
            "session": 221,
            "closing": None,
            "speechOrder": 5,
            "startPage": 3,
            "meetingURL": "",
            "pdfURL": "",
        },
    ],
}


class TestDietClient(unittest.TestCase):
    def test_parse_response(self):
        import asyncio

        async def _test():
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = _make_response(SAMPLE_RESPONSE)
                client = DietClient()
                total, records = await client.search_speeches("民法改正")
                await client.close()

            self.assertEqual(total, 42)
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0].speaker, "テスト太郎")
            self.assertEqual(records[0].house, "参議院")
            self.assertEqual(records[0].meeting, "法務委員会")
            self.assertEqual(records[0].speaker_position, "大臣")
            self.assertIn("民法第七百七十条", records[0].speech)
            self.assertEqual(records[1].speaker_group, "")

        asyncio.run(_test())

    def test_empty_response(self):
        import asyncio

        async def _test():
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = _make_response({"numberOfRecords": 0})
                client = DietClient()
                total, records = await client.search_speeches("存在しない検索語")
                await client.close()

            self.assertEqual(total, 0)
            self.assertEqual(records, [])

        asyncio.run(_test())


class TestSearchDebateTool(unittest.TestCase):
    def test_format_output(self):
        import asyncio

        async def _test():
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = _make_response(SAMPLE_RESPONSE)
                client = DietClient()
                result = await search_debate(client, "民法改正")
                await client.close()

            self.assertIn("国会議事録検索", result)
            self.assertIn("42件中2件", result)
            self.assertIn("テスト太郎", result)
            self.assertIn("法務委員会", result)
            self.assertIn("(大臣)", result)

        asyncio.run(_test())

    def test_no_results(self):
        import asyncio

        async def _test():
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = _make_response({"numberOfRecords": 0})
                client = DietClient()
                result = await search_debate(client, "なし")
                await client.close()

            self.assertIn("見つかりませんでした", result)

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
