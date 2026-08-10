from __future__ import annotations

from sourcetrace_v2.core.contracts.compiled_artifacts import (
    CompiledEvidenceSnapshot,
    CompiledResearchArtifact,
    PdfEvidenceContextSnapshot,
)
from sourcetrace_v2.core.domain.models import ResearchResultArtifact
from sourcetrace_v2.core.policies.selected_evidence import (
    build_candidate_judgment,
    decide_selected_evidence,
)


def build_compiled_artifact(
    *, artifact: ResearchResultArtifact
) -> CompiledResearchArtifact:
    decision = decide_selected_evidence(artifact.evidence_candidates, limit=2)
    selected_with_judgments = tuple(
        (candidate, build_candidate_judgment(candidate))
        for candidate in decision.selected
    )
    selected = tuple(
        CompiledEvidenceSnapshot(
            title=candidate.title,
            url=candidate.url,
            provider=candidate.provider,
            rank=candidate.rank,
            snippet=candidate.snippet,
            judgment=judgment,
            pdf_context=(
                PdfEvidenceContextSnapshot(
                    document_scope=candidate.pdf_context.document_scope,
                    entity_match_summary=candidate.pdf_context.entity_match_summary,
                    key_findings=candidate.pdf_context.key_findings,
                )
                if candidate.pdf_context is not None
                else None
            ),
            trust_metadata=candidate.trust_metadata,
        )
        for candidate, judgment in selected_with_judgments
    )
    return CompiledResearchArtifact(
        artifact_id=f"compiled:{artifact.job_id}:{artifact.run_id}",
        job_id=artifact.job_id,
        run_id=artifact.run_id,
        summary=artifact.summary,
        selected_evidence=selected,
        selected_evidence_contract_version=(
            selected_with_judgments[0][1].contract_version
            if selected_with_judgments
            else None
        ),
    )
