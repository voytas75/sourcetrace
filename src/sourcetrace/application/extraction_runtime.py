"""Minimal application runtime for LLM-backed claim extraction."""

from typing import TYPE_CHECKING

from sourcetrace.application.extraction import ClaimExtractionOutcome, ClaimExtractionRequest
from sourcetrace.domain import Claim, ClaimEvidenceLink, Document, DocumentChunk
from sourcetrace.domain.types import VerificationVerdict

if TYPE_CHECKING:
    from sourcetrace.llm.interfaces import ClaimExtractionGateway, ClaimNormalizationGateway
    from sourcetrace.storage.interfaces import ClaimRepository


_CLAIM_TEXT_KEYS = ("exact_text", "text", "claim", "statement", "claim_text")
_CLAIM_CHUNK_KEYS = ("chunk_id", "source_chunk_id", "chunk")
_SPAN_REFERENCE_KEYS = ("source_span_reference", "span_reference", "span")
_EVIDENCE_KEYS = ("evidence", "evidence_items", "supporting_evidence")
_EVIDENCE_CHUNK_KEYS = ("chunk_id", "source_chunk_id", "chunk")
_EVIDENCE_SNIPPET_KEYS = ("snippet", "text", "quote", "evidence")
_EVIDENCE_RATIONALE_KEYS = ("rationale", "reason", "explanation")
_CONVERSATIONAL_CLAIM_PATTERNS = (
    "could you please clarify",
    "could you clarify",
    "if you need help",
    "let me know and i can help",
    "let me know and i can assist",
    "let me know if you need help",
    "let me know if you need",
    "thank you for your update",
    "thank you for the update",
    "it looks like you mentioned",
    "let me know how i can assist",
    "please provide more context",
    "so i can assist you better",
    "are you asking for more details",
    "here are a few ways you might do so",
    "if you need to expand or clarify this statement",
    "help drafting a report, summary, or announcement",
    "glad to hear",
    "i can help you draft",
    "customer notice",
    "incident summary",
    "outage update",
    "yes —",
    "yes -",
    "yes, ",
    "no —",
    "no -",
    "no, ",
)


class _LlmClaimExtractor:
    def __init__(
        self,
        *,
        extract_claims: "ClaimExtractionGateway",
        normalize_claim: "ClaimNormalizationGateway | None" = None,
        claim_repository: "ClaimRepository | None" = None,
    ) -> None:
        self._extract_claims = extract_claims
        self._normalize_claim = normalize_claim
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
        claim_items, dropped_claim_items = _claim_items_for(result.payload)
        claim_items = _deduplicate_claim_items(claim_items)
        claims = tuple(
            Claim(
                claim_id=_normalized_string(item.get("claim_id")) or f"claim-{index + 1}",
                case_id=request.case_id,
                document_id=request.document_id,
                chunk_id=_chunk_id_for(item=item, request=request),
                exact_text=_claim_text_for(item=item, normalize_claim=self._normalize_claim),
                source_span_reference=_span_reference_for(
                    item=item,
                    request=request,
                    chunk_by_id=chunk_by_id,
                ),
                system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
                rationale=None,
            )
            for index, item in enumerate(claim_items)
        )
        if self._claim_repository is not None:
            claims = self._claim_repository.save_claims(claims)
        evidence_links = _build_initial_evidence_links(
            claims=claims,
            items=claim_items,
        )
        dropped_evidence_items = _count_dropped_evidence_items(claim_items)
        if self._claim_repository is not None:
            evidence_links = self._claim_repository.save_evidence_links(evidence_links)
        return ClaimExtractionOutcome(
            request=request,
            document=document,
            chunks=chunks,
            claims=claims,
            evidence_links=evidence_links,
            dropped_claim_items=dropped_claim_items,
            dropped_evidence_items=dropped_evidence_items,
        )


def _chunk_id_for(item: dict[str, object], request: ClaimExtractionRequest) -> str | None:
    chunk_id = _first_normalized_item_string(item, *_CLAIM_CHUNK_KEYS)
    if chunk_id is not None:
        return chunk_id
    if request.chunk_ids:
        return request.chunk_ids[0]
    return None


def _normalized_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized


def _claim_text_for(
    *,
    item: dict[str, object],
    normalize_claim: "ClaimNormalizationGateway | None",
) -> str:
    exact_text = _first_normalized_item_string(item, *_CLAIM_TEXT_KEYS) or ""
    if normalize_claim is None or not exact_text:
        return exact_text
    normalized = normalize_claim(exact_text).text.strip()
    if _looks_conversational_response(normalized):
        return exact_text
    if _drops_attribution_or_caveat(source_text=exact_text, normalized_text=normalized):
        return exact_text
    return normalized or exact_text


