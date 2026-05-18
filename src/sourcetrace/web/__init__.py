"""Web and API delivery layer."""

from sourcetrace.web.api import SourceTraceWSGIApp, create_wsgi_app
from sourcetrace.web.delivery import (
    PersistenceReportAssembler,
    SourceTraceDelivery,
    VerificationDeliveryRequest,
    VerificationInspection,
    claim_from_payload,
    claim_to_payload,
    create_default_delivery,
    evidence_link_to_payload,
    render_case_review_html,
    render_report_markdown,
    report_entry_to_payload,
    report_outcome_to_payload,
    review_decision_from_payload,
    verification_inspection_to_payload,
    verification_outcome_to_payload,
    verification_to_payload,
)

__all__ = [
    "PersistenceReportAssembler",
    "SourceTraceDelivery",
    "SourceTraceWSGIApp",
    "VerificationDeliveryRequest",
    "VerificationInspection",
    "claim_from_payload",
    "claim_to_payload",
    "create_default_delivery",
    "create_wsgi_app",
    "evidence_link_to_payload",
    "render_case_review_html",
    "render_report_markdown",
    "report_entry_to_payload",
    "report_outcome_to_payload",
    "review_decision_from_payload",
    "verification_inspection_to_payload",
    "verification_outcome_to_payload",
    "verification_to_payload",
]
