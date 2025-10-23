from __future__ import annotations

from typing import Iterable

from config.loader import AppConfig
from services.logger import get_logger


class Validator:
    def __init__(self, config: AppConfig) -> None:
        self._required = set(config.required_fields)
        self._log = get_logger("validator")

    def validate_minimum(self, record: dict) -> bool:
        missing = [field for field in self._required if field not in record or record.get(field) in (None, "")]
        if missing:
            self._log.warning("validation.missing_fields", missing=missing)
            return False
        return True

    def validate_many(self, records: Iterable[dict]) -> list[dict]:
        valid: list[dict] = []
        for rec in records:
            if self.validate_minimum(rec):
                valid.append(rec)
        return valid
