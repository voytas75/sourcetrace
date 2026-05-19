"""SourceTrace-owned task routing and bootstrap config for LLM work."""

from dataclasses import dataclass, field
from os import environ

from sourcetrace.llm.errors import LlmConfigurationError


@dataclass(frozen=True)
class LlmBootstrapConfig:
    """Provider-bootstrap inputs kept outside task-level routing config."""

    api_key_env_var: str | None = None
    base_url_env_var: str | None = None
    api_version_env_var: str | None = None

    def env_var_names(self) -> tuple[str, ...]:
        names: list[str] = []
        if self.api_key_env_var is not None:
            names.append(self.api_key_env_var)
        if self.base_url_env_var is not None:
            names.append(self.base_url_env_var)
        if self.api_version_env_var is not None:
            names.append(self.api_version_env_var)
        return tuple(names)


@dataclass(frozen=True)
class ResolvedLlmBootstrapConfig:
    """Resolved bootstrap inputs read from the current process environment."""

    api_key: str | None = None
    base_url: str | None = None
    api_version: str | None = None


def resolve_llm_bootstrap_config(
    bootstrap: LlmBootstrapConfig,
) -> ResolvedLlmBootstrapConfig:
    """Resolve declared bootstrap env-var names against the current process env."""

    api_key = _resolve_required_env_value(
        bootstrap.api_key_env_var,
        field_label="api_key",
    )
    base_url = _resolve_required_env_value(
        bootstrap.base_url_env_var,
        field_label="base_url",
    )
    api_version = _resolve_required_env_value(
        bootstrap.api_version_env_var,
        field_label="api_version",
    )
    return ResolvedLlmBootstrapConfig(
        api_key=api_key,
        base_url=base_url,
        api_version=api_version,
    )


def _resolve_required_env_value(env_var_name: str | None, *, field_label: str) -> str | None:
    if env_var_name is None:
        return None

    value = environ.get(env_var_name)
    if value is None or not value.strip():
        raise LlmConfigurationError(
            f"missing required LLM bootstrap env var for {field_label}: {env_var_name}"
        )
    return value


@dataclass(frozen=True)
class LlmProfileConfig:
    """Logical profile routing defaults resolved separately from task semantics."""

    model: str
    temperature: float | None = None
    max_output_tokens: int | None = None


@dataclass(frozen=True)
class LlmTaskConfig:
    """Task-level logical profile binding."""

    profile: str


@dataclass(frozen=True)
class SourceTraceLlmConfig:
    """Resolved config surface used by the local LLM layer."""

    default_timeout_seconds: float | None = None
    default_max_output_tokens: int | None = None
    bootstrap: LlmBootstrapConfig = field(default_factory=LlmBootstrapConfig)
    profiles: dict[str, LlmProfileConfig] = field(default_factory=dict)
    tasks: dict[str, LlmTaskConfig] = field(default_factory=dict)

    def bootstrap_env_var_names(self) -> tuple[str, ...]:
        """Return the explicit env vars expected from an external launcher/runtime."""

        return self.bootstrap.env_var_names()

    def profile(self, profile_name: str) -> LlmProfileConfig:
        """Return logical profile routing config or raise a normalized config error."""

        profile_config = self.profiles.get(profile_name)
        if profile_config is None:
            raise LlmConfigurationError(f"missing LLM profile config for {profile_name}")

        if (
            profile_config.max_output_tokens is None
            and self.default_max_output_tokens is not None
        ):
            return LlmProfileConfig(
                model=profile_config.model,
                temperature=profile_config.temperature,
                max_output_tokens=self.default_max_output_tokens,
            )
        return profile_config

    def task(self, task_name: str) -> LlmProfileConfig:
        """Return resolved task routing config or raise a normalized config error."""

        task_config = self.tasks.get(task_name)
        if task_config is None:
            raise LlmConfigurationError(f"missing LLM task config for {task_name}")
        return self.profile(task_config.profile)


__all__ = [
    "LlmBootstrapConfig",
    "LlmProfileConfig",
    "LlmTaskConfig",
    "ResolvedLlmBootstrapConfig",
    "SourceTraceLlmConfig",
    "resolve_llm_bootstrap_config",
]
