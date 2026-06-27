from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RuntimeProfile:
    name: str
    provider: str
    model: str
    provider_model_id: str | None = None
    mode: str = "text"
    temperature: float = 0.0
    max_output_tokens: int = 800
    timeout_seconds: float = 30.0
    retries: int = 0
    fallbacks: tuple[str, ...] = ()


@dataclass(frozen=True)
class FeaturePolicy:
    planning_profile: str = "planning_default"
    query_refinement_profile: str = "research_fast"
    evidence_judge_profile: str = "judge_strict"
    synthesis_profile: str = "synthesis_default"


@dataclass(frozen=True)
class LoggingPolicy:
    level: str = "INFO"
    format: str = "text"
    redact_sensitive: bool = True
    include_correlation: bool = True
    handlers: tuple[str, ...] = ("console",)


@dataclass(frozen=True)
class RuntimeConfig:
    profiles: dict[str, RuntimeProfile] = field(default_factory=dict)
    deep_research: FeaturePolicy = field(default_factory=FeaturePolicy)
    logging: LoggingPolicy = field(default_factory=LoggingPolicy)
