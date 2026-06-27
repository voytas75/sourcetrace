from __future__ import annotations

from sourcetrace_v2.core.domain.models import RetrievedEvidenceCandidate
from sourcetrace_v2.adapters.search.interfaces import SearchGateway


class StubSearchGateway(SearchGateway):
    def __init__(self, *, provider_name: str = "stub-search") -> None:
        self.provider_name = provider_name

    def search(self, *, job_id: str, run_id: str, query: str, limit: int) -> tuple[RetrievedEvidenceCandidate, ...]:
        return tuple(
            RetrievedEvidenceCandidate(
                candidate_id=f"cand:{run_id}:{index}",
                job_id=job_id,
                run_id=run_id,
                provider=self.provider_name,
                query=query,
                title=f"Stub result {index + 1} for {query[:40]}",
                url=f"https://example.test/{run_id}/{index + 1}",
                snippet=f"Stub evidence candidate {index + 1} for query: {query[:80]}",
                rank=index + 1,
            )
            for index in range(limit)
        )
