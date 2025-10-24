from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from .validation import AggregationSpec, RankingSpec


def _collect_field(items: Iterable[Mapping[str, Any]], field: str) -> List[float]:
    values: List[float] = []
    for it in items:
        v = it.get(field)
        if v is None:
            continue
        try:
            values.append(float(v))
        except Exception:
            continue
    return values


def aggregate(items: Iterable[Mapping[str, Any]], specs: Sequence[AggregationSpec]) -> Dict[str, float]:
    result: Dict[str, float] = {}
    materialized = list(items)
    for spec in specs:
        values = _collect_field(materialized, spec.field)
        key = f"{spec.kind}:{spec.field}"
        if not values:
            result[key] = 0.0
            continue
        if spec.kind == "sum":
            result[key] = float(sum(values))
        elif spec.kind == "avg":
            result[key] = float(sum(values) / len(values))
        elif spec.kind == "min":
            result[key] = float(min(values))
        elif spec.kind == "max":
            result[key] = float(max(values))
        elif spec.kind == "count":
            result[key] = float(len(values))
        else:
            result[key] = 0.0
    return result


def rank(items_by_driver: Mapping[str, Mapping[str, Any]], spec: RankingSpec) -> List[Tuple[str, float]]:
    rows: List[Tuple[str, float]] = []
    field = spec.field
    for driver_id, metrics in items_by_driver.items():
        v = metrics.get(field)
        try:
            rows.append((driver_id, float(v)))
        except Exception:
            continue
    reverse = spec.order == "desc"
    rows.sort(key=lambda x: (x[1], x[0]), reverse=reverse)  # deterministic
    return rows[: spec.limit]


def compare(metrics_by_driver: Mapping[str, Mapping[str, Any]], drivers: Sequence[str], field: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {"field": field, "drivers": []}
    for d in drivers:
        v = metrics_by_driver.get(d, {}).get(field)
        out["drivers"].append({"driver_id": d, "value": None if v is None else float(v)})
    return out


__all__ = ["aggregate", "rank", "compare"]
