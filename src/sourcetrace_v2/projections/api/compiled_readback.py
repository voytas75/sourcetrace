from __future__ import annotations

from sourcetrace_v2.core.contracts.compiled_read_models import PersistedCompiledArtifactView
from sourcetrace_v2.projections.api.compiled_artifacts import project_compiled_artifact


def project_persisted_compiled_artifact_view(*, view: PersistedCompiledArtifactView) -> dict[str, object]:
    envelope = view.envelope
    return {
        "status": view.status.value,
        "job_id": envelope.job_id,
        "run_id": envelope.run_id,
        "persistence": {
            "completeness": envelope.persistence_completeness.value,
            "compiled_artifact_present": envelope.compiled_artifact_present,
            "run_artifact_present": envelope.run_artifact_present,
            "marker_present": envelope.marker_present,
            "marker_state": envelope.marker_state,
        },
        "compiled_artifact": project_compiled_artifact(artifact=view.compiled_artifact),
    }
