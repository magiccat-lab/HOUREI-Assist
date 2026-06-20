"""Runtime configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Config:
    host: str = "127.0.0.1"
    port: int = 8790
    data_dir: Path = field(default_factory=lambda: Path(os.environ.get("HOUREI_DATA_DIR", "~/.local/share/hourei-mcp")).expanduser())
    egov_base_url: str = "https://laws.e-gov.go.jp/api/2"
    egov_timeout: float = 30.0
    fts_db_name: str = "hourei.db"

    @property
    def fts_db_path(self) -> Path:
        return self.data_dir / self.fts_db_name

    @classmethod
    def from_env(cls) -> Config:
        return cls(
            host=os.environ.get("HOUREI_HOST", "127.0.0.1"),
            port=int(os.environ.get("HOUREI_PORT", "8790")),
            egov_timeout=float(os.environ.get("HOUREI_EGOV_TIMEOUT", "30")),
        )
