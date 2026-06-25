from sourcetrace.application import PdfIngestResult
from sourcetrace.runtime_pdf_ingest import (
    _coerce_float,
    _coerce_positive_ints,
    _coerce_strings,
    build_research_pdf_analyzer,
    parse_full_evidence_pages,
    parse_full_key_findings,
    parse_full_relevant,
    parse_preview_candidate_pages,
    parse_preview_confidence,
    parse_preview_relevance,
)


def test_coerce_float_clamps_values() -> None:
    assert _coerce_float(1.5) == 1.0
    assert _coerce_float(-0.2) == 0.0
    assert _coerce_float("0.7") == 0.7


def test_coerce_positive_ints_filters_invalid_values() -> None:
    assert _coerce_positive_ints([1, "2", -1, "x", 0], limit=10) == [1, 2]


def test_coerce_strings_strips_empty_values() -> None:
    assert _coerce_strings([" a ", "", None, "b"], limit=10) == ["a", "b"]


def test_parse_preview_relevance_accepts_known_values() -> None:
    assert parse_preview_relevance({"relevance_verdict": "relevant"}) == "relevant"
    assert parse_preview_relevance({"relevance_verdict": "uncertain"}) == "uncertain"
    assert parse_preview_relevance({"relevance_verdict": "irrelevant"}) == "irrelevant"


def test_parse_preview_relevance_defaults_to_irrelevant() -> None:
    assert parse_preview_relevance({"relevance_verdict": "unknown"}) == "irrelevant"


def test_parse_preview_candidate_pages_parses_safely() -> None:
    assert parse_preview_candidate_pages({"candidate_pages": [1, "2", "x", -1]}) == [1, 2]


def test_parse_preview_confidence_clamps() -> None:
    assert parse_preview_confidence({"confidence": 3}) == 1.0


def test_parse_full_relevant_reads_bool() -> None:
    assert parse_full_relevant({"relevant": True}) is True


def test_parse_full_key_findings_limits_output() -> None:
    findings = ["a", "b", "c", "d", "e", "f"]
    assert parse_full_key_findings({"key_findings": findings}) == ["a", "b", "c", "d", "e"]


def test_parse_full_evidence_pages_filters_values() -> None:
    assert parse_full_evidence_pages({"evidence_pages": [3, "4", 0, "x"]}) == [3, 4]


def test_research_pdf_analyzer_blocks_irrelevant_triage() -> None:
    analyzer = build_research_pdf_analyzer(lambda **_: {"ignored": True})

    result = analyzer(
        query="Q",
        url="https://example.test/doc.pdf",
        title="Doc",
        triage_verdict="irrelevant",
    )

    assert result == PdfIngestResult(
        relevant=False,
        confidence=0.0,
        document_scope="triage_blocked",
        entity_match_summary="Skipped because triage verdict was not positive.",
        key_findings=(),
        evidence_pages=(),
    )


def test_research_pdf_analyzer_stops_after_irrelevant_preview() -> None:
    calls = []

    def capability(**kwargs):
        calls.append(kwargs)
        return {
            "document_title": "Doc",
            "main_entity": "Other entity",
            "document_scope": "Preview scope",
            "relevance_verdict": "irrelevant",
            "reason": "No match",
            "candidate_pages": [1],
            "confidence": 0.81,
        }

    analyzer = build_research_pdf_analyzer(capability)
    result = analyzer(
        query="Q",
        url="https://example.test/doc.pdf",
        title="Doc",
        triage_verdict="relevant",
    )

    assert len(calls) == 1
    assert result.relevant is False
    assert result.document_scope == "Preview scope"
    assert result.evidence_pages == (1,)


def test_research_pdf_analyzer_runs_full_after_positive_preview() -> None:
    calls = []

    def capability(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return {
                "document_title": "Doc",
                "main_entity": "Szpital Południowy",
                "document_scope": "Preview scope",
                "relevance_verdict": "relevant",
                "reason": "Looks relevant",
                "candidate_pages": [3, 4],
                "confidence": 0.7,
            }
        return {
            "relevant": True,
            "document_scope": "NIK control document",
            "entity_match_summary": "Szpital Południowy w Warszawie",
            "key_findings": ["Finding 1", "Finding 2"],
            "evidence_pages": [3, 4],
            "confidence": 0.92,
        }

    analyzer = build_research_pdf_analyzer(capability)
    result = analyzer(
        query="Q",
        url="https://example.test/doc.pdf",
        title="Doc",
        triage_verdict="relevant",
    )

    assert len(calls) == 2
    assert result.relevant is True
    assert result.document_scope == "NIK control document"
    assert result.entity_match_summary == "Szpital Południowy w Warszawie"
    assert result.key_findings == ("Finding 1", "Finding 2")
    assert result.evidence_pages == (3, 4)
    assert result.confidence == 0.92


def test_research_pdf_analyzer_handles_full_read_failure_conservatively() -> None:
    calls = []

    def capability(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return {
                "document_title": "Doc",
                "main_entity": "Szpital Południowy",
                "document_scope": "Preview scope",
                "relevance_verdict": "relevant",
                "reason": "Looks relevant",
                "candidate_pages": [3, 4],
                "confidence": 0.7,
            }
        raise RuntimeError("boom")

    analyzer = build_research_pdf_analyzer(capability)
    result = analyzer(
        query="Q",
        url="https://example.test/doc.pdf",
        title="Doc",
        triage_verdict="relevant",
    )

    assert result.relevant is False
    assert result.document_scope == "Preview scope"
    assert "Full read failed" in result.entity_match_summary


def test_research_pdf_analyzer_handles_invalid_preview_json() -> None:
    analyzer = build_research_pdf_analyzer(lambda **_: [])

    result = analyzer(
        query="Q",
        url="https://example.test/doc.pdf",
        title="Doc",
        triage_verdict="relevant",
    )

    assert result.relevant is False
    assert result.document_scope == "preview_invalid"


def test_research_pdf_analyzer_handles_invalid_full_json() -> None:
    calls = []

    def capability(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return {
                "document_title": "Doc",
                "main_entity": "Szpital Południowy",
                "document_scope": "Preview scope",
                "relevance_verdict": "relevant",
                "reason": "Looks relevant",
                "candidate_pages": [3, 4],
                "confidence": 0.7,
            }
        return []

    analyzer = build_research_pdf_analyzer(capability)
    result = analyzer(
        query="Q",
        url="https://example.test/doc.pdf",
        title="Doc",
        triage_verdict="relevant",
    )

    assert result.relevant is False
    assert result.document_scope == "Preview scope"
