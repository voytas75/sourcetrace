from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from sourcetrace_v2.adapters.search.interfaces import SearchGateway
from sourcetrace_v2.adapters.search.searxng import SearchGatewayError
from sourcetrace_v2.core.domain.models import RetrievedEvidenceCandidate


@dataclass(frozen=True)
class UnifiedSearchBootstrap:
    search_web: Callable[..., object]
    provider_name: str = "procedural_admin_unified_search"
    count: int = 10


def _as_result_row(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return cast(dict[str, object], value)


class UnifiedSearchGateway(SearchGateway):
    def __init__(self, *, bootstrap: UnifiedSearchBootstrap) -> None:
        self.bootstrap = bootstrap
        self.provider_name = bootstrap.provider_name

    def search(
        self, *, job_id: str, run_id: str, query: str, limit: int
    ) -> tuple[RetrievedEvidenceCandidate, ...]:
        try:
            rows = self.bootstrap.search_web(
                query, count=max(limit, self.bootstrap.count)
            )
        except Exception as exc:  # pragma: no cover - defensive boundary
            raise SearchGatewayError(
                f"Unified Search failed: {type(exc).__name__}: {exc}"
            ) from exc
        if not isinstance(rows, list):
            raise SearchGatewayError(
                "Unified Search failed: expected list of result dicts"
            )
        candidates: list[RetrievedEvidenceCandidate] = []
        seen: set[str] = set()
        for index, raw_item in enumerate(cast(list[object], rows), start=1):
            item = _as_result_row(raw_item)
            if item is None:
                continue
            url = str(item.get("url") or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            title = str(item.get("title") or query).strip() or query
            snippet = str(item.get("snippet") or item.get("content") or "").strip()
            candidates.append(
                RetrievedEvidenceCandidate(
                    candidate_id=f"cand:{run_id}:{index}",
                    job_id=job_id,
                    run_id=run_id,
                    provider=self.provider_name,
                    query=query,
                    title=title,
                    url=url,
                    snippet=snippet,
                    rank=index,
                )
            )
            if len(candidates) >= limit:
                break
        return tuple(candidates)


def build_preferred_search_gateway(
    *, primary: SearchGateway | None, fallback: SearchGateway
) -> SearchGateway:
    if primary is None:
        return fallback

    class _PreferredSearchGateway(SearchGateway):
        def search(
            self, *, job_id: str, run_id: str, query: str, limit: int
        ) -> tuple[RetrievedEvidenceCandidate, ...]:
            hits = primary.search(
                job_id=job_id, run_id=run_id, query=query, limit=limit
            )
            if hits:
                return hits
            return fallback.search(
                job_id=job_id, run_id=run_id, query=query, limit=limit
            )

    return _PreferredSearchGateway()
