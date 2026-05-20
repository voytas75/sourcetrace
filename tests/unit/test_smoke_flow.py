import json

from sourcetrace.smoke_flow import main


def test_smoke_flow_cli_emits_expected_checks(monkeypatch, capsys) -> None:
    responses = [
        {"case_id": "case-1", "status": "ready"},
        {
            "document_id": "doc-1",
            "status": "ready",
            "document": {"has_inline_content": True},
        },
        {"status": "ready", "diagnostics": {"chunk_count": 1}},
        {"status": "ready", "diagnostics": {"claim_count": 2}},
        {"status": "ready", "credibility_assessment": {"summary": "Looks plausible."}},
    ]
    html = "<html><body><strong>Snippet:</strong><div><strong>Summary:</strong></div></body></html>"

    def fake_request_json(base_url: str, method: str, path: str, payload=None):
        assert base_url == "http://127.0.0.1:8000"
        return responses.pop(0)

    def fake_request_text(base_url: str, path: str) -> str:
        assert path == "/cases/case-1"
        return html

    monkeypatch.setattr("sourcetrace.smoke_flow._request_json", fake_request_json)
    monkeypatch.setattr("sourcetrace.smoke_flow._request_text", fake_request_text)

    exit_code = main([])

    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["case_id"] == "case-1"
    assert report["document_id"] == "doc-1"
    assert report["checks"] == {
        "create_case_status": "ready",
        "create_document_status": "ready",
        "document_has_inline_content": True,
        "prepare_status": "ready",
        "prepare_chunk_count": 1,
        "extract_status": "ready",
        "extract_claim_count": 2,
        "credibility_status": "ready",
        "credibility_has_summary": True,
        "html_has_snippet": True,
        "html_has_summary": True,
    }