from sourcetrace_v2.core.domain.models import ResearchResultArtifact, RetrievedEvidenceCandidate
from sourcetrace_v2.projections.api.evidence import project_selected_evidence


def _candidate(*, title: str, url: str, snippet: str, rank: int, source_type: str) -> RetrievedEvidenceCandidate:
    return RetrievedEvidenceCandidate(
        candidate_id=f"cand:{rank}",
        job_id="job-inst-precision",
        run_id="run-inst-precision",
        provider="searxng",
        query="break glass account guidance conditional access official best practice",
        title=title,
        url=url,
        snippet=snippet,
        rank=rank,
        source_type=source_type,
    )


def test_institutional_source_type_improves_authority_on_exact_official_candidate() -> None:
    artifact = ResearchResultArtifact(
        job_id="job-inst-precision",
        run_id="run-inst-precision",
        result_text="result",
        evidence_candidates=(
            _candidate(
                title="Manage emergency access admin accounts - Microsoft Entra ID",
                url="https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/security-emergency-access",
                snippet="Official guidance for emergency access admin accounts.",
                rank=1,
                source_type="institutional",
            ),
            _candidate(
                title="r/sysadmin on Reddit: PSA: Stop Excluding Your Break Glass Global Admins from Conditional Access",
                url="https://www.reddit.com/r/sysadmin/comments/1hgjn87/psa_stop_excluding_your_break_glass_global_admins/",
                snippet="Community discussion with practical experience.",
                rank=2,
                source_type="unknown",
            ),
        ),
    )

    payload = project_selected_evidence(artifact=artifact)
    items = payload["items"]

    assert items[0]["title"].startswith("Manage emergency access admin accounts")
    assert items[0]["judgment"]["authority"]["band"] in {"high", "medium"}
    assert "institutional_source_type" in items[0]["judgment"]["authority"]["signals"]
    assert items[1]["judgment"]["authority"]["band"] == "none"
