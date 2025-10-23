from __future__ import annotations

from pathlib import Path
from typing import List

import yaml
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    api_base_url: str = Field(...)
    pagination_size: int = Field(100, ge=1, le=1000)
    max_retries: int = Field(3, ge=0, le=10)
    cache_ttl: int = Field(600, ge=0)
    mcp_tool_server_url: str = Field(...)
    required_fields: List[str] = Field(default_factory=lambda: ["driver_id", "name"]) 


def load_config(config_path: str | Path) -> AppConfig:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found at {path}")

    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    return AppConfig(**raw)
