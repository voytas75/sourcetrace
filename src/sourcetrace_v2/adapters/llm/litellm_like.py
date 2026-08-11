from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

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
    def __init__(self, *, config: RuntimeConfig, completion_fn: Callable[..., dict[str, object]], bootstrap: LiteLikeBootstrap | None = None) -> None:
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
        choices = _object_list(response.get("choices"))
        choice: dict[str, object] = _object_mapping(choices[0]) if choices else {}
        message = _object_mapping(choice.get("message"))
        usage = _object_mapping(response.get("usage"))
        raw_finish_reason = choice.get("finish_reason")
        finish_reason = raw_finish_reason if isinstance(raw_finish_reason, str) else None
        coverage_status = ReceiptCoverageStatus.TRACKED if usage else ReceiptCoverageStatus.PROVIDER_MISSING_USAGE
        degradation_reason = None
        if finish_reason == "length":
            degradation_reason = DegradationReason.VALIDATION_FALLBACK
        return LlmCallResult(
            text=str(message.get("content", "")),
            provider=profile.provider,
            model=profile.model,
            input_tokens=_optional_int(usage.get("prompt_tokens")),
            output_tokens=_optional_int(usage.get("completion_tokens")),
            total_tokens=_optional_int(usage.get("total_tokens")),
            finish_reason=finish_reason,
            coverage_status=coverage_status,
            degradation_reason=degradation_reason,
        )


def _object_mapping(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return {}


def _object_list(value: object) -> list[object]:
    if isinstance(value, list):
        return cast(list[object], value)
    return []


def _optional_int(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None
