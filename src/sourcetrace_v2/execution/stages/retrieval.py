from __future__ import annotations

from dataclasses import dataclass, replace

from sourcetrace_v2.adapters.pdf.interfaces import PdfReadGateway
from sourcetrace_v2.adapters.search.interfaces import SearchGateway
from sourcetrace_v2.core.domain.identifiers import StageStatus
from sourcetrace_v2.core.domain.models import PdfEvidenceContext, RetrievedEvidenceCandidate, StageExecutionReceipt
from sourcetrace_v2.execution.context.models import ExecutionContext
from sourcetrace_v2.execution.receipts.collector import ReceiptCollector


@dataclass(frozen=True)
class RetrievalStageResult:
    retrieval_query: str
    candidates: tuple[RetrievedEvidenceCandidate, ...]


class RetrievalStage:
    def __init__(self, *, search: SearchGateway, pdf: PdfReadGateway | None = None, limit: int = 3) -> None:
        self.search = search
        self.pdf = pdf
        self.limit = limit

    def run(self, *, context: ExecutionContext, collector: ReceiptCollector, input_text: str) -> RetrievalStageResult:
        collector.append_stage(
            StageExecutionReceipt(
                receipt_id=f"stage:{context.stage_id}:start",
                job_id=context.job_id,
                run_id=context.run_id,
                stage_id=context.stage_id,
                call_site=context.call_site,
                status=StageStatus.STARTED,
                attempt=context.attempt,
                round_number=context.round_number,
            )
        )
        try:
            candidates = self.search.search(
                job_id=context.job_id,
                run_id=context.run_id,
                query=input_text,
                limit=self.limit,
            )
            candidates = self._enrich_pdf_candidates(
                candidates=candidates,
                query=input_text,
            )
        except Exception as exc:
            collector.append_stage(
                StageExecutionReceipt(
                    receipt_id=f"stage:{context.stage_id}:failed",
                    job_id=context.job_id,
                    run_id=context.run_id,
                    stage_id=context.stage_id,
                    call_site=context.call_site,
                    status=StageStatus.FAILED,
                    attempt=context.attempt,
                    round_number=context.round_number,
                    detail=str(exc),
                )
            )
            raise
        collector.append_stage(
            StageExecutionReceipt(
                receipt_id=f"stage:{context.stage_id}:complete",
                job_id=context.job_id,
                run_id=context.run_id,
                stage_id=context.stage_id,
                call_site=context.call_site,
                status=StageStatus.COMPLETED,
                attempt=context.attempt,
                round_number=context.round_number,
                detail=f"candidate_count={len(candidates)}",
            )
        )
        return RetrievalStageResult(retrieval_query=input_text, candidates=candidates)

    def _enrich_pdf_candidates(
        self,
        *,
        candidates: tuple[RetrievedEvidenceCandidate, ...],
        query: str,
    ) -> tuple[RetrievedEvidenceCandidate, ...]:
        if self.pdf is None:
            return candidates
        enriched: list[RetrievedEvidenceCandidate] = []
        for candidate in candidates:
            if not _looks_like_pdf_candidate(candidate):
                enriched.append(candidate)
                continue
            try:
                pdf_result = self.pdf.read(
                    query=query,
                    url=candidate.url,
                    title=candidate.title,
                    triage_verdict="relevant",
                )
            except Exception:
                enriched.append(candidate)
                continue
            if not pdf_result.relevant:
                enriched.append(candidate)
                continue
            snippet_parts = []
            if pdf_result.document_scope:
                snippet_parts.append(f"pdf_scope={pdf_result.document_scope}")
            if pdf_result.entity_match_summary:
                snippet_parts.append(pdf_result.entity_match_summary)
            if pdf_result.key_findings:
                snippet_parts.extend(pdf_result.key_findings[:2])
            snippet = " | ".join(part.strip() for part in snippet_parts if part and part.strip()) or candidate.snippet
            enriched.append(
                replace(
                    candidate,
                    snippet=snippet,
                    pdf_context=PdfEvidenceContext(
                        document_scope=pdf_result.document_scope,
                        entity_match_summary=pdf_result.entity_match_summary,
                        key_findings=tuple(pdf_result.key_findings[:2]),
                    ),
                )
            )
        return tuple(enriched)


def _looks_like_pdf_candidate(candidate: RetrievedEvidenceCandidate) -> bool:
    lowered_url = candidate.url.lower()
    lowered_title = candidate.title.lower()
    return lowered_url.endswith('.pdf') or '/pobierz,' in lowered_url or lowered_title.endswith('.pdf')
