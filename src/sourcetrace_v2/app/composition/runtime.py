from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from sourcetrace_v2.adapters.llm.litellm_like import LiteLikeBootstrap, LiteLikeLlmGateway
from sourcetrace_v2.adapters.llm.stub import StubLlmGateway
from sourcetrace_v2.adapters.storage.memory import InMemoryReceiptRepository, InMemoryResultArtifactRepository
from sourcetrace_v2.adapters.storage.jsonl import JsonlReceiptRepository, JsonlResultArtifactRepository
from sourcetrace_v2.adapters.llm.interfaces import LlmTextGateway
from sourcetrace_v2.core.contracts.persistence import ReceiptRepository, ResultArtifactRepository
from sourcetrace_v2.runtime.config.defaults import build_default_runtime_config
from sourcetrace_v2.runtime.config.models import RuntimeConfig
from sourcetrace_v2.runtime.logging.setup import configure_logging


@dataclass(frozen=True)
class RuntimeAssembly:
    config: RuntimeConfig
    llm: LlmTextGateway
    results: ResultArtifactRepository
    receipts: ReceiptRepository
    logger: logging.Logger


def build_stubbed_memory_runtime() -> RuntimeAssembly:
    config = build_default_runtime_config()
    logger = configure_logging(config.logging)
    llm = StubLlmGateway(config)
    results = InMemoryResultArtifactRepository()
    receipts = InMemoryReceiptRepository()
    return RuntimeAssembly(
        config=config,
        llm=llm,
        results=results,
        receipts=receipts,
        logger=logger,
    )


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


def build_litellm_like_jsonl_runtime(*, base_dir: str | Path, completion_fn: Callable[..., dict[str, Any]], bootstrap: LiteLikeBootstrap | None = None) -> RuntimeAssembly:
    config = build_default_runtime_config()
    logger = configure_logging(config.logging)
    llm = LiteLikeLlmGateway(config=config, completion_fn=completion_fn, bootstrap=bootstrap)
    results = JsonlResultArtifactRepository(base_dir)
    receipts = JsonlReceiptRepository(base_dir)
    return RuntimeAssembly(
        config=config,
        llm=llm,
        results=results,
        receipts=receipts,
        logger=logger,
    )
