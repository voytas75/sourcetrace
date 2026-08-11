from sourcetrace.application import PdfIngestResult
from sourcetrace_pdf_runtime.capability import (
    full_prompt,
    openclaw_pdf_capability,
    preview_prompt,
)


def build_native_pdf_ingestor_with_llm(*, llm_judge):
    def ingest(*, query: str, url: str, title: str, triage_verdict: str) -> PdfIngestResult:
        preview = openclaw_pdf_capability(
            pdf=url,
            pages="1-3",
            prompt=preview_prompt(query=query, title=title),
        )
        candidate_pages = tuple(preview.get("candidate_pages") or ()) if isinstance(preview, dict) else ()
        page_spec = "1-5" if not candidate_pages or candidate_pages == (1,) else ",".join(str(page) for page in candidate_pages)
        full = openclaw_pdf_capability(
            pdf=url,
            pages=page_spec,
            prompt=full_prompt(query=query, title=title),
        )
        snippets = tuple(full.get("context_chunks") or full.get("key_findings") or ()) if isinstance(full, dict) else ()
        fallback = PdfIngestResult(
            relevant=bool(full.get("relevant", False)) if isinstance(full, dict) else False,
            confidence=float(full.get("confidence", 0.0)) if isinstance(full, dict) else 0.0,
            document_scope=str(full.get("document_scope", title)) if isinstance(full, dict) else title,
            entity_match_summary=str(full.get("entity_match_summary", title)) if isinstance(full, dict) else title,
            key_findings=tuple(str(item) for item in (full.get("key_findings") or [])[:5]) if isinstance(full, dict) else (),
            evidence_pages=tuple(int(item) for item in (full.get("evidence_pages") or [])[:5]) if isinstance(full, dict) else (),
        )
        debug = llm_judge(
            query=query,
            title=title,
            url=url,
            triage_verdict=triage_verdict,
            snippets=snippets,
            candidate_pages=tuple(int(page) for page in candidate_pages[:5]),
            fallback=fallback,
        )
        ingest.last_debug = debug
        return debug.result

    ingest.last_debug = None
    return ingest
