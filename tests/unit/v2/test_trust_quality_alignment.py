from sourcetrace_v2.app.services.compiled_artifacts import build_compiled_artifact
from sourcetrace_v2.core.contracts.read_models import ExecutionRollup, PersistedExecutionView, PersistedRunEnvelope, PersistedViewStatus, PersistenceCompleteness
from sourcetrace_v2.core.domain.models import ResearchResultArtifact, RetrievedEvidenceCandidate, RunPersistenceMarker
from sourcetrace_v2.projections.api.trust import project_operator_trust


def _candidate(*, title: str, url: str, rank: int, source_type: str, snippet: str) -> RetrievedEvidenceCandidate:
    return RetrievedEvidenceCandidate(
        candidate_id=f"cand:{rank}",
        job_id="job-trust-align",
        run_id="run-trust-align",
        provider="searxng",
        query="official guidance",
        title=title,
        url=url,
        snippet=snippet,
        rank=rank,
        source_type=source_type,
    )


def _view(*, artifact: ResearchResultArtifact, degraded_calls: int = 0) -> PersistedExecutionView:
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
        rollup=ExecutionRollup(job_id=artifact.job_id, run_id=artifact.run_id, llm_calls=4, degraded_calls=degraded_calls, failed_stages=0),
        stage_receipts=(),
        llm_receipts=(),
    )


def test_trust_contract_marks_low_authority_selected_shape_as_needs_review() -> None:
    artifact = ResearchResultArtifact(
        job_id="job-trust-align",
        run_id="run-trust-align",
        result_text="summary",
        evidence_candidates=(
            _candidate(
                title="Commercial explainer for official guidance",
                url="https://vendor.example.test/official-guidance-explainer",
                rank=1,
                source_type="unknown",
                snippet="Explainer about official guidance for organizations.",
            ),
            _candidate(
                title="Practical guide for compliance teams",
                url="https://vendor.example.test/practical-guide",
                rank=2,
                source_type="vendor",
                snippet="Practical guide for teams.",
            ),
        ),
    )

    payload = project_operator_trust(view=_view(artifact=artifact))

    assert payload["status"] == "needs_review"
    assert "low_confidence_selected_shape" in payload["reasons"]


def test_trust_contract_marks_jurisdiction_mixed_institutional_pair_as_needs_review() -> None:
    artifact = ResearchResultArtifact(
        job_id="job-trust-align-mixed",
        run_id="run-trust-align-mixed",
        result_text="summary",
        evidence_candidates=(
            _candidate(
                title="Starting or ending a business 3 | Internal Revenue Service",
                url="https://www.irs.gov/businesses/small-businesses-self-employed/starting-or-ending-a-business-3",
                rank=1,
                source_type="institutional",
                snippet="IRS guidance for small businesses.",
            ),
            _candidate(
                title="Small Businesses - Taxpayers | South African Revenue Service",
                url="https://www.sars.gov.za/types-of-tax/small-businesses-and-employment-taxes/",
                rank=2,
                source_type="institutional",
                snippet="SARS small business tax guidance.",
            ),
        ),
    )

    payload = project_operator_trust(view=_view(artifact=artifact))

    assert payload["status"] == "needs_review"
    assert payload["reasons"] == ["jurisdiction_mixed_selected_institutional_pair"]


def test_trust_contract_keeps_same_jurisdiction_institutional_shape_usable() -> None:
    artifact = ResearchResultArtifact(
        job_id="job-trust-align-strong",
        run_id="run-trust-align-strong",
        result_text="summary",
        evidence_candidates=(
            _candidate(
                title="Manage emergency access admin accounts - Microsoft Entra ID",
                url="https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/security-emergency-access",
                rank=1,
                source_type="institutional",
                snippet="Official Microsoft Learn guidance for emergency access admin accounts.",
            ),
            _candidate(
                title="Plan emergency access accounts - Microsoft Learn",
                url="https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/plan-emergency-access-accounts",
                rank=2,
                source_type="institutional",
                snippet="Official Microsoft Learn planning guidance for emergency access accounts.",
            ),
        ),
    )

    payload = project_operator_trust(view=_view(artifact=artifact))

    assert payload["status"] == "usable"
    assert payload["reasons"] == []
