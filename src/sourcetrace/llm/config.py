"""SourceTrace-owned task routing config for LLM work."""

from dataclasses import dataclass, field

from sourcetrace.llm.errors import LlmConfigurationError


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
    tasks: dict[str, LlmTaskConfig] = field(default_factory=dict)

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
    "LlmTaskConfig",
    "SourceTraceLlmConfig",
]
