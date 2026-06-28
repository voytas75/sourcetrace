from sourcetrace_v2.adapters.storage.jsonl import JsonlResultArtifactRepository
from sourcetrace_v2.core.domain.models import ResearchResultArtifact, RetrievedEvidenceCandidate


def test_jsonl_roundtrip_preserves_candidate_source_type(tmp_path) -> None:
    repo = JsonlResultArtifactRepository(tmp_path)
    result = ResearchResultArtifact(
        job_id="job-source-type",
        run_id="run-source-type",
        result_text="answer",
        evidence_query="official guidance",
        evidence_candidates=(
            RetrievedEvidenceCandidate(
                candidate_id="cand-1",
                job_id="job-source-type",
                run_id="run-source-type",
                provider="searxng",
                query="official guidance",
                title="FTC guide",
                url="https://www.ftc.gov/business-guidance/resources/data-breach-response-guide-business",
                snippet="official breach guide",
                rank=1,
                source_type="institutional",
            ),
        ),
    )
    repo.save_result(result)

    loaded = repo.get_result(job_id="job-source-type", run_id="run-source-type")

    assert loaded is not None
    assert loaded.evidence_candidates[0].source_type == "institutional"
