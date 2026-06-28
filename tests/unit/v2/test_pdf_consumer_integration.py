import json

from sourcetrace_v2.adapters.pdf.interfaces import PdfReadResult
from sourcetrace_v2.app.composition.runtime import RuntimeAssembly
from sourcetrace_v2.app.services.http_api import handle_run_minimal_flow_request
from sourcetrace_v2.runtime.config.defaults import build_default_runtime_config
from sourcetrace_v2.adapters.llm.stub import StubLlmGateway
from sourcetrace_v2.adapters.search.stub import StubSearchGateway
from sourcetrace_v2.adapters.storage.memory import InMemoryReceiptRepository, InMemoryResultArtifactRepository
from sourcetrace_v2.runtime.logging.setup import configure_logging


class _PdfStub:
    def read(self, *, query: str, url: str, title: str, triage_verdict: str) -> PdfReadResult:
        assert triage_verdict == "relevant"
        return PdfReadResult(
            relevant=True,
            confidence=0.93,
            document_scope="NIK official control document",
            entity_match_summary="Szpital Południowy w Warszawie",
            key_findings=("Ustalenie 1", "Ustalenie 2"),
            evidence_pages=(7, 9),
        )


class _PdfSearchStub(StubSearchGateway):
    def search(self, *, job_id: str, run_id: str, query: str, limit: int):
        candidates = super().search(job_id=job_id, run_id=run_id, query=query, limit=limit)
        first = candidates[0]
        pdf_first = type(first)(
            candidate_id=first.candidate_id,
            job_id=first.job_id,
            run_id=first.run_id,
            provider=first.provider,
            query=first.query,
            title="Raport NIK.pdf",
            url="https://example.test/raport.pdf",
            snippet=first.snippet,
            rank=first.rank,
        )
        return (pdf_first, *candidates[1:])


def test_run_http_path_enriches_pdf_candidate_via_pdf_seam() -> None:
    config = build_default_runtime_config()
    runtime = RuntimeAssembly(
        config=config,
        llm=StubLlmGateway(config),
        search=_PdfSearchStub(),
        results=InMemoryResultArtifactRepository(),
        receipts=InMemoryReceiptRepository(),
        logger=configure_logging(config.logging),
        pdf=_PdfStub(),
    )

    response = handle_run_minimal_flow_request(
        job_id="job-pdf-consumer",
        run_id="run-pdf-consumer",
        seed_text="Co ustaliła NIK w sprawie Szpitala Południowego?",
        runtime=runtime,
    )
    payload = json.loads(response.body)

    assert response.status_code == 201
    assert payload["status"] == "found"
    assert payload["evidence_input"]["candidates"][0]["url"] == "https://example.test/raport.pdf"
    assert payload["selected_evidence"]["items"][0]["snippet"].startswith("pdf_scope=NIK official control document")
    assert "Szpital Południowy w Warszawie" in payload["selected_evidence"]["items"][0]["snippet"]
