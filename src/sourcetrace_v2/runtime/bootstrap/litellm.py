from __future__ import annotations

from dataclasses import dataclass
from os import environ

from sourcetrace_v2.adapters.llm.litellm_like import LiteLikeBootstrap


@dataclass(frozen=True)
class EnvBootstrapRequest:
    api_key_env: str
    base_url_env: str | None = None
    api_version_env: str | None = None


def resolve_litellm_bootstrap_from_env(request: EnvBootstrapRequest) -> LiteLikeBootstrap:
    api_key = environ.get(request.api_key_env)
    if api_key is None or not api_key.strip():
        raise RuntimeError(f"missing required env var: {request.api_key_env}")
    base_url = environ.get(request.base_url_env) if request.base_url_env is not None else None
    api_version = environ.get(request.api_version_env) if request.api_version_env is not None else None
    return LiteLikeBootstrap(api_key=api_key, base_url=base_url, api_version=api_version)
