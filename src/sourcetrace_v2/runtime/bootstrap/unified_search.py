from __future__ import annotations

from collections.abc import Callable


def load_mycrewhelper_unified_search_web() -> Callable[..., list[dict[str, object]]] | None:
    try:
        from mycrewhelper.unified_search import UnifiedSearch
    except ImportError:
        return None

    search = UnifiedSearch(
        execution_mode="stepped",
        fallback_min_results=8,
        step_shuffle=False,
    )

    def unified_search_web(query: str, count: int = 10) -> list[dict[str, object]]:
        response = search.search(query, limit=count)
        payload = response.to_dict() if hasattr(response, "to_dict") else response
        results = payload.get("results", []) if isinstance(payload, dict) else []
        normalized: list[dict[str, object]] = []
        for item in results[:count]:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "url": str(item.get("url", "") or ""),
                    "title": str(item.get("title", "") or ""),
                    "snippet": str(item.get("snippet", "") or ""),
                }
            )
        return normalized

    return unified_search_web
