from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from typing import Protocol, cast, runtime_checkable


class _UnifiedSearchClient(Protocol):
    def search(self, query: str, *, limit: int) -> object: ...


@runtime_checkable
class _ToDictResponse(Protocol):
    def to_dict(self) -> object: ...


def load_mycrewhelper_unified_search_web() -> Callable[..., list[dict[str, object]]] | None:
    try:
        module = import_module("mycrewhelper.unified_search")
    except ImportError:
        return None
    factory = getattr(module, "UnifiedSearch", None)
    if not callable(factory):
        return None

    search = cast(_UnifiedSearchClient, factory(
        execution_mode="stepped",
        fallback_min_results=8,
        step_shuffle=False,
    ))

    def unified_search_web(query: str, count: int = 10) -> list[dict[str, object]]:
        response = search.search(query, limit=count)
        payload = response.to_dict() if isinstance(response, _ToDictResponse) else response
        payload_object = _object_mapping(payload)
        results = _object_list(payload_object.get("results"))
        normalized: list[dict[str, object]] = []
        for item in results[:count]:
            item_object = _object_mapping(item)
            if not item_object:
                continue
            normalized.append(
                {
                    "url": str(item_object.get("url", "") or ""),
                    "title": str(item_object.get("title", "") or ""),
                    "snippet": str(item_object.get("snippet", "") or ""),
                }
            )
        return normalized

    return unified_search_web


def _object_mapping(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return {}


def _object_list(value: object) -> list[object]:
    if isinstance(value, list):
        return cast(list[object], value)
    return []
