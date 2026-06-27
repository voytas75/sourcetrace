from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from sourcetrace_v2.adapters.llm.litellm_like import LiteLikeBootstrap, LiteLikeLlmGateway
from sourcetrace_v2.adapters.llm.stub import StubLlmGateway
from sourcetrace_v2.adapters.search.interfaces import SearchGateway
from sourcetrace_v2.adapters.search.searxng import SearxNGBootstrap, SearxNGSearchGateway
from sourcetrace_v2.adapters.search.stub import StubSearchGateway
from sourcetrace_v2.adapters.storage.memory import InMemoryReceiptRepository, InMemoryResultArtifactRepository
from sourcetrace_v2.adapters.storage.jsonl import JsonlReceiptRepository, JsonlResultArtifactRepository
from sourcetrace_v2.adapters.llm.interfaces import LlmTextGateway
from sourcetrace_v2.core.contracts.persistence import ReceiptRepository, ResultArtifactRepository
from sourcetrace_v2.runtime.config.defaults import build_default_runtime_config
from sourcetrace_v2.runtime.config.models import RuntimeConfig
from sourcetrace_v2.runtime.logging.setup import configure_logging
from sourcetrace_v2.runtime.bootstrap.litellm import EnvBootstrapRequest, resolve_litellm_bootstrap_from_env
from sourcetrace_v2.runtime.bootstrap.search import SearchEnvBootstrapRequest, resolve_searxng_bootstrap_from_env


@dataclass(frozen=True)
class RuntimeAssembly:
    config: RuntimeConfig
    llm: LlmTextGateway
    search: SearchGateway
    results: ResultArtifactRepository
    receipts: ReceiptRepository
    logger: logging.Logger


def build_stubbed_memory_runtime() -> RuntimeAssembly:
    config = build_default_runtime_config()
    logger = configure_logging(config.logging)
    llm = StubLlmGateway(config)
    search = StubSearchGateway()
    results = InMemoryResultArtifactRepository()
    receipts = InMemoryReceiptRepository()
    return RuntimeAssembly(
        config=config,
        llm=llm,
        search=search,
        results=results,
        receipts=receipts,
        logger=logger,
    )


def build_stubbed_jsonl_runtime(*, base_dir: str | Path) -> RuntimeAssembly:
    config = build_default_runtime_config()
    logger = configure_logging(config.logging)
    llm = StubLlmGateway(config)
    search = StubSearchGateway()
    results = JsonlResultArtifactRepository(base_dir)
    receipts = JsonlReceiptRepository(base_dir)
    return RuntimeAssembly(
        config=config,
        llm=llm,
        search=search,
        results=results,
        receipts=receipts,
        logger=logger,
    )


def build_litellm_like_jsonl_runtime(*, base_dir: str | Path, completion_fn: Callable[..., dict[str, Any]], bootstrap: LiteLikeBootstrap | None = None) -> RuntimeAssembly:
    config = build_default_runtime_config()
    logger = configure_logging(config.logging)
    llm = LiteLikeLlmGateway(config=config, completion_fn=completion_fn, bootstrap=bootstrap)
    search = StubSearchGateway()
    results = JsonlResultArtifactRepository(base_dir)
    receipts = JsonlReceiptRepository(base_dir)
    return RuntimeAssembly(
        config=config,
        llm=llm,
        search=search,
        results=results,
        receipts=receipts,
        logger=logger,
    )


def build_env_backed_litellm_like_jsonl_runtime(*, base_dir: str | Path, completion_fn: Callable[..., dict[str, Any]], api_key_env: str, base_url_env: str | None = None, api_version_env: str | None = None) -> RuntimeAssembly:
    bootstrap = resolve_litellm_bootstrap_from_env(
        EnvBootstrapRequest(
            api_key_env=api_key_env,
            base_url_env=base_url_env,
            api_version_env=api_version_env,
        )
    )
    return build_litellm_like_jsonl_runtime(
        base_dir=base_dir,
        completion_fn=completion_fn,
        bootstrap=bootstrap,
    )


def build_searxng_backed_stubbed_jsonl_runtime(*, base_dir: str | Path, base_url: str, language: str = "en", timeout_seconds: int = 10) -> RuntimeAssembly:
    config = build_default_runtime_config()
    logger = configure_logging(config.logging)
    llm = StubLlmGateway(config)
    search = SearxNGSearchGateway(
        bootstrap=SearxNGBootstrap(
            base_url=base_url,
            language=language,
            timeout_seconds=timeout_seconds,
        )
    )
    results = JsonlResultArtifactRepository(base_dir)
    receipts = JsonlReceiptRepository(base_dir)
    return RuntimeAssembly(
        config=config,
        llm=llm,
        search=search,
        results=results,
        receipts=receipts,
        logger=logger,
    )


def build_env_backed_searxng_stubbed_jsonl_runtime(*, base_dir: str | Path, base_url_env: str, language_env: str | None = None, timeout_env: str | None = None) -> RuntimeAssembly:
    config = build_default_runtime_config()
    logger = configure_logging(config.logging)
    llm = StubLlmGateway(config)
    search = SearxNGSearchGateway(
        bootstrap=resolve_searxng_bootstrap_from_env(
            SearchEnvBootstrapRequest(
                base_url_env=base_url_env,
                language_env=language_env,
                timeout_env=timeout_env,
            )
        )
    )
    results = JsonlResultArtifactRepository(base_dir)
    receipts = JsonlReceiptRepository(base_dir)
    return RuntimeAssembly(
        config=config,
        llm=llm,
        search=search,
        results=results,
        receipts=receipts,
        logger=logger,
    )
