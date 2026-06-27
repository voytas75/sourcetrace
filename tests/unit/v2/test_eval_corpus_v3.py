import json
from pathlib import Path

from sourcetrace_v2.app.composition.runtime import (
    build_preferred_search_backed_stubbed_jsonl_runtime,
    build_searxng_backed_stubbed_jsonl_runtime,
)
from sourcetrace_v2.app.services.http_api import handle_run_minimal_flow_request
from sourcetrace_v2.core.domain.models import ResearchResultArtifact, RetrievedEvidenceCandidate
from sourcetrace_v2.projections.api.evidence import project_selected_evidence


FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "v2" / "eval_corpus_v3.json"


def _load_cases() -> list[dict[str, object]]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_eval_corpus_v3_cases(tmp_path) -> None:
    for case in _load_cases():
        kind = case["kind"]
        if kind == "run_flow":
            if case["runtime"] == "preferred_search_stubbed_jsonl":
                runtime = build_preferred_search_backed_stubbed_jsonl_runtime(
                    base_dir=tmp_path / case["case_id"],
                    base_url="http://127.0.0.1:8080",
                    unified_search_web=lambda query, count=10, results=case["search_results"]: results,
                )
            elif case["runtime"] == "searxng_stubbed_jsonl":
                class _FakeResponse:
                    def __init__(self, payload: dict[str, object]) -> None:
                        self.payload = payload

                    def read(self) -> bytes:
                        return json.dumps(self.payload).encode("utf-8")

                    def __enter__(self):
                        return self

                    def __exit__(self, exc_type, exc, tb) -> None:
                        return None

                import sourcetrace_v2.adapters.search.searxng as searxng_module

                def fake_urlopen(request, timeout=0, results=case["search_results"]):
                    return _FakeResponse({"results": results})

                original = searxng_module.urlopen
                searxng_module.urlopen = fake_urlopen
                try:
                    runtime = build_searxng_backed_stubbed_jsonl_runtime(
                        base_dir=tmp_path / case["case_id"],
                        base_url="http://127.0.0.1:8080",
                    )
                    response = handle_run_minimal_flow_request(
                        job_id=case["job_id"],
                        run_id=case["run_id"],
                        seed_text=case["seed_text"],
                        runtime=runtime,
                    )
                finally:
                    searxng_module.urlopen = original
                payload = json.loads(response.body)
                expect = case["expect"]
                assert payload["status"] == expect["status"]
                assert payload["selected_evidence"]["selected_count"] == expect["selected_evidence_count"]
                assert payload["selected_evidence"]["selection_basis"] == expect["selection_basis"]
                assert payload["selected_evidence"]["items"][0]["provider"] == expect["top_provider"]
                continue
            else:
                raise AssertionError(f"unknown runtime for eval corpus v3: {case['runtime']}")

            response = handle_run_minimal_flow_request(
                job_id=case["job_id"],
                run_id=case["run_id"],
                seed_text=case["seed_text"],
                runtime=runtime,
            )
            payload = json.loads(response.body)
            expect = case["expect"]
            assert payload["status"] == expect["status"]
            assert payload["selected_evidence"]["selected_count"] == expect["selected_evidence_count"]
            assert payload["selected_evidence"]["selection_basis"] == expect["selection_basis"]
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
            assert payload["items"][0]["title"] == expect["first_selected_title"]
            assert payload["items"][1]["title"] == expect["second_selected_title"]
            assert payload["rejected_reasons"][1]["count"] == expect["missing_minimal_content_dropped"]
            assert payload["rejected_reasons"][2]["count"] == expect["domain_diversity_dropped"]

        else:
            raise AssertionError(f"unknown eval corpus v3 case kind: {kind}")
