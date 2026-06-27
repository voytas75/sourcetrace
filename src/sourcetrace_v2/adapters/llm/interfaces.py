from __future__ import annotations

from dataclasses import dataclass

from sourcetrace_v2.core.domain.identifiers import DegradationReason, ReceiptCoverageStatus


@dataclass(frozen=True)
class LlmCallResult:
    text: str
    provider: str
    model: str
    provider_name: str | None = None
    model_name: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    finish_reason: str | None = None
    coverage_status: ReceiptCoverageStatus = ReceiptCoverageStatus.TRACKED
    degradation_reason: DegradationReason | None = None


class LlmTextGateway:
    def generate(self, *, profile_name: str, prompt: str) -> LlmCallResult:
        raise NotImplementedError
