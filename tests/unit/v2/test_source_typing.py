from sourcetrace_v2.core.domain.models import RetrievedEvidenceCandidate
from sourcetrace_v2.execution.stages.retrieval import RetrievalStage


def _candidate(*, title: str, url: str, rank: int) -> RetrievedEvidenceCandidate:
    return RetrievedEvidenceCandidate(
        candidate_id=f"cand:{rank}",
        job_id="job-source-type",
        run_id="run-source-type",
        provider="searxng",
        query="official guidance",
        title=title,
        url=url,
        snippet="snippet",
        rank=rank,
    )


def test_source_typing_labels_institutional_vendor_commentary_and_unknown() -> None:
    stage = RetrievalStage(search=None)  # type: ignore[arg-type]
    candidates = (
        _candidate(title="FTC guide", url="https://www.ftc.gov/business-guidance/resources/data-breach-response-guide-business", rank=1),
        _candidate(title="OpenText legal hold guide", url="https://www.opentext.com/products/legal-hold", rank=2),
        _candidate(title="Break glass best practices blog", url="https://blog.example.test/break-glass-best-practices", rank=3),
        _candidate(title="Some page", url="https://example.test/page", rank=4),
    )

    typed = stage._annotate_source_types(candidates=candidates)

    assert [candidate.source_type for candidate in typed] == ["institutional", "vendor", "commentary", "unknown"]


def test_source_typing_v2_covers_real_weak_case_hosts() -> None:
    stage = RetrievalStage(search=None)  # type: ignore[arg-type]
    candidates = (
        _candidate(title="Remote Work in Poland - Guide 2026", url="https://www.dudkowiak.com/employment-law-in-poland/remote-work-regulation-in-poland/", rank=1),
        _candidate(title="Manage emergency access admin accounts - Microsoft Entra ID | Microsoft Learn", url="https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/security-emergency-access", rank=2),
        _candidate(title="Litigation Holds (Legal Holds): A Comprehensive Guide - Everlaw", url="https://www.everlaw.com/blog/ediscovery-best-practices/guide-to-legal-holds/", rank=3),
    )

    typed = stage._annotate_source_types(candidates=candidates)

    assert [candidate.source_type for candidate in typed] == ["commentary", "institutional", "vendor"]


def test_source_typing_v3_covers_advisory_hosts_and_hosted_vendor_pdfs() -> None:
    stage = RetrievalStage(search=None)  # type: ignore[arg-type]
    candidates = (
        _candidate(title="Protecting your Break Glass accounts in Entra now that MFA gets enforced", url="https://www.vansurksum.com/2025/01/08/protecting-your-break-glass-accounts-in-entra-now-that-mfa-gets-enforced-on-more-and-more-admin-portals/", rank=1),
        _candidate(title="Remote work from abroad: OECD 2025 guidance for Poland - getsix", url="https://getsix.eu/resources/remote-work-from-abroad-oecd-2025-guidance-for-poland/", rank=2),
        _candidate(title="PDF OpenText | Practical guidance on managing legal holds - White paper", url="https://cloc.org/wp-content/uploads/2024/12/Practical-Guidance-on-Managing-Legal-Holds_Opentext_July2019.pdf", rank=3),
    )

    typed = stage._annotate_source_types(candidates=candidates)

    assert [candidate.source_type for candidate in typed] == ["commentary", "commentary", "vendor"]
