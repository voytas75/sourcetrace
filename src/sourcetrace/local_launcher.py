"""Local launcher that wires runtime_config into the stdlib web server."""

from collections.abc import Callable
from os import environ
from typing import Any

_DEFAULT_WWW_HOST = "127.0.0.1"
_DEFAULT_WWW_PORT = 8000

from sourcetrace.llm.errors import LlmConfigurationError

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


def _mirror_legacy_azure_env() -> None:
    if not environ.get("SOURCETRACE_LLM_API_KEY") and environ.get("AZURE_OPENAI_API_KEY"):
        environ["SOURCETRACE_LLM_API_KEY"] = environ["AZURE_OPENAI_API_KEY"]
    if not environ.get("SOURCETRACE_LLM_BASE_URL") and environ.get("AZURE_OPENAI_BASE_URL"):
        environ["SOURCETRACE_LLM_BASE_URL"] = environ["AZURE_OPENAI_BASE_URL"]
    if not environ.get("SOURCETRACE_LLM_API_VERSION") and environ.get("AZURE_OPENAI_API_VERSION"):
        environ["SOURCETRACE_LLM_API_VERSION"] = environ["AZURE_OPENAI_API_VERSION"]


def _build_runtime_config_with_legacy_env_fallback():
    _mirror_legacy_azure_env()
    try:
        return build_default_llm_config()
    except LlmConfigurationError:
        raise


def _resolve_server_bind() -> tuple[str, int]:
    host = environ.get("SOURCETRACE_WWW_HOST", _DEFAULT_WWW_HOST).strip() or _DEFAULT_WWW_HOST
    raw_port = environ.get("SOURCETRACE_WWW_PORT", str(_DEFAULT_WWW_PORT)).strip() or str(
        _DEFAULT_WWW_PORT
    )
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise ValueError("SOURCETRACE_WWW_PORT must be an integer.") from exc
    return host, port


def build_local_server_runtime(
    *,
    completion_fn: Callable[..., dict[str, Any]] | None = None,
):
    """Build the local web server runtime using the repo-owned runtime config."""

    environ.setdefault("LITELLM_LOG", "ERROR")
    llm_runtime = build_llm_runtime(
        completion_fn=_resolve_completion_fn(completion_fn),
        config=_build_runtime_config_with_legacy_env_fallback(),
    )
    delivery = create_default_delivery(
        credibility_draft=llm_runtime.credibility_draft,
        claim_extraction=llm_runtime.claim_extraction,
        claim_normalization=llm_runtime.claim_normalization,
    )
    host, port = _resolve_server_bind()
    return run_local_server(host=host, port=port, delivery=delivery)


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
