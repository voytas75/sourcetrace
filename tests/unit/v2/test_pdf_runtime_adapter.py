from sourcetrace.runtime_pdf_ingest import build_research_pdf_analyzer
from sourcetrace_v2.adapters.pdf.runtime_ingest import RuntimePdfReadGateway
from sourcetrace_v2.app.composition.runtime import RuntimeAssembly, build_stubbed_memory_runtime


def test_runtime_pdf_read_gateway_adapts_runtime_pdf_analyzer_to_v2_contract() -> None:
    calls: list[dict[str, object]] = []

    def capability(*, pdf: str, prompt: str, pages: str = "") -> dict[str, object]:
        calls.append({"pdf": pdf, "prompt": prompt, "pages": pages})
        if len(calls) == 1:
            return {
                "document_title": "Doc",
                "main_entity": "Szpital Południowy w Warszawie",
                "document_scope": "NIK kontrola",
                "relevance_verdict": "relevant",
                "reason": "subject found",
                "candidate_pages": [1, 3, 7],
                "confidence": 0.8,
            }
        if 'selected_pages' in prompt:
            return {
                "selected_pages": [7],
                "reason": "findings page",
                "confidence": 0.9,
            }
        return {
            "relevant": True,
            "document_scope": "NIK official control document",
            "entity_match_summary": "Szpital Południowy w Warszawie",
            "key_findings": ["Ustalenie 1"],
            "evidence_pages": [7],
            "confidence": 0.91,
        }

    gateway = RuntimePdfReadGateway(analyzer=build_research_pdf_analyzer(capability))
    result = gateway.read(
        query="Co ustaliła NIK w sprawie Szpitala Południowego?",
        url="https://example.test/doc.pdf",
        title="Raport NIK",
        triage_verdict="relevant",
    )

    assert result.relevant is True
    assert result.document_scope == "NIK official control document"
    assert result.entity_match_summary == "Szpital Południowy w Warszawie"
    assert result.key_findings == ("Ustalenie 1",)
    assert result.evidence_pages == (7,)


def test_runtime_assembly_exposes_optional_pdf_gateway_slot() -> None:
    runtime = build_stubbed_memory_runtime()

    assert isinstance(runtime, RuntimeAssembly)
    assert runtime.pdf is None
