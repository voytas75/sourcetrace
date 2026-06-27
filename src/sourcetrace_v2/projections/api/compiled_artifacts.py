from __future__ import annotations

from sourcetrace_v2.core.contracts.compiled_artifacts import CompiledResearchArtifact


def project_compiled_artifact(*, artifact: CompiledResearchArtifact | None) -> dict[str, object]:
    return {
        "present": artifact is not None,
        "artifact_id": artifact.artifact_id if artifact is not None else None,
        "summary": artifact.summary if artifact is not None else None,
        "confidence_note": artifact.confidence_note if artifact is not None else None,
        "selected_evidence": [
            {
                "title": item.title,
                "url": item.url,
                "provider": item.provider,
                "rank": item.rank,
                "snippet": item.snippet,
            }
            for item in (artifact.selected_evidence if artifact is not None else ())
        ],
    }
