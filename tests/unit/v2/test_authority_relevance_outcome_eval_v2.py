import json
from pathlib import Path

from sourcetrace_v2.app.services.compiled_artifacts import build_compiled_artifact
from sourcetrace_v2.core.domain.models import ResearchResultArtifact, RetrievedEvidenceCandidate
from sourcetrace_v2.projections.api.evidence import project_selected_evidence


FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "v2" / "authority_relevance_outcome_eval_v2.json"


def _load_cases() -> list[dict[str, object]]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_authority_relevance_outcome_eval_v2_cases() -> None:
    for case in _load_cases():
        artifact_payload = case["artifact"]
        artifact = ResearchResultArtifact(
            job_id=artifact_payload["job_id"],
            run_id=artifact_payload["run_id"],
            result_text=artifact_payload["result_text"],
            evidence_candidates=tuple(
                RetrievedEvidenceCandidate(**candidate)
                for candidate in artifact_payload["evidence_candidates"]
            ),
        )

        selected_payload = project_selected_evidence(artifact=artifact)
        compiled = build_compiled_artifact(artifact=artifact)

        selected_titles = [item["title"] for item in selected_payload["items"]]
        compiled_titles = [item.title for item in compiled.selected_evidence]
        evaluation = case["evaluation"]

        assert evaluation["acceptable"] is True
        assert selected_payload["selected_count"] == 2
        assert selected_payload["selection_basis"] == "rank_with_minimal_content_guard_and_domain_diversity"

        for title in evaluation["must_include"]:
            assert title in selected_titles
            assert title in compiled_titles

        for title in evaluation["must_exclude"]:
            assert title not in selected_titles
            assert title not in compiled_titles
