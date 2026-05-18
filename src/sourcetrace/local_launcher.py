"""Local launcher that wires runtime_config into the stdlib web server."""

from collections.abc import Callable
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


def build_local_server_runtime(
    *,
    completion_fn: Callable[..., dict[str, Any]] | None = None,
):
    """Build the local web server runtime using the repo-owned runtime config."""

    llm_runtime = build_llm_runtime(
        completion_fn=completion_fn or _missing_litellm_completion,
        config=build_default_llm_config(),
    )
    delivery = create_default_delivery(credibility_draft=llm_runtime.credibility_draft)
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
