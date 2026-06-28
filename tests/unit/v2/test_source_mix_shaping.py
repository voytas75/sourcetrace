from sourcetrace_v2.core.domain.models import RetrievedEvidenceCandidate
from sourcetrace_v2.execution.stages.retrieval import RetrievalStage


def _candidate(*, title: str, url: str, rank: int, source_type: str = "unknown") -> RetrievedEvidenceCandidate:
    return RetrievedEvidenceCandidate(
        candidate_id=f"cand:{rank}",
        job_id="job-source-mix",
        run_id="run-source-mix",
        provider="searxng",
        query="official guidance",
        title=title,
        url=url,
        snippet="snippet",
        rank=rank,
        source_type=source_type,
    )


def test_source_mix_shaping_promotes_institutional_sources_when_query_implies_official_intent() -> None:
    stage = RetrievalStage(search=None)  # type: ignore[arg-type]
    candidates = (
        _candidate(title="Vendor guide", url="https://vendor.example.test/guide", rank=1),
        _candidate(title="National Archives guidance", url="https://www.archives.gov/records-mgmt/policy", rank=2),
        _candidate(title="Official FAQ", url="https://gov.example.test/faq", rank=3),
    )

    shaped = stage._shape_source_mix(candidates=candidates, query="records retention official guidance")

    assert shaped[0].url == "https://www.archives.gov/records-mgmt/policy"
    assert shaped[1].url == "https://gov.example.test/faq"
    assert shaped[2].url == "https://vendor.example.test/guide"
    assert [candidate.rank for candidate in shaped] == [1, 2, 3]


def test_source_mix_shaping_uses_explicit_source_type_as_primary_signal() -> None:
    stage = RetrievalStage(search=None)  # type: ignore[arg-type]
    candidates = (
        _candidate(title="Commentary blog", url="https://blog.example.test/guide", rank=1, source_type="commentary"),
        _candidate(title="Institutional page", url="https://example.test/page", rank=2, source_type="institutional"),
        _candidate(title="Unknown page", url="https://example.test/other", rank=3, source_type="unknown"),
    )

    shaped = stage._shape_source_mix(candidates=candidates, query="official guidance")

    assert [candidate.source_type for candidate in shaped] == ["institutional", "unknown", "commentary"]


def test_source_mix_shaping_leaves_plain_queries_unchanged() -> None:
    stage = RetrievalStage(search=None)  # type: ignore[arg-type]
    candidates = (
        _candidate(title="Vendor guide", url="https://vendor.example.test/guide", rank=1),
        _candidate(title="National Archives guidance", url="https://www.archives.gov/records-mgmt/policy", rank=2),
    )

    shaped = stage._shape_source_mix(candidates=candidates, query="legal hold steps")

    assert tuple(candidate.url for candidate in shaped) == tuple(candidate.url for candidate in candidates)
