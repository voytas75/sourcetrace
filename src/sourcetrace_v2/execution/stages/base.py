from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sourcetrace_v2.execution.context.models import ExecutionContext
from sourcetrace_v2.execution.receipts.collector import ReceiptCollector


@dataclass(frozen=True)
class StageResult:
    output_text: str


class StageModule(Protocol):
    def run(self, *, context: ExecutionContext, collector: ReceiptCollector, input_text: str) -> StageResult:
        ...
