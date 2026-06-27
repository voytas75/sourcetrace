from sourcetrace_v2.adapters.llm.litellm_like import LiteLikeBootstrap, LiteLikeLlmGateway
from sourcetrace_v2.adapters.llm.stub import StubLlmGateway
from sourcetrace_v2.core.domain.identifiers import DegradationReason, FeatureId, ReceiptCoverageStatus, StageId, StageStatus
from sourcetrace_v2.execution.context.models import ExecutionContext
from sourcetrace_v2.execution.receipts.collector import ReceiptCollector
from sourcetrace_v2.execution.stages.simple import SimpleLlmStage
from sourcetrace_v2.runtime.config.defaults import build_default_runtime_config


def test_stub_stage_can_emit_degraded_completion() -> None:
    config = build_default_runtime_config()
    llm = StubLlmGateway(config)
    collector = ReceiptCollector()
    stage = SimpleLlmStage(profile_name="planning_default", llm=llm)

    result = stage.run(
        context=ExecutionContext(
            job_id="job-1",
            run_id="run-1",
            feature=FeatureId.DEEP_RESEARCH,
            stage_id=StageId.PLANNING,
            call_site="test.degraded",
        ),
        collector=collector,
        input_text="please use fallback",
    )

    assert result.output_text.startswith("stub:")
    assert collector.llm_receipts[0].degradation_reason == DegradationReason.FALLBACK_USED
    assert collector.stage_receipts[-1].status == StageStatus.DEGRADED
    rollup = collector.build_rollup(job_id="job-1", run_id="run-1")
    assert rollup.degraded_calls == 1


def test_litellm_like_gateway_maps_usage_and_missing_usage() -> None:
    config = build_default_runtime_config()

    def completion_with_usage(**_: object) -> dict[str, object]:
        return {
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 22, "total_tokens": 33},
        }

    gateway = LiteLikeLlmGateway(
        config=config,
        completion_fn=completion_with_usage,
        bootstrap=LiteLikeBootstrap(api_key="x"),
    )
    result = gateway.generate(profile_name="planning_default", prompt="hello")
    assert result.total_tokens == 33
    assert result.coverage_status == ReceiptCoverageStatus.TRACKED

    def completion_without_usage(**_: object) -> dict[str, object]:
        return {
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
        }

    gateway_missing = LiteLikeLlmGateway(config=config, completion_fn=completion_without_usage)
    missing = gateway_missing.generate(profile_name="planning_default", prompt="hello")
    assert missing.coverage_status == ReceiptCoverageStatus.PROVIDER_MISSING_USAGE


def test_stage_failure_is_captured_as_failed_stage_receipt() -> None:
    class FailingGateway:
        def generate(self, *, profile_name: str, prompt: str):
            raise RuntimeError("boom")

    collector = ReceiptCollector()
    stage = SimpleLlmStage(profile_name="planning_default", llm=FailingGateway())

    try:
        stage.run(
            context=ExecutionContext(
                job_id="job-2",
                run_id="run-2",
                feature=FeatureId.DEEP_RESEARCH,
                stage_id=StageId.PLANNING,
                call_site="test.failure",
            ),
            collector=collector,
            input_text="hello",
        )
    except RuntimeError as exc:
        assert str(exc) == "boom"
    else:
        raise AssertionError("expected RuntimeError")

    assert collector.stage_receipts[-1].status == StageStatus.FAILED
    rollup = collector.build_rollup(job_id="job-2", run_id="run-2")
    assert rollup.failed_stages == 1


def test_stage_receipt_prefers_execution_truth_over_profile_defaults() -> None:
    class GatewayWithExecutionTruth:
        def generate(self, *, profile_name: str, prompt: str):
            from sourcetrace_v2.adapters.llm.interfaces import LlmCallResult
            return LlmCallResult(
                text="ok",
                provider="azure",
                model="gpt-5.4",
                provider_name="openai-responses",
                model_name="gpt-5.4-mini-real",
                total_tokens=12,
            )

    collector = ReceiptCollector()
    stage = SimpleLlmStage(profile_name="planning_default", llm=GatewayWithExecutionTruth())

    stage.run(
        context=ExecutionContext(
            job_id="job-3",
            run_id="run-3",
            feature=FeatureId.DEEP_RESEARCH,
            stage_id=StageId.PLANNING,
            call_site="test.execution_truth",
        ),
        collector=collector,
        input_text="hello",
    )

    assert collector.llm_receipts[0].provider == "openai-responses"
    assert collector.llm_receipts[0].model == "gpt-5.4-mini-real"
