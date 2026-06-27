import json
from pathlib import Path

from sourcetrace_v2.app.composition.runtime import (
    build_preferred_search_backed_stubbed_jsonl_runtime,
    build_searxng_backed_stubbed_jsonl_runtime,
    build_stubbed_memory_runtime,
)
from sourcetrace_v2.app.services.http_api import (
    handle_get_persisted_compiled_artifact_request,
    handle_run_minimal_flow_request,
)
from sourcetrace_v2.core.contracts.compiled_artifacts import CompiledResearchArtifact
from sourcetrace_v2.core.domain.models import ResearchResultArtifact, RetrievedEvidenceCandidate
from sourcetrace_v2.projections.api.evidence import project_selected_evidence


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "v2" / "eval_corpus_v2.json"


def _load_cases() -> list[dict[str, object]]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_eval_corpus_v2_cases(monkeypatch, tmp_path) -> None:
    def fake_searxng_urlopen(request, timeout=0):
        return _FakeResponse(
            {
                "results": [
                    {"url": "https://example.test/a", "title": "Alpha", "content": "First"},
                    {"url": "https://example.test/b", "title": "Beta", "content": "Second"},
                    {"url": "https://example.test/c", "title": "Gamma", "content": "Third"},
                ]
            }
        )

    monkeypatch.setattr("sourcetrace_v2.adapters.search.searxng.urlopen", fake_searxng_urlopen)

    for case in _load_cases():
        kind = case["kind"]
        if kind == "run_flow":
            runtime_name = case["runtime"]
            if runtime_name == "stubbed_memory":
                runtime = build_stubbed_memory_runtime()
            elif runtime_name == "searxng_stubbed_jsonl":
                runtime = build_searxng_backed_stubbed_jsonl_runtime(
                    base_dir=tmp_path / case["case_id"],
                    base_url="http://127.0.0.1:8080",
                )
            elif runtime_name == "preferred_search_stubbed_jsonl":
                runtime = build_preferred_search_backed_stubbed_jsonl_runtime(
                    base_dir=tmp_path / case["case_id"],
                    base_url="http://127.0.0.1:8080",
                    unified_search_web=lambda query, count=10: [
                        {"url": "https://example.test/u1", "title": "Unified 1", "snippet": "One"},
                        {"url": "https://example.test/u2", "title": "Unified 2", "snippet": "Two"},
                        {"url": "https://example.test/u3", "title": "Unified 3", "snippet": "Three"},
                    ],
                )
            else:  # pragma: no cover
                raise AssertionError(f"unknown runtime in eval corpus: {runtime_name}")

            response = handle_run_minimal_flow_request(
                job_id=case["job_id"],
                run_id=case["run_id"],
                seed_text=case["seed_text"],
                runtime=runtime,
            )
            payload = json.loads(response.body)
            compiled_response = handle_get_persisted_compiled_artifact_request(
                job_id=case["job_id"],
                run_id=case["run_id"],
                runtime=runtime,
            )
            compiled_payload = json.loads(compiled_response.body)
            expect = case["expect"]

            assert payload["status"] == expect["status"]
            assert payload["evidence_input"]["candidate_count"] == expect["evidence_input_candidate_count"]
            assert payload["selected_evidence"]["selected_count"] == expect["selected_evidence_count"]
            assert payload["selected_evidence"]["selection_basis"] == expect["selection_basis"]
            assert payload["compiled_artifact"]["present"] is expect["compiled_artifact_present"]
            assert compiled_payload["status"] == expect["compiled_readback_status"]
            if "top_provider" in expect:
                assert payload["selected_evidence"]["items"][0]["provider"] == expect["top_provider"]

        elif kind == "selected_evidence_only":
            artifact_payload = case["artifact"]
            artifact = ResearchResultArtifact(
                job_id=artifact_payload["job_id"],
                run_id=artifact_payload["run_id"],
                result_text=artifact_payload["result_text"],
                evidence_candidates=tuple(
                    RetrievedEvidenceCandidate(**candidate)
                    for candidate in artifact_payload["evidence_candidates"]
                ),
            )
            payload = project_selected_evidence(artifact=artifact)
            expect = case["expect"]
            assert payload["selected_count"] == expect["selected_evidence_count"]
            assert payload["selection_basis"] == expect["selection_basis"]
            if "first_selected_title" in expect:
                assert payload["items"][0]["title"] == expect["first_selected_title"]
            if "second_selected_title" in expect:
                assert payload["items"][1]["title"] == expect["second_selected_title"]
            assert payload["rejected_reasons"][1]["count"] == expect["missing_minimal_content_dropped"]
            if "domain_diversity_dropped" in expect:
                assert payload["rejected_reasons"][2]["count"] == expect["domain_diversity_dropped"]

        elif kind == "compiled_partial":
            runtime = build_stubbed_memory_runtime()
            runtime.results.save_compiled_artifact(
                CompiledResearchArtifact(
                    artifact_id=f"compiled:{case['job_id']}:{case['run_id']}",
                    job_id=case["job_id"],
                    run_id=case["run_id"],
                    summary="partial compiled",
                )
            )
            response = handle_get_persisted_compiled_artifact_request(
                job_id=case["job_id"],
                run_id=case["run_id"],
                runtime=runtime,
            )
            payload = json.loads(response.body)
            expect = case["expect"]
            assert payload["status"] == expect["status"]
            assert payload["persistence"]["compiled_artifact_present"] is expect["compiled_artifact_present"]
            assert payload["persistence"]["run_artifact_present"] is expect["run_artifact_present"]
            assert payload["persistence"]["marker_present"] is expect["marker_present"]

        else:  # pragma: no cover
            raise AssertionError(f"unknown eval corpus case kind: {kind}")
