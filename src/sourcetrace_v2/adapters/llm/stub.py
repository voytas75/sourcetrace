from __future__ import annotations

from sourcetrace_v2.adapters.llm.interfaces import LlmCallResult, LlmTextGateway
from sourcetrace_v2.core.domain.identifiers import DegradationReason, ReceiptCoverageStatus
from sourcetrace_v2.runtime.config.models import RuntimeConfig
from sourcetrace_v2.runtime.config.resolver import resolve_profile


class StubLlmGateway(LlmTextGateway):
    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config

    def generate(self, *, profile_name: str, prompt: str) -> LlmCallResult:
        profile = resolve_profile(self.config, profile_name)
        degraded = "fallback" in prompt.lower()
        return LlmCallResult(
            text=f"stub:{profile_name}:{prompt[:80]}",
            provider=profile.provider,
            model=profile.model,
            input_tokens=32,
            output_tokens=64,
            total_tokens=96,
            finish_reason="stop",
            coverage_status=ReceiptCoverageStatus.TRACKED,
            degradation_reason=DegradationReason.FALLBACK_USED if degraded else None,
        )
