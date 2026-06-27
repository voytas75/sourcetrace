from __future__ import annotations

from sourcetrace_v2.core.contracts.compiled_artifacts import CompiledEvidenceSnapshot, CompiledResearchArtifact
from sourcetrace_v2.core.domain.models import ResearchResultArtifact


def build_compiled_artifact(*, artifact: ResearchResultArtifact) -> CompiledResearchArtifact:
    selected = tuple(
        CompiledEvidenceSnapshot(
            title=candidate.title,
            url=candidate.url,
            provider=candidate.provider,
            rank=candidate.rank,
            snippet=candidate.snippet,
        )
        for candidate in sorted(artifact.evidence_candidates, key=lambda candidate: candidate.rank)[:2]
    )
    return CompiledResearchArtifact(
        artifact_id=f"compiled:{artifact.job_id}:{artifact.run_id}",
        job_id=artifact.job_id,
        run_id=artifact.run_id,
        summary=artifact.summary,
        selected_evidence=selected,
    )