def _drops_attribution_or_caveat(*, source_text: str, normalized_text: str) -> bool:
    source = source_text.casefold()
    normalized = normalized_text.casefold()
    for marker in (
        " said ",
        " according to ",
        " warned ",
        " claimed ",
        " stated ",
        " reported ",
        " analysts ",
        " analyst ",
        " ministry ",
        " agency ",
        " central bank",
        " should not be treated as",
        " remain temporary",
        " remains temporary",
        " no implementation timetable",
        " but ",
        " however ",
        " although ",
        " despite ",
        " no dataset",
        " no evidence",
        " has not been published",
        " has not been released",
    ):
        if marker in source and marker not in normalized:
            return True
    return False


def _normalized_item_string(item: dict[str, object], key: str) -> str | None:
    return _normalized_string(item.get(key))


def _first_normalized_item_string(item: dict[str, object], *keys: str) -> str | None:
    for key in keys:
        normalized = _normalized_item_string(item, key)
        if normalized is not None:
            return normalized
    return None


def _has_any_normalized_string(item: dict[str, object], *keys: str) -> bool:
    return any(_normalized_item_string(item, key) is not None for key in keys)


def _claim_items_for(payload: dict[str, object]) -> tuple[tuple[dict[str, object], ...], int]:
    claims = payload.get("claims")
    if not isinstance(claims, list):
        return (), 0
    normalized = tuple(item for item in claims if _is_valid_claim_payload(item))
    return normalized, len(claims) - len(normalized)


def _deduplicate_claim_items(
    items: tuple[dict[str, object], ...],
) -> tuple[dict[str, object], ...]:
    deduplicated: list[dict[str, object]] = []
    for item in items:
        claim_text = _first_normalized_item_string(item, *_CLAIM_TEXT_KEYS)
        if claim_text is None:
            deduplicated.append(item)
            continue
        for index, existing in enumerate(deduplicated):
            existing_text = _first_normalized_item_string(existing, *_CLAIM_TEXT_KEYS)
            if existing_text is None:
                continue
            if _is_near_duplicate_claim_text(existing_text, claim_text):
                if len(claim_text) > len(existing_text):
                    deduplicated[index] = item
                break
        else:
            deduplicated.append(item)
    return tuple(deduplicated)


def _is_near_duplicate_claim_text(left: str, right: str) -> bool:
    left_tokens = _claim_text_tokens(left)
    right_tokens = _claim_text_tokens(right)
    if not left_tokens or not right_tokens:
        return False
    shorter, longer = (left_tokens, right_tokens)
    if len(shorter) > len(longer):
        shorter, longer = longer, shorter
    overlap = sum(1 for token in shorter if token in longer)
    return overlap / len(shorter) >= 0.9


def _claim_text_tokens(text: str) -> tuple[str, ...]:
    return tuple(
        token
        for token in (
            normalized.strip(".,;:!?()[]{}\"'")
            for normalized in text.casefold().split()
        )
        if token
    )


