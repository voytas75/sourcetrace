"""Minimal application runtime for LLM-backed claim extraction."""

from typing import TYPE_CHECKING

from sourcetrace.application.extraction import ClaimExtractionOutcome, ClaimExtractionRequest
from sourcetrace.domain import Claim, Document, DocumentChunk
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
        return ClaimExtractionOutcome(
            request=request,
            document=document,
            chunks=chunks,
            claims=claims,
            evidence_links=(),
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
