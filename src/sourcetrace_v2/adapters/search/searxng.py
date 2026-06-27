from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sourcetrace_v2.adapters.search.interfaces import SearchGateway
from sourcetrace_v2.core.domain.models import RetrievedEvidenceCandidate


class SearchGatewayError(RuntimeError):
    """Raised when a provider-backed search gateway cannot return usable results."""


@dataclass(frozen=True)
class SearxNGBootstrap:
    base_url: str
    language: str = "en"
    timeout_seconds: int = 10


class SearxNGSearchGateway(SearchGateway):
    provider_name = "searxng"

    def __init__(self, *, bootstrap: SearxNGBootstrap, count: int = 3) -> None:
        self.bootstrap = bootstrap
        self.count = count

    def search(self, *, job_id: str, run_id: str, query: str, limit: int) -> tuple[RetrievedEvidenceCandidate, ...]:
        try:
            rows = self._fetch(query=query, count=limit)
        except (OSError, TimeoutError, URLError, ValueError) as exc:
            raise SearchGatewayError(f"SearxNG search failed: {type(exc).__name__}: {exc}") from exc
        candidates: list[RetrievedEvidenceCandidate] = []
        seen: set[str] = set()
        for index, item in enumerate(rows, start=1):
            url = str(item.get("url") or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            title = str(item.get("title") or query).strip() or query
            snippet = str(item.get("content") or item.get("snippet") or "").strip()
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
        return tuple(candidates)

    def _fetch(self, *, query: str, count: int) -> list[dict[str, object]]:
        params = urlencode(
            {
                "q": query,
                "format": "json",
                "language": self.bootstrap.language,
            }
        )
        request = Request(
            f"{self.bootstrap.base_url.rstrip('/')}/search?{params}",
            headers={"Accept": "application/json", "User-Agent": "SourceTrace-v2/0.1"},
        )
        with urlopen(request, timeout=self.bootstrap.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        results = payload.get("results")
        if not isinstance(results, list):
            return []
        return [item for item in results[:count] if isinstance(item, dict)]
