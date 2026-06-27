from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sourcetrace_v2.adapters.llm.stub import StubLlmGateway
from sourcetrace_v2.adapters.storage.jsonl import JsonlReceiptRepository, JsonlResultArtifactRepository
from sourcetrace_v2.core.contracts.persistence import ReceiptRepository, ResultArtifactRepository
from sourcetrace_v2.runtime.config.defaults import build_default_runtime_config
from sourcetrace_v2.runtime.config.models import RuntimeConfig
from sourcetrace_v2.runtime.logging.setup import configure_logging


@dataclass(frozen=True)
class RuntimeAssembly:
    config: RuntimeConfig
    llm: object
    results: ResultArtifactRepository
    receipts: ReceiptRepository
    logger: object


def build_stubbed_jsonl_runtime(*, base_dir: str | Path) -> RuntimeAssembly:
    config = build_default_runtime_config()
    logger = configure_logging(config.logging)
    llm = StubLlmGateway(config)
    results = JsonlResultArtifactRepository(base_dir)
    receipts = JsonlReceiptRepository(base_dir)
    return RuntimeAssembly(
        config=config,
        llm=llm,
        results=results,
        receipts=receipts,
        logger=logger,
    )
