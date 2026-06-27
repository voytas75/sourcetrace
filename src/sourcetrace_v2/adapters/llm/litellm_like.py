from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from sourcetrace_v2.adapters.llm.interfaces import LlmCallResult, LlmTextGateway
from sourcetrace_v2.core.domain.identifiers import DegradationReason, ReceiptCoverageStatus
from sourcetrace_v2.runtime.config.models import RuntimeConfig
from sourcetrace_v2.runtime.config.resolver import resolve_profile


@dataclass(frozen=True)
class LiteLikeBootstrap:
    api_key: str | None = None
    base_url: str | None = None
    api_version: str | None = None


class LiteLikeLlmGateway(LlmTextGateway):
    def __init__(self, *, config: RuntimeConfig, completion_fn: Callable[..., dict[str, Any]], bootstrap: LiteLikeBootstrap | None = None) -> None:
        self.config = config
        self.completion_fn = completion_fn
        self.bootstrap = bootstrap or LiteLikeBootstrap()

    def generate(self, *, profile_name: str, prompt: str) -> LlmCallResult:
        profile = resolve_profile(self.config, profile_name)
        completion_model = profile.provider_model_id or profile.model
        if profile.provider == "azure":
            completion_model = f"azure/{completion_model}"
        response = self.completion_fn(
            model=completion_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=profile.temperature,
            max_tokens=profile.max_output_tokens,
            api_key=self.bootstrap.api_key,
            base_url=self.bootstrap.base_url,
            api_version=self.bootstrap.api_version,
        )
        choices = response.get("choices") or []
        message = choices[0].get("message", {}) if choices else {}
        usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
        finish_reason = choices[0].get("finish_reason") if choices else None
        coverage_status = ReceiptCoverageStatus.TRACKED if usage else ReceiptCoverageStatus.PROVIDER_MISSING_USAGE
        degradation_reason = None
        if finish_reason == "length":
            degradation_reason = DegradationReason.VALIDATION_FALLBACK
        return LlmCallResult(
            text=str(message.get("content", "")),
            provider=profile.provider,
            model=profile.model,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
            finish_reason=finish_reason,
            coverage_status=coverage_status,
            degradation_reason=degradation_reason,
        )
