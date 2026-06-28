from sourcetrace_v2.core.domain.models import RetrievedEvidenceCandidate
from sourcetrace_v2.execution.stages.retrieval import RetrievalStage


class _SpySearch:
    def __init__(self, results: tuple[RetrievedEvidenceCandidate, ...]) -> None:
        self.results = results
        self.calls: list[dict[str, object]] = []

    def search(self, *, job_id: str, run_id: str, query: str, limit: int) -> tuple[RetrievedEvidenceCandidate, ...]:
        self.calls.append({"job_id": job_id, "run_id": run_id, "query": query, "limit": limit})
        return self.results[:limit]


def _candidate(*, title: str, url: str, rank: int, source_type: str) -> RetrievedEvidenceCandidate:
    return RetrievedEvidenceCandidate(
        candidate_id=f"cand:{rank}",
        job_id="job-inst-window",
        run_id="run-inst-window",
        provider="searxng",
        query="records retention official guidance",
        title=title,
        url=url,
        snippet="snippet",
        rank=rank,
        source_type=source_type,
    )


def test_retrieval_window_limit_expands_for_institutional_intent_queries() -> None:
    stage = RetrievalStage(search=None)  # type: ignore[arg-type]

    assert stage._retrieval_window_limit(query="records retention official guidance") == 6
    assert stage._retrieval_window_limit(query="legal hold steps") == 3


def test_trim_candidate_window_restores_bounded_pool_after_shaping() -> None:
    stage = RetrievalStage(search=None)  # type: ignore[arg-type]
    candidates = (
        _candidate(title="A", url="https://a.example", rank=1, source_type="institutional"),
        _candidate(title="B", url="https://b.example", rank=2, source_type="vendor"),
        _candidate(title="C", url="https://c.example", rank=3, source_type="commentary"),
        _candidate(title="D", url="https://d.example", rank=4, source_type="unknown"),
    )

    trimmed = stage._trim_candidate_window(candidates=candidates)

    assert [candidate.url for candidate in trimmed] == ["https://a.example", "https://b.example", "https://c.example"]
    assert [candidate.rank for candidate in trimmed] == [1, 2, 3]


def test_source_mix_can_rescue_lower_ranked_institutional_candidate_before_final_trim() -> None:
    stage = RetrievalStage(search=None)  # type: ignore[arg-type]
    candidates = (
        _candidate(title="Vendor 1", url="https://vendor1.example/guide", rank=1, source_type="vendor"),
        _candidate(title="Vendor 2", url="https://vendor2.example/guide", rank=2, source_type="vendor"),
        _candidate(title="Vendor 3", url="https://vendor3.example/guide", rank=3, source_type="vendor"),
        _candidate(title="HHS litigation holds", url="https://www.hhs.gov/digital/governance/it-policy-archive/litigation-holds.html", rank=4, source_type="institutional"),
    )

    shaped = stage._shape_source_mix(candidates=candidates, query="legal hold records retention official guidance")
    trimmed = stage._trim_candidate_window(candidates=shaped)

    assert trimmed[0].source_type == "institutional"
    assert trimmed[0].url == "https://www.hhs.gov/digital/governance/it-policy-archive/litigation-holds.html"
    assert len(trimmed) == 3
