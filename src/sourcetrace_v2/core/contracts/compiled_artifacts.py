from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompiledEvidenceSnapshot:
    title: str
    url: str
    provider: str
    rank: int
    snippet: str = ""


@dataclass(frozen=True)
class CompiledResearchArtifact:
    artifact_id: str
    job_id: str
    run_id: str
    summary: str
    selected_evidence: tuple[CompiledEvidenceSnapshot, ...] = ()
    confidence_note: str = "bounded_v2_compiled_artifact"
