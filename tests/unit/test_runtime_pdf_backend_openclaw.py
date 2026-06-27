from sourcetrace.runtime_pdf_backend_openclaw import (
    build_native_pdf_ingestor_with_llm,
    _PageText,
    _extract_toc_candidate_pages,
    _section_snippet_candidates,
)


def test_section_snippet_candidates_prefers_substantive_section_blocks() -> None:
    pages = [
        _PageText(
            page_number=3,
            text=(
                "Spis treści\n"
                "Ocena ogólna\n"
                "Kontrola wykazała istotne nieprawidłowości w realizacji uchwał antysmogowych, "
                "a działania gmin były niewystarczające i opóźnione. "
                "Ustalono także braki w egzekwowaniu obowiązków wymiany źródeł ciepła.\n"
                "Wnioski\n"
                "NIK zaleca wzmocnienie nadzoru oraz lepsze monitorowanie efektów programu.\n"
            ),
        )
    ]

    snippets = _section_snippet_candidates(pages, {"antysmog", "uchwal", "gmin", "wymian"}, limit=5)

    assert snippets
    assert snippets[0].startswith("Ocena ogólna:")
    assert "nieprawidłowości" in snippets[0]


def test_extract_toc_candidate_pages_prefers_substantive_sections() -> None:
    pages = [
        _PageText(
            page_number=1,
            text=(
                "SPIS TREŚCI\n"
                "1. Wprowadzenie....................................................6\n"
                "2. Ocena ogólna..................................................11\n"
                "3. Synteza........................................................13\n"
                "4. Wnioski.......................................................18\n"
                "5. Ważniejsze wyniki kontroli....................................19\n"
            ),
        )
    ]

    assert _extract_toc_candidate_pages(pages)[:4] == [11, 12, 18, 19]


def test_native_pdf_ingestor_reads_preview_across_first_three_pages(monkeypatch) -> None:
    calls = []

    def fake_capability(*, pdf: str, prompt: str, pages: str = "") -> dict[str, object]:
        calls.append(pages)
        if pages == "1-3":
            return {
                "document_title": "Doc",
                "main_entity": "Entity",
                "document_scope": "Scope",
                "relevance_verdict": "relevant",
                "reason": "ok",
                "candidate_pages": [11, 12, 18, 19],
                "confidence": 0.5,
            }
        return {
            "relevant": True,
            "document_scope": "Scope",
            "entity_match_summary": "Entity",
            "key_findings": ["Ocena ogólna: test"],
            "evidence_pages": [11, 12],
            "confidence": 0.75,
        }

    def fake_judge(**kwargs):
        class _Debug:
            fallback_used = True
            raw_text = ""
            parsed_json = None
            snippets = kwargs["snippets"]
            candidate_pages = kwargs["candidate_pages"]
            result = kwargs["fallback"]
        return _Debug()

    monkeypatch.setattr(
        "sourcetrace.runtime_pdf_backend_openclaw.openclaw_pdf_capability",
        fake_capability,
    )

    ingest = build_native_pdf_ingestor_with_llm(llm_judge=fake_judge)
    result = ingest(query="Q", url="https://example.test/doc.pdf", title="Doc", triage_verdict="relevant")

    assert calls[0] == "1-3"
    assert calls[1] == "11,12,18,19"
    assert result.confidence == 0.75


def test_native_pdf_ingestor_prefers_context_chunks_over_thin_findings(monkeypatch) -> None:
    def fake_capability(*, pdf: str, prompt: str, pages: str = "") -> dict[str, object]:
        if pages == "1-3":
            return {
                "document_title": "Doc",
                "main_entity": "Entity",
                "document_scope": "Scope",
                "relevance_verdict": "relevant",
                "reason": "ok",
                "candidate_pages": [11, 12],
                "confidence": 0.5,
            }
        return {
            "relevant": True,
            "document_scope": "Scope",
            "entity_match_summary": "Entity",
            "key_findings": ["thin finding"],
            "context_chunks": ["[page 11] longer substantive context", "[page 12] another chunk"],
            "evidence_pages": [11, 12],
            "confidence": 0.75,
        }

    captured = {}

    def fake_judge(**kwargs):
        captured['snippets'] = kwargs['snippets']
        class _Debug:
            fallback_used = True
            raw_text = ""
            parsed_json = None
            snippets = kwargs["snippets"]
            candidate_pages = kwargs["candidate_pages"]
            result = kwargs["fallback"]
        return _Debug()

    monkeypatch.setattr(
        "sourcetrace.runtime_pdf_backend_openclaw.openclaw_pdf_capability",
        fake_capability,
    )

    ingest = build_native_pdf_ingestor_with_llm(llm_judge=fake_judge)
    ingest(query="Q", url="https://example.test/doc.pdf", title="Doc", triage_verdict="relevant")

    assert captured['snippets'] == ("[page 11] longer substantive context", "[page 12] another chunk")
