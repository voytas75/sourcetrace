from sourcetrace_v2.app.services.compiled_artifacts import build_compiled_artifact
from sourcetrace_v2.core.contracts.read_models import ExecutionRollup, PersistedExecutionView, PersistedRunEnvelope, PersistedViewStatus, PersistenceCompleteness
from sourcetrace_v2.core.contracts.trust_metadata import SourceTraceTrustMetadata
from sourcetrace_v2.core.domain.models import ResearchResultArtifact, RetrievedEvidenceCandidate, RunPersistenceMarker
from sourcetrace_v2.execution.stages.retrieval import _build_retrieval_semantic_fit_diagnostics
from sourcetrace_v2.projections.api.trust import TRUST_USABLE, project_operator_trust


def _candidate(
    *,
    title: str,
    url: str,
    rank: int,
    source_type: str,
    snippet: str,
    query: str = "official guidance",
    trust_metadata: SourceTraceTrustMetadata | None = None,
) -> RetrievedEvidenceCandidate:
    return RetrievedEvidenceCandidate(
        candidate_id=f"cand:{rank}",
        job_id="job-trust-align",
        run_id="run-trust-align",
        provider="searxng",
        query=query,
        title=title,
        url=url,
        snippet=snippet,
        rank=rank,
        source_type=source_type,
        trust_metadata=trust_metadata,
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


def _semantic_fit_artifact(
    *,
    job_id: str,
    run_id: str,
    query: str,
    candidates: tuple[RetrievedEvidenceCandidate, ...],
) -> ResearchResultArtifact:
    diagnostics = _build_retrieval_semantic_fit_diagnostics(
        query=query,
        pretrim_candidates=candidates,
        trimmed_candidates=candidates,
        pretrim_explicit=True,
    )
    return ResearchResultArtifact(
        job_id=job_id,
        run_id=run_id,
        result_text="summary",
        evidence_query=query,
        evidence_candidates=candidates,
        pretrim_evidence_candidates=candidates,
        retrieval_diagnostics=diagnostics,
        retrieval_candidate_pool_count=len(candidates),
        retrieval_semantic_fit_status=diagnostics.pretrim.status,
        retrieval_best_focus_coverage=(
            diagnostics.pretrim.matched_term_count / diagnostics.pretrim.focus_term_count
            if diagnostics.pretrim.focus_term_count > 0
            else None
        ),
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

    assert payload["status"] == "usable"
    assert payload["reasons"] == []


def test_irrelevant_but_institutional_pool_marks_retrieval_semantic_fit_as_insufficient() -> None:
    query = "incident response reporting requirements"
    candidates = (
        _candidate(
            title="Agency Alpha climate adaptation strategy",
            url="https://agency-alpha.gov/publications/climate-adaptation",
            rank=1,
            source_type="institutional",
            snippet="Official strategy for climate adaptation and resilience planning.",
            query=query,
        ),
        _candidate(
            title="Agency Beta water conservation manual",
            url="https://agency-beta.gov/guidance/water-conservation",
            rank=2,
            source_type="institutional",
            snippet="Official manual for water conservation programs.",
            query=query,
        ),
    )
    artifact = _semantic_fit_artifact(
        job_id="job-trust-align-upstream-insufficient",
        run_id="run-trust-align-upstream-insufficient",
        query=query,
        candidates=candidates,
    )

    payload = project_operator_trust(view=_view(artifact=artifact))

    assert artifact.retrieval_candidate_pool_count == 2
    assert artifact.retrieval_semantic_fit_status == "insufficient"
    assert artifact.retrieval_best_focus_coverage == 0.0
    assert artifact.retrieval_diagnostics is not None
    assert artifact.retrieval_diagnostics.insufficiency_stage == "upstream_candidate_pool"
    assert payload["status"] == "needs_review"
    assert payload["reasons"] == ["retrieval_insufficient_semantic_fit"]


def test_trust_contract_keeps_relevant_different_institutional_domains_usable() -> None:
    query = "incident response guidance"
    artifact = ResearchResultArtifact(
        job_id="job-trust-align-different-institutions",
        run_id="run-trust-align-different-institutions",
        result_text="summary",
        evidence_candidates=(
            _candidate(
                title="Agency Alpha incident response guidance",
                url="https://agency-alpha.gov/guidance/incident-response",
                rank=1,
                source_type="institutional",
                snippet="Official incident response guidance for public-sector teams.",
                query=query,
            ),
            _candidate(
                title="Agency Beta incident response procedures",
                url="https://agency-beta.gov/publications/incident-response",
                rank=2,
                source_type="institutional",
                snippet="Official procedures for incident response and recovery.",
                query=query,
            ),
        ),
    )

    payload = project_operator_trust(view=_view(artifact=artifact))

    assert payload["status"] == TRUST_USABLE
    assert payload["reasons"] == []


def test_healthy_irs_like_pool_does_not_degrade_operator_trust() -> None:
    query = "tax filing deadline official guidance"
    candidates = (
        _candidate(
            title="IRS tax filing deadline extension guidance",
            url="https://www.irs.gov/newsroom/tax-filing-deadline-extension-guidance",
            rank=1,
            source_type="institutional",
            snippet="Official IRS guidance about the tax filing deadline and extension rules.",
            query=query,
        ),
        _candidate(
            title="IRS filing deadline help and payment options",
            url="https://www.irs.gov/payments/filing-deadline-help",
            rank=2,
            source_type="institutional",
            snippet="Official IRS help for filing deadline questions and payments.",
            query=query,
        ),
    )
    artifact = _semantic_fit_artifact(
        job_id="job-trust-align-irs-fit",
        run_id="run-trust-align-irs-fit",
        query=query,
        candidates=candidates,
    )

    payload = project_operator_trust(view=_view(artifact=artifact))

    assert artifact.retrieval_semantic_fit_status == "sufficient"
    assert artifact.retrieval_best_focus_coverage is not None
    assert artifact.retrieval_best_focus_coverage >= 0.5
    assert artifact.retrieval_diagnostics is not None
    assert artifact.retrieval_diagnostics.insufficiency_stage == "none"
    assert payload["status"] == TRUST_USABLE
    assert payload["reasons"] == []


def test_trust_contract_marks_strong_authority_but_weak_fit_as_needs_review() -> None:
    query = "incident response reporting requirements"
    artifact = ResearchResultArtifact(
        job_id="job-trust-align-weak-fit",
        run_id="run-trust-align-weak-fit",
        result_text="summary",
        evidence_candidates=(
            _candidate(
                title="Agency Alpha climate adaptation strategy",
                url="https://agency-alpha.gov/publications/climate-adaptation",
                rank=1,
                source_type="institutional",
                snippet="Official strategy for climate adaptation and resilience planning.",
                query=query,
            ),
            _candidate(
                title="Agency Beta water conservation manual",
                url="https://agency-beta.gov/guidance/water-conservation",
                rank=2,
                source_type="institutional",
                snippet="Official manual for water conservation programs.",
                query=query,
            ),
        ),
    )

    payload = project_operator_trust(view=_view(artifact=artifact))

    assert payload["status"] == "needs_review"
    assert payload["reasons"] == ["strong_authority_but_weak_fit_selected_shape"]


def test_trust_contract_keeps_relevant_same_institutional_surface_usable() -> None:
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
                query="emergency access accounts guidance",
            ),
            _candidate(
                title="Plan emergency access accounts - Microsoft Learn",
                url="https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/plan-emergency-access-accounts",
                rank=2,
                source_type="institutional",
                snippet="Official Microsoft Learn planning guidance for emergency access accounts.",
                query="emergency access accounts guidance",
            ),
        ),
    )

    payload = project_operator_trust(view=_view(artifact=artifact))

    assert payload["status"] == "usable"
    assert payload["reasons"] == []


