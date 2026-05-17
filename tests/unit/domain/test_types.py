from sourcetrace.domain.types import (
    AnalystDisposition,
    HumanReviewStatus,
    QueueStatus,
    VerificationVerdict,
)


def test_verification_verdict_values() -> None:
    assert [verdict.value for verdict in VerificationVerdict] == [
        "support",
        "contradict",
        "insufficient_evidence",
    ]


def test_human_review_status_values() -> None:
    assert [status.value for status in HumanReviewStatus] == [
        "unreviewed",
        "reviewed_accept",
        "reviewed_override",
        "needs_followup",
        "excluded",
        "escalated",
    ]


def test_analyst_disposition_values() -> None:
    assert [disposition.value for disposition in AnalystDisposition] == [
        "confirmed_support",
        "confirmed_contradiction",
        "insufficient_evidence",
        "needs_more_collection",
        "exclude_from_report",
    ]


def test_queue_status_values() -> None:
    assert [status.value for status in QueueStatus] == [
        "new",
        "triaged",
        "in_review",
        "on_hold",
        "resolved",
        "escalated",
    ]