def _is_valid_claim_payload(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    if _is_conversational_claim_payload(item):
        return False
    return _has_any_normalized_string(
        item,
        "claim_id",
        *_CLAIM_CHUNK_KEYS,
        *_CLAIM_TEXT_KEYS,
        *_SPAN_REFERENCE_KEYS,
    ) or bool(_evidence_items_for(item))


def _is_conversational_claim_payload(item: dict[str, object]) -> bool:
    claim_text = _first_normalized_item_string(item, *_CLAIM_TEXT_KEYS)
    if claim_text is None:
        return False
    return _looks_conversational_response(claim_text)


def _looks_conversational_response(text: str) -> bool:
    normalized = text.casefold()
    if any(pattern in normalized for pattern in _CONVERSATIONAL_CLAIM_PATTERNS):
        return True
    if "if you want" in normalized and "i can help" in normalized:
        return True
    if any(
        marker in normalized
        for marker in (
            "status update",
            "draft a report",
            "draft an update",
            "draft a status update",
            "customer notice",
            "incident summary",
        )
    ) and any(
        marker in normalized
        for marker in (
            "i can help",
            "i can assist",
            "if you want",
            "let me know",
        )
    ):
        return True
    line_count = sum(1 for line in text.splitlines() if line.strip())
    if line_count >= 3:
        return True
    if any(marker in normalized for marker in ("if you'd like", "if you would like", "let me know", "here's a bit more context", "to elaborate", "summary:")):
        return True
    if text.count("**") >= 2:
        return True
    return False


def _span_reference_for(
    *,
    item: dict[str, object],
    request: ClaimExtractionRequest,
    chunk_by_id: dict[str, DocumentChunk],
) -> str:
    span_reference = _first_normalized_item_string(item, *_SPAN_REFERENCE_KEYS)
    if span_reference is not None:
        return span_reference
    chunk_id = _first_normalized_item_string(item, *_CLAIM_CHUNK_KEYS)
    if chunk_id is not None:
        chunk = chunk_by_id.get(chunk_id)
        if chunk is not None and chunk.position_reference is not None:
            return chunk.position_reference
    if len(request.chunk_ids) == 1:
        request_chunk = chunk_by_id.get(request.chunk_ids[0])
        if request_chunk is not None and request_chunk.position_reference is not None:
            return request_chunk.position_reference
    return "chunk-span:unknown"


def _build_initial_evidence_links(
    *,
    claims: tuple[Claim, ...],
    items: tuple[dict[str, object], ...],
) -> tuple[ClaimEvidenceLink, ...]:
    evidence_links: list[ClaimEvidenceLink] = []
    for claim, item in zip(claims, items, strict=False):
        evidence_links.extend(_build_initial_evidence_links_for_claim(claim=claim, item=item))
    return tuple(evidence_links)


def _build_initial_evidence_links_for_claim(
    *,
    claim: Claim,
    item: dict[str, object],
) -> tuple[ClaimEvidenceLink, ...]:
    evidence_items = _evidence_items_for(item)
    if not evidence_items:
        return (_build_initial_evidence_link(claim=claim, evidence_payload={}, evidence_rank=1),)
    return tuple(
        _build_initial_evidence_link(
            claim=claim,
            evidence_payload=evidence_payload,
            evidence_rank=index,
        )
        for index, evidence_payload in enumerate(evidence_items, start=1)
    )


def _count_dropped_evidence_items(items: tuple[dict[str, object], ...]) -> int:
    return sum(_dropped_evidence_items_for(item) for item in items)


def _dropped_evidence_items_for(item: dict[str, object]) -> int:
    evidence = _evidence_payload_for(item)
    if isinstance(evidence, dict) or not isinstance(evidence, list):
        return 0
    return len(evidence) - len(_evidence_items_for(item))


def _build_initial_evidence_link(
    *,
    claim: Claim,
    evidence_payload: dict[str, object],
    evidence_rank: int,
) -> ClaimEvidenceLink:
    span_reference = claim.source_span_reference or "chunk-span:unknown"
    return ClaimEvidenceLink(
        claim_id=claim.claim_id,
        document_id=claim.document_id,
        chunk_id=_evidence_chunk_id(evidence_payload, claim=claim),
        evidence_rank=evidence_rank,
        evidence_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=_evidence_rationale(evidence_payload, span_reference=span_reference),
        snippet=_evidence_snippet(evidence_payload, claim=claim),
        score=_evidence_score(evidence_payload),
    )


def _evidence_items_for(item: dict[str, object]) -> tuple[dict[str, object], ...]:
    evidence = _evidence_payload_for(item)
    if isinstance(evidence, dict):
        return (evidence,)
    if not isinstance(evidence, list):
        return ()
    return tuple(entry for entry in evidence if _is_valid_evidence_payload(entry))


def _evidence_payload_for(item: dict[str, object]) -> object:
    for key in _EVIDENCE_KEYS:
        evidence = item.get(key)
        if isinstance(evidence, dict | list):
            return evidence
    return None


def _is_valid_evidence_payload(entry: object) -> bool:
    if not isinstance(entry, dict):
        return False
    return _has_any_normalized_string(
        entry,
        *_EVIDENCE_CHUNK_KEYS,
        *_EVIDENCE_SNIPPET_KEYS,
        *_EVIDENCE_RATIONALE_KEYS,
    ) or isinstance(
        entry.get("score"),
        int | float,
    )


def _evidence_chunk_id(
    evidence_payload: dict[str, object],
    *,
    claim: Claim,
) -> str | None:
    chunk_id = _first_normalized_item_string(evidence_payload, *_EVIDENCE_CHUNK_KEYS)
    if chunk_id is not None:
        return chunk_id
    return claim.chunk_id


def _evidence_rationale(
    evidence_payload: dict[str, object],
    *,
    span_reference: str,
) -> str:
    rationale = _first_normalized_item_string(evidence_payload, *_EVIDENCE_RATIONALE_KEYS)
    if rationale is not None:
        return rationale
    return f"Initial extraction link from chunk {span_reference}."


def _evidence_snippet(
    evidence_payload: dict[str, object],
    *,
    claim: Claim,
) -> str | None:
    snippet = _first_normalized_item_string(evidence_payload, *_EVIDENCE_SNIPPET_KEYS)
    if snippet is not None:
        return snippet
    return _normalized_string(claim.exact_text)


def _evidence_score(evidence_payload: dict[str, object]) -> float | None:
    score = evidence_payload.get("score")
    if isinstance(score, int | float):
        return float(score)
    return None


def build_llm_claim_extractor(
    *,
    extract_claims: "ClaimExtractionGateway",
    normalize_claim: "ClaimNormalizationGateway | None" = None,
    claim_repository: "ClaimRepository | None" = None,
) -> _LlmClaimExtractor:
    """Bind the LLM claim extraction gateway into the application extraction shape."""

    return _LlmClaimExtractor(
        extract_claims=extract_claims,
        normalize_claim=normalize_claim,
        claim_repository=claim_repository,
    )


__all__ = ["build_llm_claim_extractor"]
