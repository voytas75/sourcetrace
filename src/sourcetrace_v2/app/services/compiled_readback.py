from __future__ import annotations

from sourcetrace_v2.core.contracts.compiled_read_models import (
    CompiledArtifactViewStatus,
    PersistedCompiledArtifactEnvelope,
    PersistedCompiledArtifactView,
)
from sourcetrace_v2.core.contracts.persistence import ResultArtifactRepository
from sourcetrace_v2.core.contracts.read_models import PersistenceCompleteness


def load_persisted_compiled_artifact_view(*, job_id: str, run_id: str, results: ResultArtifactRepository) -> PersistedCompiledArtifactView:
    compiled_artifact = results.get_compiled_artifact(job_id=job_id, run_id=run_id)
    artifact = results.get_result(job_id=job_id, run_id=run_id)
    marker = results.get_run_marker(job_id=job_id, run_id=run_id)

    if compiled_artifact is None and artifact is None and marker is None:
        status = CompiledArtifactViewStatus.NOT_FOUND
        completeness = PersistenceCompleteness.ABSENT
    elif compiled_artifact is not None and artifact is not None and marker is not None:
        status = CompiledArtifactViewStatus.FOUND
        completeness = PersistenceCompleteness.COMPLETE
    else:
        status = CompiledArtifactViewStatus.INCOMPLETE
        completeness = PersistenceCompleteness.PARTIAL

    envelope = PersistedCompiledArtifactEnvelope(
        job_id=job_id,
        run_id=run_id,
        status=status,
        persistence_completeness=completeness,
        compiled_artifact_present=compiled_artifact is not None,
        run_artifact_present=artifact is not None,
        marker_present=marker is not None,
        marker_state=marker.status if marker is not None else None,
    )
    return PersistedCompiledArtifactView(
        status=status,
        envelope=envelope,
        compiled_artifact=compiled_artifact,
    )
