from sourcetrace_v2.app.composition.runtime import build_stubbed_jsonl_runtime


def test_build_stubbed_jsonl_runtime_returns_assembled_dependencies(tmp_path) -> None:
    runtime = build_stubbed_jsonl_runtime(base_dir=tmp_path)

    assert runtime.config.deep_research.planning_profile == "planning_default"
    assert runtime.results is not None
    assert runtime.receipts is not None
    assert runtime.llm is not None
    assert runtime.logger is not None
