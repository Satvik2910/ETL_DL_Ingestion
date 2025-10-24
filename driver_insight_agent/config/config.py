from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml


@dataclass(frozen=True)
class CacheConfig:
    ttl_seconds: int
    persistent_path: str
    namespace: str


@dataclass(frozen=True)
class ConcurrencyConfig:
    max_workers: int
    batch_size: int


@dataclass(frozen=True)
class PaginationConfig:
    page_size: int


@dataclass(frozen=True)
class SummarizationConfig:
    max_tokens: int


@dataclass(frozen=True)
class LoggingConfig:
    level: str
    json: bool


@dataclass(frozen=True)
class AppConfig:
    cache: CacheConfig
    concurrency: ConcurrencyConfig
    pagination: PaginationConfig
    summarization: SummarizationConfig
    logging: LoggingConfig


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _merge_dict(defaults: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(defaults)
    for k, v in overrides.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _merge_dict(result[k], v)
        else:
            result[k] = v
    return result


def load_config(config_path: str | None = None, overrides: Dict[str, Any] | None = None) -> AppConfig:
    """Load application configuration from YAML with optional overrides."""
    base_path = Path(config_path or Path(__file__).with_name("config.yaml"))
    data: Dict[str, Any] = _load_yaml(base_path)
    if overrides:
        data = _merge_dict(data, overrides)

    cache = data.get("cache", {})
    concurrency = data.get("concurrency", {})
    pagination = data.get("pagination", {})
    summarization = data.get("summarization", {})
    logging_cfg = data.get("logging", {})

    return AppConfig(
        cache=CacheConfig(
            ttl_seconds=int(cache.get("ttl_seconds", 900)),
            persistent_path=str(cache.get("persistent_path", ".cache/insight_cache.sqlite")),
            namespace=str(cache.get("namespace", "driver_insight")),
        ),
        concurrency=ConcurrencyConfig(
            max_workers=int(concurrency.get("max_workers", 8)),
            batch_size=int(concurrency.get("batch_size", 100)),
        ),
        pagination=PaginationConfig(page_size=int(pagination.get("page_size", 200))),
        summarization=SummarizationConfig(max_tokens=int(summarization.get("max_tokens", 512))),
        logging=LoggingConfig(level=str(logging_cfg.get("level", "INFO")), json=bool(logging_cfg.get("json", True))),
    )
