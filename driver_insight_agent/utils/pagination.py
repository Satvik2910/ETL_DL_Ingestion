from __future__ import annotations

import base64
import hashlib
import orjson
from typing import Any, Dict, List, Sequence, Tuple


def chunk_list(items: Sequence[Any], chunk_size: int) -> List[Sequence[Any]]:
    if chunk_size <= 0:
        return [items]
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def _checksum(request_id: str, offset: int, page_size: int) -> str:
    raw = f"{request_id}:{offset}:{page_size}".encode()
    return hashlib.sha1(raw).hexdigest()[:12]


def create_pagination_token(request_id: str, offset: int, page_size: int) -> str:
    payload = {"offset": offset, "page_size": page_size, "sum": _checksum(request_id, offset, page_size)}
    return base64.urlsafe_b64encode(orjson.dumps(payload, option=orjson.OPT_SORT_KEYS)).decode()


def parse_pagination_token(request_id: str, token: str | None) -> Tuple[int, int]:
    if not token:
        return 0, 0
    try:
        data: Dict[str, Any] = orjson.loads(base64.urlsafe_b64decode(token))
        offset = int(data.get("offset", 0))
        page_size = int(data.get("page_size", 0))
        if data.get("sum") != _checksum(request_id, offset, page_size):
            return 0, 0
        return offset, page_size
    except Exception:
        return 0, 0


def paginate_list(items: Sequence[Any], request_id: str, page_size: int, token: str | None) -> Tuple[List[Any], str | None]:
    start, provided_page_size = parse_pagination_token(request_id, token)
    if provided_page_size:
        page_size = provided_page_size
    end = start + page_size
    page = list(items[start:end])
    next_token = None
    if end < len(items):
        next_token = create_pagination_token(request_id, end, page_size)
    return page, next_token


__all__ = ["chunk_list", "paginate_list", "create_pagination_token", "parse_pagination_token"]
