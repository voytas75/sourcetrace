"""SourceTrace-owned task routing and bootstrap config for LLM work."""

from dataclasses import dataclass, field

from sourcetrace.llm.errors import LlmConfigurationError


@dataclass(frozen=True)
class LlmBootstrapConfig:
    """Provider-bootstrap inputs kept outside task-level routing config."""

    api_key_env_var: str | None = None
    base_url_env_var: str | None = None

    def env_var_names(self) -> tuple[str, ...]:
        names: list[str] = []
        if self.api_key_env_var is not None:
            names.append(self.api_key_env_var)
        if self.base_url_env_var is not None:
            names.append(self.base_url_env_var)
        return tuple(names)


@dataclass(frozen=True)
class LlmTaskConfig:
    """Task-level provider-neutral routing defaults."""

    model: str
    temperature: float | None = None
    max_output_tokens: int | None = None


@dataclass(frozen=True)
class SourceTraceLlmConfig:
    """Resolved config surface used by the local LLM layer."""

    default_timeout_seconds: float | None = None
    default_max_output_tokens: int | None = None
    bootstrap: LlmBootstrapConfig = field(default_factory=LlmBootstrapConfig)
    tasks: dict[str, LlmTaskConfig] = field(default_factory=dict)

    def bootstrap_env_var_names(self) -> tuple[str, ...]:
        """Return the explicit env vars expected from an external launcher/runtime."""

        return self.bootstrap.env_var_names()

    def task(self, task_name: str) -> LlmTaskConfig:
        """Return task routing config or raise a normalized config error."""

        task_config = self.tasks.get(task_name)
        if task_config is None:
            raise LlmConfigurationError(f"missing LLM task config for {task_name}")

        if (
            task_config.max_output_tokens is None
            and self.default_max_output_tokens is not None
        ):
            return LlmTaskConfig(
                model=task_config.model,
                temperature=task_config.temperature,
                max_output_tokens=self.default_max_output_tokens,
            )
        return task_config


__all__ = [
    "LlmBootstrapConfig",
    "LlmTaskConfig",
    "SourceTraceLlmConfig",
]
