from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sourcetrace_v2.core.contracts.compiled_artifacts import CompiledResearchArtifact
from sourcetrace_v2.core.contracts.read_models import PersistenceCompleteness


class CompiledArtifactViewStatus(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True)
class PersistedCompiledArtifactEnvelope:
    job_id: str
    run_id: str
    status: CompiledArtifactViewStatus
    persistence_completeness: PersistenceCompleteness
    compiled_artifact_present: bool
    run_artifact_present: bool
    marker_present: bool
    marker_state: str | None


@dataclass(frozen=True)
class PersistedCompiledArtifactView:
    status: CompiledArtifactViewStatus
    envelope: PersistedCompiledArtifactEnvelope
    compiled_artifact: CompiledResearchArtifact | None
