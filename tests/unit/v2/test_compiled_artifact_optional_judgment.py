from typing import cast

from sourcetrace_v2.core.contracts.compiled_artifacts import (
    CompiledEvidenceSnapshot,
    CompiledResearchArtifact,
)
from sourcetrace_v2.projections.api.compiled_artifacts import project_compiled_artifact


def test_compiled_artifact_without_judgment_projects_null_contract_fields() -> None:
    artifact = CompiledResearchArtifact(
        artifact_id="compiled:job-optional-judgment:run-optional-judgment",
        job_id="job-optional-judgment",
        run_id="run-optional-judgment",
        summary="persisted snapshot without judgment",
        selected_evidence=(CompiledEvidenceSnapshot("legacy", "url", "fixture", 1),),
    )
    payload = project_compiled_artifact(artifact=artifact)
    selected_evidence = cast(list[dict[str, object]], payload["selected_evidence"])

    assert payload["selected_evidence_contract_version"] is None
    assert selected_evidence[0]["judgment"] is None