def test_trust_contract_uses_selected_pair_after_minimal_content_guard() -> None:
    artifact = ResearchResultArtifact(
        job_id="job-trust-align-minimal-guard",
        run_id="run-trust-align-minimal-guard",
        result_text="summary",
        evidence_candidates=(
            _candidate(
                title="",
                url="https://vendor.example.test/empty-title",
                rank=1,
                source_type="vendor",
                snippet="Thin vendor result with missing title.",
            ),
            _candidate(
                title="Microsoft Entra emergency access guidance",
                url="https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/security-emergency-access",
                rank=2,
                source_type="institutional",
                snippet="Official Microsoft Learn guidance for emergency access accounts.",
            ),
            _candidate(
                title="Plan emergency access accounts - Microsoft Learn",
                url="https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/plan-emergency-access-accounts",
                rank=3,
                source_type="institutional",
                snippet="Official Microsoft Learn planning guidance for emergency access accounts.",
            ),
        ),
    )

    payload = project_operator_trust(view=_view(artifact=artifact))

    assert payload["status"] == TRUST_USABLE
    assert payload["reasons"] == []
    assert payload["selected_evidence_count"] == 2



def test_trust_contract_uses_selected_pair_after_domain_diversity_drop() -> None:
    artifact = ResearchResultArtifact(
        job_id="job-trust-align-domain-diversity",
        run_id="run-trust-align-domain-diversity",
        result_text="summary",
        evidence_candidates=(
            _candidate(
                title="Commercial explainer one",
                url="https://vendor.example.test/explainer-one",
                rank=1,
                source_type="vendor",
                snippet="Commercial explainer about official guidance.",
            ),
            _candidate(
                title="Commercial explainer two",
                url="https://vendor.example.test/explainer-two",
                rank=2,
                source_type="vendor",
                snippet="Another vendor explainer from the same domain.",
            ),
            _candidate(
                title="Official Microsoft Learn guidance",
                url="https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/security-emergency-access",
                rank=3,
                source_type="institutional",
                snippet="Official Microsoft Learn guidance for emergency access accounts.",
            ),
        ),
    )

    payload = project_operator_trust(view=_view(artifact=artifact))

    assert payload["status"] == TRUST_USABLE
    assert payload["reasons"] == []
    assert payload["selected_evidence_count"] == 2


