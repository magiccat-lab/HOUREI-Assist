"""国会議事録検索 API client — kokkai.ndl.go.jp/api"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class SpeechRecord:
    speech_id: str
    date: str
    house: str
    meeting: str
    issue: str
    speaker: str
    speaker_group: str
    speaker_position: str
    speech: str
    speech_url: str


class DietClient:
    BASE_URL = "https://kokkai.ndl.go.jp/api"

    def __init__(self, timeout: float = 30.0) -> None:
        self._http = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self._http.aclose()

    async def search_speeches(
        self,
        keyword: str,
        *,
        speaker: str = "",
        meeting: str = "",
        date_from: str = "",
        date_until: str = "",
        limit: int = 20,
    ) -> tuple[int, list[SpeechRecord]]:
        params: dict[str, Any] = {
            "any": keyword,
            "maximumRecords": str(min(limit, 100)),
            "recordPacking": "json",
        }
        if speaker:
            params["speaker"] = speaker
        if meeting:
            params["nameOfMeeting"] = meeting
        if date_from:
            params["from"] = date_from
        if date_until:
            params["until"] = date_until

        resp = await self._http.get(f"{self.BASE_URL}/speech", params=params)
        resp.raise_for_status()
        data = resp.json()

        total = data.get("numberOfRecords", 0)
        records = []
        for rec in data.get("speechRecord", []):
            records.append(SpeechRecord(
                speech_id=rec.get("speechID", ""),
                date=rec.get("date", ""),
                house=rec.get("nameOfHouse", ""),
                meeting=rec.get("nameOfMeeting", ""),
                issue=rec.get("issue", ""),
                speaker=rec.get("speaker", ""),
                speaker_group=rec.get("speakerGroup", ""),
                speaker_position=rec.get("speakerPosition") or "",
                speech=rec.get("speech", ""),
                speech_url=rec.get("speechURL", ""),
            ))
        return total, records
