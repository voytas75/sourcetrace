from __future__ import annotations

from sourcetrace_v2.core.contracts.compiled_artifacts import CompiledResearchArtifact


def project_compiled_artifact(*, artifact: CompiledResearchArtifact | None) -> dict[str, object]:
    return {
        "present": artifact is not None,
        "artifact_id": artifact.artifact_id if artifact is not None else None,
        "summary": artifact.summary if artifact is not None else None,
        "confidence_note": artifact.confidence_note if artifact is not None else None,
        "selected_evidence_contract_version": artifact.selected_evidence_contract_version if artifact is not None else None,
        "selected_evidence": [
            {
                "title": item.title,
                "url": item.url,
                "provider": item.provider,
                "rank": item.rank,
                "snippet": item.snippet,
                "pdf_context": {
                    "document_scope": item.pdf_context.document_scope,
                    "entity_match_summary": item.pdf_context.entity_match_summary,
                    "key_findings": list(item.pdf_context.key_findings),
                } if item.pdf_context is not None else None,
                "judgment": {
                    "contract_version": item.judgment.contract_version,
                    "authority": {
                        "score": item.judgment.authority.score,
                        "band": item.judgment.authority.band,
                        "signals": list(item.judgment.authority.signals),
                    },
                    "topic_match": {
                        "score": item.judgment.topic_match.score,
                        "band": item.judgment.topic_match.band,
                        "signals": list(item.judgment.topic_match.signals),
                    },
                    "specificity": {
                        "score": item.judgment.specificity.score,
                        "band": item.judgment.specificity.band,
                        "signals": list(item.judgment.specificity.signals),
                    },
                    "answer_fit": {
                        "score": item.judgment.answer_fit.score,
                        "band": item.judgment.answer_fit.band,
                        "signals": list(item.judgment.answer_fit.signals),
                    },
                } if item.judgment is not None else None,
            }
            for item in (artifact.selected_evidence if artifact is not None else ())
        ],
    }
