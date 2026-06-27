from __future__ import annotations

from sourcetrace_v2.core.domain.models import RetrievedEvidenceCandidate


class SearchGateway:
    def search(self, *, job_id: str, run_id: str, query: str, limit: int) -> tuple[RetrievedEvidenceCandidate, ...]:
        raise NotImplementedError
