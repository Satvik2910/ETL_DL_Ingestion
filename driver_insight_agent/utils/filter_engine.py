from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence

from .validation import FilterCondition


def _match_condition(value: Any, cond: FilterCondition) -> bool:
    op = cond.op
    target = cond.value

    try:
        if op == "eq":
            return value == target
        if op == "neq":
            return value != target
        if op == "gt":
            return value > target  # type: ignore[operator]
        if op == "gte":
            return value >= target  # type: ignore[operator]
        if op == "lt":
            return value < target  # type: ignore[operator]
        if op == "lte":
            return value <= target  # type: ignore[operator]
        if op == "contains":
            if value is None:
                return False
            return str(target) in str(value)
        if op == "in":
            assert isinstance(target, list)
            return value in target
        if op == "nin":
            assert isinstance(target, list)
            return value not in target
        if op == "startswith":
            return str(value).startswith(str(target))
        if op == "endswith":
            return str(value).endswith(str(target))
    except Exception:
        return False
    return False


def _get_value(item: Dict[str, Any], field: str) -> Any:
    # simple key access; extend to dotted paths if needed
    return item.get(field)


def item_matches(item: Dict[str, Any], conditions: Sequence[FilterCondition]) -> bool:
    for cond in conditions:
        value = _get_value(item, cond.field)
        if not _match_condition(value, cond):
            return False
    return True


def apply_filters(items: Iterable[Dict[str, Any]], conditions: Sequence[FilterCondition]) -> List[Dict[str, Any]]:
    if not conditions:
        return list(items)
    return [it for it in items if item_matches(it, conditions)]


__all__ = ["apply_filters", "item_matches"]
