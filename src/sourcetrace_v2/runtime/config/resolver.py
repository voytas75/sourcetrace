from __future__ import annotations

from sourcetrace_v2.runtime.config.models import RuntimeConfig, RuntimeProfile


class RuntimeProfileNotFoundError(KeyError):
    pass


def resolve_profile(config: RuntimeConfig, profile_name: str) -> RuntimeProfile:
    try:
        return config.profiles[profile_name]
    except KeyError as exc:
        raise RuntimeProfileNotFoundError(profile_name) from exc