def test_trust_contract_marks_explicit_cross_jurisdiction_institutional_pair_as_needs_review() -> None:
    artifact = ResearchResultArtifact(
        job_id="job-trust-align-explicit-cross-jurisdiction",
        run_id="run-trust-align-explicit-cross-jurisdiction",
        result_text="summary",
        evidence_candidates=(
            _candidate(
                title="Authority one filing guidance",
                url="https://authority-one.example.test/guidance",
                rank=1,
                source_type="institutional",
                snippet="Official filing guidance.",
                trust_metadata=SourceTraceTrustMetadata(
                    authority_id="authority-one", jurisdiction_id="US", scope="national",
                    provenance="operator", confidence="high",
                ),
            ),
            _candidate(
                title="Authority two filing guidance",
                url="https://authority-two.example.test/guidance",
                rank=2,
                source_type="institutional",
                snippet="Official filing guidance.",
                trust_metadata=SourceTraceTrustMetadata(
                    authority_id="authority-two", jurisdiction_id="ZA", scope="national",
                    provenance="operator", confidence="high",
                ),
            ),
        ),
    )

    payload = project_operator_trust(view=_view(artifact=artifact))

    assert payload["status"] == "needs_review"
    assert payload["reasons"] == ["jurisdiction_mixed_selected_institutional_pair"]


def test_trust_contract_keeps_explicit_same_jurisdiction_different_authorities_usable() -> None:
    artifact = ResearchResultArtifact(
        job_id="job-trust-align-explicit-same-jurisdiction",
        run_id="run-trust-align-explicit-same-jurisdiction",
        result_text="summary",
        evidence_candidates=(
            _candidate(
                title="Authority one incident guidance",
                url="https://authority-one.example.test/incident",
                rank=1,
                source_type="institutional",
                snippet="Official incident guidance.",
                trust_metadata=SourceTraceTrustMetadata(
                    authority_id="authority-one", jurisdiction_id="US", scope="national",
                    provenance="operator", confidence="high",
                ),
            ),
            _candidate(
                title="Authority two incident guidance",
                url="https://authority-two.example.test/incident",
                rank=2,
                source_type="institutional",
                snippet="Official incident guidance.",
                trust_metadata=SourceTraceTrustMetadata(
                    authority_id="authority-two", jurisdiction_id="US", scope="national",
                    provenance="operator", confidence="high",
                ),
            ),
        ),
    )

    payload = project_operator_trust(view=_view(artifact=artifact))

    assert payload["status"] == TRUST_USABLE
    assert payload["reasons"] == []
