from __future__ import annotations

from typing import Any, Dict


def summarize_results(results: Dict[str, Any], report_type: str, max_tokens: int) -> str:
    # Deterministic, token-efficient. No randomness, simple structure.
    if not results:
        return "No results."

    def clamp(text: str) -> str:
        # Approximate token constraint by character length
        max_chars = max(64, max_tokens * 4)
        return text[:max_chars]

    if report_type == "score":
        scores = results.get("scores", {})
        n = len(scores)
        avg = 0.0
        if n:
            avg = sum(float(s.get("score", 0.0)) for s in scores.values()) / n
        return clamp(f"Scores for {n} drivers. Avg score: {avg:.1f}.")

    if report_type == "trip":
        trips = results.get("trips", {})
        total_trips = sum(len(v) for v in trips.values())
        total_miles = 0.0
        for v in trips.values():
            total_miles += sum(float(t.get("distance_miles", 0.0)) for t in v)
        return clamp(f"Trips: {total_trips} total, {total_miles:.1f} miles.")

    if report_type == "trend":
        series = results.get("trends", {})
        n = sum(len(v) for v in series.values())
        return clamp(f"Trend points: {n} across {len(series)} drivers.")

    # combined
    parts = []
    if "scores" in results:
        parts.append(f"scores={len(results['scores'])}")
    if "trips" in results:
        parts.append(f"trips={sum(len(v) for v in results['trips'].values())}")
    if "trends" in results:
        parts.append(f"trends={sum(len(v) for v in results['trends'].values())}")
    return clamp("Combined: " + ", ".join(parts))


__all__ = ["summarize_results"]
