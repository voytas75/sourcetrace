"""Local launcher that wires runtime_config into the stdlib web server."""

from collections.abc import Callable
from os import environ
from typing import Any

from sourcetrace.llm import build_llm_runtime
from sourcetrace.runtime_config import build_default_llm_config
from sourcetrace.web.api import run_local_server
from sourcetrace.web.delivery import create_default_delivery


def _missing_litellm_completion(**_: Any) -> dict[str, Any]:
    raise RuntimeError(
        "LiteLLM completion function is not wired yet. "
        "Pass a real LiteLLM-compatible completion callable into build_local_server_runtime()."
    )


def _load_litellm_completion() -> Callable[..., dict[str, Any]] | None:
    try:
        from litellm import completion
    except ImportError:
        return None
    return completion


def _resolve_completion_fn(
    completion_fn: Callable[..., dict[str, Any]] | None,
) -> Callable[..., dict[str, Any]]:
    if completion_fn is not None:
        return completion_fn
    auto_completion_fn = _load_litellm_completion()
    if auto_completion_fn is not None:
        return auto_completion_fn
    raise RuntimeError(
        "LiteLLM is not installed in the local launcher environment. "
        "Install it or pass a real LiteLLM-compatible completion callable into build_local_server_runtime()."
    )


def build_local_server_runtime(
    *,
    completion_fn: Callable[..., dict[str, Any]] | None = None,
):
    """Build the local web server runtime using the repo-owned runtime config."""

    environ.setdefault("LITELLM_LOG", "ERROR")
    llm_runtime = build_llm_runtime(
        completion_fn=_resolve_completion_fn(completion_fn),
        config=build_default_llm_config(),
    )
    delivery = create_default_delivery(
        credibility_draft=llm_runtime.credibility_draft,
        claim_extraction=llm_runtime.claim_extraction,
        claim_normalization=llm_runtime.claim_normalization,
    )
    return run_local_server(delivery=delivery)


def main() -> int:
    runtime = build_local_server_runtime()
    try:
        runtime.server.serve_forever()
        return 0
    except KeyboardInterrupt:
        return 0
    finally:
        runtime.server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["build_local_server_runtime", "main"]
