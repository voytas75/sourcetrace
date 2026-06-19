"""Filesystem-backed persistence adapters for durable Deep Research state."""

import json
from dataclasses import asdict
from pathlib import Path

from sourcetrace.domain.research import (
    ResearchCompletionMode,
    ResearchFinding,
    ResearchJob,
    ResearchJobStatus,
    ResearchPhase,
    ResearchProgressEvent,
    ResearchResultArtifact,
    ResearchSettings,
    ResearchSource,
    ResearchStats,
)
from sourcetrace.storage.research import (
    InMemoryResearchJobRepository,
    InMemoryResearchProgressEventStore,
    InMemoryResearchResultRepository,
)
from sourcetrace.storage.interfaces import ResearchPersistence


class FileBackedResearchJobRepository(InMemoryResearchJobRepository):
    """Job repository with JSON persistence under a local research root."""

    def __init__(self, root_dir: str | Path) -> None:
        super().__init__()
        self._root_dir = Path(root_dir)
        self._jobs_dir = self._root_dir / "jobs"
        self._jobs_dir.mkdir(parents=True, exist_ok=True)
        self._load_jobs()

    def save_job(self, job: ResearchJob) -> ResearchJob:
        saved = super().save_job(job)
        self._job_path(job.job_id).write_text(
            json.dumps(_research_job_payload(saved), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return saved

    def _job_path(self, job_id: str) -> Path:
        return self._jobs_dir / f"{job_id}.json"

    def _load_jobs(self) -> None:
        for path in sorted(self._jobs_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            job = _research_job_from_payload(payload)
            self._jobs[job.job_id] = job


class FileBackedResearchResultRepository(InMemoryResearchResultRepository):
    """Result repository with JSON persistence under a local research root."""

    def __init__(self, root_dir: str | Path) -> None:
        super().__init__()
        self._root_dir = Path(root_dir)
        self._results_dir = self._root_dir / "results"
        self._results_dir.mkdir(parents=True, exist_ok=True)
        self._load_results()

    def save_result(self, result: ResearchResultArtifact) -> ResearchResultArtifact:
        saved = super().save_result(result)
        self._result_path(result.job_id).write_text(
            json.dumps(_research_result_payload(saved), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return saved

    def _result_path(self, job_id: str) -> Path:
        return self._results_dir / f"{job_id}.json"

    def _load_results(self) -> None:
        for path in sorted(self._results_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            result = _research_result_from_payload(payload)
            self._results[result.job_id] = result


class FileBackedResearchProgressEventStore(InMemoryResearchProgressEventStore):
    """Progress event store with JSON persistence under a local research root."""

    def __init__(self, root_dir: str | Path) -> None:
        super().__init__()
        self._root_dir = Path(root_dir)
        self._events_dir = self._root_dir / "events"
        self._events_dir.mkdir(parents=True, exist_ok=True)
        self._load_events()

    def append_event(self, event: ResearchProgressEvent) -> ResearchProgressEvent:
        saved = super().append_event(event)
        self._events_path(event.job_id).write_text(
            json.dumps([_research_event_payload(item) for item in self.list_events(event.job_id)], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return saved

    def _events_path(self, job_id: str) -> Path:
        return self._events_dir / f"{job_id}.json"

    def _load_events(self) -> None:
        for path in sorted(self._events_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, list):
                continue
            self._events[path.stem] = [_research_event_from_payload(item) for item in payload if isinstance(item, dict)]


def create_file_backed_research_persistence(root_dir: str | Path) -> ResearchPersistence:
    """Build the Deep Research persistence bundle from JSON-backed repositories."""

    root = Path(root_dir)
    root.mkdir(parents=True, exist_ok=True)
    return ResearchPersistence(
        jobs=FileBackedResearchJobRepository(root),
        results=FileBackedResearchResultRepository(root),
        progress=FileBackedResearchProgressEventStore(root),
    )

def recover_interrupted_research_jobs(root_dir: str | Path) -> tuple[str, ...]:
    """Mark persisted queued/probing/running jobs as errored after process restart."""

    persistence = create_file_backed_research_persistence(root_dir)
    recovered: list[str] = []
    for job in persistence.jobs.list_jobs_for_owner(""):
        pass
    jobs_repo = persistence.jobs
    raw_jobs = getattr(jobs_repo, "_jobs", {})
    for job in tuple(raw_jobs.values()):
        if job.status not in {ResearchJobStatus.QUEUED, ResearchJobStatus.PROBING, ResearchJobStatus.RUNNING}:
            continue
        recovered_job = ResearchJob(
            job_id=job.job_id,
            owner_id=job.owner_id,
            query=job.query,
            status=ResearchJobStatus.ERROR,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at or __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
            settings=job.settings,
            error="interrupted_on_recovery",
        )
        jobs_repo.save_job(recovered_job)
        persistence.progress.append_event(
            ResearchProgressEvent(
                job_id=job.job_id,
                status=ResearchJobStatus.ERROR,
                phase=ResearchPhase.ERROR,
                message="Research job was interrupted by process restart and recovered as error.",
                final=True,
            )
        )
        recovered.append(job.job_id)
    return tuple(recovered)

def _research_job_payload(job: ResearchJob) -> dict[str, object]:
    return {
        "job_id": job.job_id,
        "owner_id": job.owner_id,
        "query": job.query,
        "status": job.status.value,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "settings": asdict(job.settings),
        "error": job.error,
    }


def _research_job_from_payload(payload: dict[str, object]) -> ResearchJob:
    settings = payload.get("settings") if isinstance(payload.get("settings"), dict) else {}
    return ResearchJob(
        job_id=str(payload["job_id"]),
        owner_id=str(payload["owner_id"]),
        query=str(payload["query"]),
        status=ResearchJobStatus(str(payload["status"])),
        created_at=str(payload["created_at"]),
        started_at=_optional_str(payload.get("started_at")),
        completed_at=_optional_str(payload.get("completed_at")),
        settings=ResearchSettings(**{k: v for k, v in settings.items() if k in ResearchSettings.__dataclass_fields__}),
        error=_optional_str(payload.get("error")),
    )


def _research_result_payload(result: ResearchResultArtifact) -> dict[str, object]:
    return {
        "job_id": result.job_id,
        "owner_id": result.owner_id,
        "query": result.query,
        "status": result.status.value,
        "completion_mode": result.completion_mode.value,
        "result": result.result,
        "raw_report": result.raw_report,
        "category": result.category,
        "stats": asdict(result.stats),
        "sources": [asdict(source) for source in result.sources],
        "raw_findings": [asdict(finding) for finding in result.raw_findings],
        "created_at": result.created_at,
        "completed_at": result.completed_at,
    }


def _research_result_from_payload(payload: dict[str, object]) -> ResearchResultArtifact:
    stats_payload = payload.get("stats") if isinstance(payload.get("stats"), dict) else {}
    return ResearchResultArtifact(
        job_id=str(payload["job_id"]),
        owner_id=str(payload["owner_id"]),
        query=str(payload["query"]),
        status=ResearchJobStatus(str(payload["status"])),
        completion_mode=ResearchCompletionMode(str(payload["completion_mode"])),
        result=str(payload["result"]),
        raw_report=str(payload["raw_report"]),
        category=_optional_str(payload.get("category")),
        stats=ResearchStats(
            duration_seconds=int(stats_payload.get("duration_seconds", 0)),
            rounds=int(stats_payload.get("rounds", 0)),
            queries=int(stats_payload.get("queries", 0)),
            urls=int(stats_payload.get("urls", 0)),
            model=_optional_str(stats_payload.get("model")),
            search_providers=tuple(str(item) for item in stats_payload.get("search_providers", [])),
        ),
        sources=tuple(
            ResearchSource(
                url=str(item.get("url", "")),
                title=str(item.get("title", "")),
                image=_optional_str(item.get("image")),
            )
            for item in payload.get("sources", []) if isinstance(item, dict)
        ),
        raw_findings=tuple(
            ResearchFinding(
                url=str(item.get("url", "")),
                title=str(item.get("title", "")),
                summary=str(item.get("summary", "")),
            )
            for item in payload.get("raw_findings", []) if isinstance(item, dict)
        ),
        created_at=str(payload["created_at"]),
        completed_at=_optional_str(payload.get("completed_at")),
    )


def _research_event_payload(event: ResearchProgressEvent) -> dict[str, object]:
    return {
        "job_id": event.job_id,
        "status": event.status.value,
        "phase": event.phase.value,
        "round": event.round,
        "queries": event.queries,
        "query_preview": event.query_preview,
        "total_sources": event.total_sources,
        "new_sources": event.new_sources,
        "total_findings": event.total_findings,
        "url": event.url,
        "title": event.title,
        "message": event.message,
        "final": event.final,
    }


def _research_event_from_payload(payload: dict[str, object]) -> ResearchProgressEvent:
    return ResearchProgressEvent(
        job_id=str(payload["job_id"]),
        status=ResearchJobStatus(str(payload["status"])),
        phase=ResearchPhase(str(payload["phase"])),
        round=int(payload.get("round", 0)),
        queries=int(payload.get("queries", 0)),
        query_preview=_optional_str(payload.get("query_preview")),
        total_sources=int(payload.get("total_sources", 0)),
        new_sources=int(payload.get("new_sources", 0)),
        total_findings=int(payload.get("total_findings", 0)),
        url=_optional_str(payload.get("url")),
        title=_optional_str(payload.get("title")),
        message=_optional_str(payload.get("message")),
        final=bool(payload.get("final", False)),
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


__all__ = [
    "FileBackedResearchJobRepository",
    "FileBackedResearchProgressEventStore",
    "FileBackedResearchResultRepository",
    "create_file_backed_research_persistence",
    "recover_interrupted_research_jobs",
]
