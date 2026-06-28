import json
from pathlib import Path

from sourcetrace_v2.app.services.compiled_artifacts import build_compiled_artifact
from sourcetrace_v2.core.contracts.read_models import (
    ExecutionRollup,
    PersistedExecutionView,
    PersistedRunEnvelope,
    PersistedViewStatus,
    PersistenceCompleteness,
)
from sourcetrace_v2.core.domain.models import ResearchResultArtifact, RetrievedEvidenceCandidate, RunPersistenceMarker
from sourcetrace_v2.projections.api.evidence import project_selected_evidence
from sourcetrace_v2.projections.api.trust import project_operator_trust


FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "v2" / "quality_regression_pack_v3.json"


def _load_cases() -> list[dict[str, object]]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _build_view(*, artifact: ResearchResultArtifact) -> PersistedExecutionView:
    return PersistedExecutionView(
        status=PersistedViewStatus.FOUND,
        envelope=PersistedRunEnvelope(
            job_id=artifact.job_id,
            run_id=artifact.run_id,
            status=PersistedViewStatus.FOUND,
            persistence_completeness=PersistenceCompleteness.COMPLETE,
            artifact_present=True,
            marker_present=True,
            marker_state="committed",
        ),
        artifact=artifact,
        compiled_artifact=build_compiled_artifact(artifact=artifact),
        marker=RunPersistenceMarker(job_id=artifact.job_id, run_id=artifact.run_id, status="committed"),
        rollup=ExecutionRollup(job_id=artifact.job_id, run_id=artifact.run_id, llm_calls=4, degraded_calls=0, failed_stages=0),
        stage_receipts=(),
        llm_receipts=(),
    )


def test_quality_regression_pack_v3_cases() -> None:
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
        trust_payload = project_operator_trust(view=_build_view(artifact=artifact))

        selected_titles = [item["title"] for item in selected_payload["items"]]
        compiled_titles = [item.title for item in compiled.selected_evidence]
        evaluation = case["evaluation"]
        trust = case["trust"]

        assert evaluation["acceptable"] is True
        assert selected_payload["selected_count"] == 2
        assert selected_payload["selection_basis"] == "rank_with_minimal_content_guard_and_domain_diversity"

        for title in evaluation.get("must_include", []):
            assert title in selected_titles
            assert title in compiled_titles

        for title in evaluation.get("must_exclude", []):
            assert title not in selected_titles
            assert title not in compiled_titles

        assert trust_payload["status"] == trust["status"]
        assert trust_payload["reasons"] == trust["reasons"]

