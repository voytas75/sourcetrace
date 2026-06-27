from sourcetrace_v2.app.composition.runtime import build_litellm_like_jsonl_runtime, build_stubbed_jsonl_runtime
from sourcetrace_v2.adapters.llm.litellm_like import LiteLikeBootstrap


def test_build_stubbed_jsonl_runtime_returns_assembled_dependencies(tmp_path) -> None:
    runtime = build_stubbed_jsonl_runtime(base_dir=tmp_path)

    assert runtime.config.deep_research.planning_profile == "planning_default"
    assert runtime.results is not None
    assert runtime.receipts is not None
    assert runtime.llm is not None
    assert runtime.logger is not None


def test_build_litellm_like_jsonl_runtime_returns_real_provider_shaped_assembly(tmp_path) -> None:
    def completion_fn(**_: object) -> dict[str, object]:
        return {
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }

    runtime = build_litellm_like_jsonl_runtime(
        base_dir=tmp_path,
        completion_fn=completion_fn,
        bootstrap=LiteLikeBootstrap(api_key="x"),
    )

    assert runtime.config.deep_research.planning_profile == "planning_default"
    assert runtime.results is not None
    assert runtime.receipts is not None
    assert runtime.llm is not None
    assert runtime.logger is not None
