"""Runtime configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Config:
    host: str = "127.0.0.1"
    port: int = 8793
    data_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get("HOUREI_DATA_DIR", "~/.local/share/hourei-mcp"),
        ).expanduser(),
    )
    egov_base_url: str = "https://laws.e-gov.go.jp/api/2"
    egov_timeout: float = 30.0
    fts_db_name: str = "hourei.db"
    notion_api_key: str = ""
    notion_rules_page_id: str = ""
    rules_cache_ttl: int = 300

    @property
    def fts_db_path(self) -> Path:
        return self.data_dir / self.fts_db_name

    @classmethod
    def from_env(cls) -> Config:
        return cls(
            host=os.environ.get("HOUREI_HOST", "127.0.0.1"),
            port=int(os.environ.get("HOUREI_PORT", "8793")),
            egov_timeout=float(os.environ.get("HOUREI_EGOV_TIMEOUT", "30")),
            notion_api_key=os.environ.get("NOTION_API_KEY", ""),
            notion_rules_page_id=os.environ.get("HOUREI_RULES_PAGE_ID", ""),
            rules_cache_ttl=int(os.environ.get("HOUREI_RULES_CACHE_TTL", "300")),
        )
