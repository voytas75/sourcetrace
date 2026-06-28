from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceJudgmentDimension:
    score: int
    band: str
    signals: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidenceJudgmentSnapshot:
    contract_version: str
    authority: EvidenceJudgmentDimension
    topic_match: EvidenceJudgmentDimension
    specificity: EvidenceJudgmentDimension
    answer_fit: EvidenceJudgmentDimension


@dataclass(frozen=True)
class CompiledEvidenceSnapshot:
    title: str
    url: str
    provider: str
    rank: int
    snippet: str = ""
    judgment: EvidenceJudgmentSnapshot | None = None


@dataclass(frozen=True)
class CompiledResearchArtifact:
    artifact_id: str
    job_id: str
    run_id: str
    summary: str
    selected_evidence: tuple[CompiledEvidenceSnapshot, ...] = ()
    selected_evidence_contract_version: str | None = None
    confidence_note: str = "bounded_v2_compiled_artifact"
