from __future__ import annotations

from sourcetrace_v2.core.contracts.compiled_artifacts import CompiledEvidenceSnapshot, CompiledResearchArtifact
from sourcetrace_v2.core.domain.models import ResearchResultArtifact
from sourcetrace_v2.core.policies.selected_evidence import build_candidate_judgment, decide_selected_evidence


def build_compiled_artifact(*, artifact: ResearchResultArtifact) -> CompiledResearchArtifact:
    decision = decide_selected_evidence(artifact.evidence_candidates, limit=2)
    selected = decision.selected
    selected = tuple(
        CompiledEvidenceSnapshot(
            title=candidate.title,
            url=candidate.url,
            provider=candidate.provider,
            rank=candidate.rank,
            snippet=candidate.snippet,
            judgment=build_candidate_judgment(candidate),
        )
        for candidate in selected
    )
    return CompiledResearchArtifact(
        artifact_id=f"compiled:{artifact.job_id}:{artifact.run_id}",
        job_id=artifact.job_id,
        run_id=artifact.run_id,
        summary=artifact.summary,
        selected_evidence=selected,
        selected_evidence_contract_version=selected[0].judgment.contract_version if selected else None,
    )
