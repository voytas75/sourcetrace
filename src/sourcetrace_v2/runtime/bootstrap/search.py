from __future__ import annotations

from dataclasses import dataclass
from os import environ

from sourcetrace_v2.adapters.search.searxng import SearxNGBootstrap


@dataclass(frozen=True)
class SearchEnvBootstrapRequest:
    base_url_env: str
    language_env: str | None = None
    timeout_env: str | None = None


def resolve_searxng_bootstrap_from_env(request: SearchEnvBootstrapRequest) -> SearxNGBootstrap:
    base_url = environ.get(request.base_url_env)
    if base_url is None or not base_url.strip():
        raise RuntimeError(f"missing required env var: {request.base_url_env}")
    language = environ.get(request.language_env).strip() if request.language_env and environ.get(request.language_env) else "en"
    raw_timeout = environ.get(request.timeout_env).strip() if request.timeout_env and environ.get(request.timeout_env) else "10"
    try:
        timeout_seconds = int(raw_timeout)
    except ValueError as exc:
        raise RuntimeError(f"invalid integer env var: {request.timeout_env}") from exc
    return SearxNGBootstrap(base_url=base_url, language=language, timeout_seconds=timeout_seconds)
