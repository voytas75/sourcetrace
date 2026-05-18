"""Minimal application runtime for LLM-backed claim extraction."""

from typing import TYPE_CHECKING

from sourcetrace.application.extraction import ClaimExtractionOutcome, ClaimExtractionRequest
from sourcetrace.domain import Claim, ClaimEvidenceLink, Document, DocumentChunk
from sourcetrace.domain.types import VerificationVerdict

if TYPE_CHECKING:
    from sourcetrace.llm.interfaces import ClaimExtractionGateway
    from sourcetrace.storage.interfaces import ClaimRepository


class _LlmClaimExtractor:
    def __init__(
        self,
        *,
        extract_claims: "ClaimExtractionGateway",
        claim_repository: "ClaimRepository | None" = None,
    ) -> None:
        self._extract_claims = extract_claims
        self._claim_repository = claim_repository

    def __call__(
        self,
        request: ClaimExtractionRequest,
        *,
        document: Document,
        chunks: tuple[DocumentChunk, ...],
    ) -> ClaimExtractionOutcome:
        chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}
        prepared_text = "\n\n".join(
            f"[{chunk.chunk_id}] {chunk.raw_text}"
            for chunk in chunks
            if chunk.chunk_id in request.chunk_ids
        )
        result = self._extract_claims(prepared_text)
        claims = tuple(
            Claim(
                claim_id=str(item.get("claim_id") or f"claim-{index + 1}"),
                case_id=request.case_id,
                document_id=request.document_id,
                chunk_id=_chunk_id_for(item=item, request=request),
                exact_text=str(item.get("exact_text") or ""),
                source_span_reference=_span_reference_for(
                    item=item,
                    chunk_by_id=chunk_by_id,
                ),
                system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
                rationale=None,
            )
            for index, item in enumerate(result.payload.get("claims", ()))
        )
        if self._claim_repository is not None:
            claims = self._claim_repository.save_claims(claims)
        evidence_links = _build_initial_evidence_links(
            claims=claims,
            items=tuple(result.payload.get("claims", ())),
        )
        if self._claim_repository is not None:
            evidence_links = self._claim_repository.save_evidence_links(evidence_links)
        return ClaimExtractionOutcome(
            request=request,
            document=document,
            chunks=chunks,
            claims=claims,
            evidence_links=evidence_links,
        )


def _chunk_id_for(item: dict[str, object], request: ClaimExtractionRequest) -> str | None:
    chunk_id = item.get("chunk_id")
    if isinstance(chunk_id, str):
        return chunk_id
    if request.chunk_ids:
        return request.chunk_ids[0]
    return None


def _span_reference_for(
    *,
    item: dict[str, object],
    chunk_by_id: dict[str, DocumentChunk],
) -> str:
    span_reference = item.get("source_span_reference")
    if isinstance(span_reference, str) and span_reference:
        return span_reference
    chunk_id = item.get("chunk_id")
    if isinstance(chunk_id, str):
        chunk = chunk_by_id.get(chunk_id)
        if chunk is not None and chunk.position_reference is not None:
            return chunk.position_reference
    return "chunk-span:unknown"


def _build_initial_evidence_links(
    *,
    claims: tuple[Claim, ...],
    items: tuple[dict[str, object], ...],
) -> tuple[ClaimEvidenceLink, ...]:
    return tuple(
        _build_initial_evidence_link(claim=claim, item=item)
        for claim, item in zip(claims, items, strict=False)
    )


def _build_initial_evidence_link(
    *,
    claim: Claim,
    item: dict[str, object],
) -> ClaimEvidenceLink:
    evidence_payload = _evidence_payload_for(item)
    span_reference = claim.source_span_reference or "chunk-span:unknown"
    return ClaimEvidenceLink(
        claim_id=claim.claim_id,
        document_id=claim.document_id,
        chunk_id=claim.chunk_id,
        evidence_rank=1,
        evidence_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=_evidence_rationale(evidence_payload, span_reference=span_reference),
        snippet=_evidence_snippet(evidence_payload, claim=claim),
        score=_evidence_score(evidence_payload),
    )


def _evidence_payload_for(item: dict[str, object]) -> dict[str, object]:
    evidence = item.get("evidence")
    if isinstance(evidence, dict):
        return evidence
    return {}


def _evidence_rationale(
    evidence_payload: dict[str, object],
    *,
    span_reference: str,
) -> str:
    rationale = evidence_payload.get("rationale")
    if isinstance(rationale, str) and rationale:
        return rationale
    return f"Initial extraction link from chunk {span_reference}."


def _evidence_snippet(
    evidence_payload: dict[str, object],
    *,
    claim: Claim,
) -> str | None:
    snippet = evidence_payload.get("snippet")
    if isinstance(snippet, str) and snippet:
        return snippet
    return claim.exact_text or None


def _evidence_score(evidence_payload: dict[str, object]) -> float | None:
    score = evidence_payload.get("score")
    if isinstance(score, int | float):
        return float(score)
    return None


def build_llm_claim_extractor(
    *,
    extract_claims: "ClaimExtractionGateway",
    claim_repository: "ClaimRepository | None" = None,
) -> _LlmClaimExtractor:
    """Bind the LLM claim extraction gateway into the application extraction shape."""

    return _LlmClaimExtractor(
        extract_claims=extract_claims,
        claim_repository=claim_repository,
    )


__all__ = ["build_llm_claim_extractor"]
