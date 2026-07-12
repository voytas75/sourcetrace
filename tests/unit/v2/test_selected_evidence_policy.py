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

    assert payload["selection_basis"] == "rank_with_minimal_content_guard_and_domain_diversity"
    assert payload["selected_count"] == 2
    assert payload["items"][0]["title"] == "Rich"
    assert payload["items"][1]["title"] == "Also rich"
    assert payload["rejected_reasons"][1]["reason"] == "missing_minimal_content"
    assert payload["rejected_reasons"][1]["count"] == 1
    assert payload["rejected_reasons"][2]["reason"] == "domain_diversity_preference"


def test_selected_evidence_prefers_domain_diversity_when_quality_is_tied() -> None:
    artifact = ResearchResultArtifact(
        job_id="job-policy-domain",
        run_id="run-policy-domain",
        result_text="result",
        evidence_candidates=(
            RetrievedEvidenceCandidate(
                candidate_id="cand:1",
                job_id="job-policy-domain",
                run_id="run-policy-domain",
                provider="provider-a",
                query="query",
                title="A1",
                url="https://same.example.test/a1",
                snippet="Useful snippet A1",
                rank=1,
            ),
            RetrievedEvidenceCandidate(
                candidate_id="cand:2",
                job_id="job-policy-domain",
                run_id="run-policy-domain",
                provider="provider-b",
                query="query",
                title="A2",
                url="https://same.example.test/a2",
                snippet="Useful snippet A2",
                rank=2,
            ),
            RetrievedEvidenceCandidate(
                candidate_id="cand:3",
                job_id="job-policy-domain",
                run_id="run-policy-domain",
                provider="provider-c",
                query="query",
                title="B1",
                url="https://other.example.test/b1",
                snippet="Useful snippet B1",
                rank=3,
            ),
        ),
    )

    payload = project_selected_evidence(artifact=artifact)

    assert payload["items"][0]["title"] == "A1"
    assert payload["items"][1]["title"] == "B1"
    assert payload["rejected_reasons"][2]["reason"] == "domain_diversity_preference"
    assert payload["rejected_reasons"][2]["count"] == 1


def test_selected_evidence_keeps_stronger_second_official_candidate_over_weaker_diverse_candidate() -> None:
    artifact = ResearchResultArtifact(
        job_id="job-policy-official-pair",
        run_id="run-policy-official-pair",
        result_text="result",
        evidence_candidates=(
            RetrievedEvidenceCandidate(
                candidate_id="cand:1",
                job_id="job-policy-official-pair",
                run_id="run-policy-official-pair",
                provider="provider-a",
                query="Poland employer remote work obligations labour ministry official faq",
                title="Remote working regulations enter into force. We answer the most frequently asked questions",
                url="https://www.gov.pl/web/family/remote-working-regulations-enter-into-force-faq",
                snippet="Official ministry FAQ on employers' rights and remote work rules.",
                rank=1,
                source_type="institutional",
            ),
            RetrievedEvidenceCandidate(
                candidate_id="cand:2",
                job_id="job-policy-official-pair",
                run_id="run-policy-official-pair",
                provider="provider-b",
                query="Poland employer remote work obligations labour ministry official faq",
                title="Remote work - Ministry of Family, Labour and Social Policy - Gov.pl website",
                url="https://www.gov.pl/web/family/remote-work",
                snippet="Official ministry guidance on remote work under the Labour Code.",
                rank=2,
                source_type="institutional",
            ),
            RetrievedEvidenceCandidate(
                candidate_id="cand:3",
                job_id="job-policy-official-pair",
                run_id="run-policy-official-pair",
                provider="provider-c",
                query="Poland employer remote work obligations labour ministry official faq",
                title="Cross-Border Remote Work FAQs Poland - L&E Global",
                url="https://leglobal.law/countries/poland/poland-remote-work-faq/",
                snippet="General remote work FAQ for Poland.",
                rank=3,
                source_type="unknown",
            ),
        ),
    )

    payload = project_selected_evidence(artifact=artifact)

    assert payload["items"][0]["title"].startswith("Remote working regulations enter into force")
    assert payload["items"][1]["title"] == "Remote work - Ministry of Family, Labour and Social Policy - Gov.pl website"
