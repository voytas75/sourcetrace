from sourcetrace_v2.core.domain.models import ResearchResultArtifact, RetrievedEvidenceCandidate
from sourcetrace_v2.projections.api.evidence import project_selected_evidence


def test_selected_evidence_prefers_candidates_with_minimal_content() -> None:
    artifact = ResearchResultArtifact(
        job_id="job-policy",
        run_id="run-policy",
        result_text="result",
        evidence_candidates=(
            RetrievedEvidenceCandidate(
                candidate_id="cand:1",
                job_id="job-policy",
                run_id="run-policy",
                provider="provider-a",
                query="query",
                title="Thin",
                url="https://example.test/thin",
                snippet="",
                rank=1,
            ),
            RetrievedEvidenceCandidate(
                candidate_id="cand:2",
                job_id="job-policy",
                run_id="run-policy",
                provider="provider-b",
                query="query",
                title="Rich",
                url="https://example.test/rich",
                snippet="Useful snippet",
                rank=2,
            ),
            RetrievedEvidenceCandidate(
                candidate_id="cand:3",
                job_id="job-policy",
                run_id="run-policy",
                provider="provider-c",
                query="query",
                title="Also rich",
                url="https://example.test/richer",
                snippet="Another useful snippet",
                rank=3,
            ),
        ),
    )

    payload = project_selected_evidence(artifact=artifact)

    assert payload["selection_basis"] == "rank_with_minimal_content_guard"
    assert payload["selected_count"] == 2
    assert payload["items"][0]["title"] == "Rich"
    assert payload["items"][1]["title"] == "Also rich"
    assert payload["rejected_reasons"][1]["reason"] == "missing_minimal_content"
    assert payload["rejected_reasons"][1]["count"] == 1
