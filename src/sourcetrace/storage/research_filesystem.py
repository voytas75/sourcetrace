"""Filesystem-backed persistence adapters for durable Deep Research state."""

import json
from dataclasses import asdict
from pathlib import Path

from sourcetrace.domain.research import (
    CompiledResearchArtifact,
    CompiledResearchArtifactLint,
    CompiledResearchArtifactLintStatus,
    CompiledResearchClaim,
    CompiledResearchEvidenceRef,
    ProblemAnalysis,
    ResearchBranchEvaluation,
    ResearchBranchProposal,
    ResearchBranchProposalSet,
    ResearchBranchScore,
    ResearchCompletionMode,
    ResearchComplexity,
    ResearchEvaluationArtifact,
    ResearchEvaluationVerdict,
    ResearchEvidencePack,
    ResearchExecutionPlan,
    ResearchExecutionPlanStep,
    ResearchFinding,
    ResearchJob,
    ResearchJobStatus,
    ResearchPhase,
    ResearchPlanStrategy,
    ResearchProgressEvent,
    ResearchQueryClass,
    ResearchReflection,
    ResearchResultArtifact,
    ResearchSettings,
    ResearchSource,
    ResearchStats,
)
from sourcetrace.storage.research import (
    InMemoryCompiledResearchArtifactLintRepository,
    InMemoryCompiledResearchArtifactRepository,
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


class FileBackedCompiledResearchArtifactRepository(InMemoryCompiledResearchArtifactRepository):
    """Compiled research artifact repository with JSON persistence."""

    def __init__(self, root_dir: str | Path) -> None:
        super().__init__()
        self._root_dir = Path(root_dir)
        self._compiled_dir = self._root_dir / "compiled"
        self._compiled_dir.mkdir(parents=True, exist_ok=True)
        self._load_artifacts()

    def list_artifacts_for_owner(self, owner_id: str) -> tuple[CompiledResearchArtifact, ...]:
        normalized_owner = owner_id.strip().lower()
        return tuple(
            artifact
            for artifact in self.list_all_artifacts()
            if artifact.owner_id.strip().lower() == normalized_owner
        )

    def save_artifact(self, artifact: CompiledResearchArtifact) -> CompiledResearchArtifact:
        saved = super().save_artifact(artifact)
        self._artifact_path(artifact.artifact_id).write_text(
            json.dumps(_compiled_research_artifact_payload(saved), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return saved

    def _artifact_path(self, artifact_id: str) -> Path:
        return self._compiled_dir / f"{artifact_id}.json"

    def _load_artifacts(self) -> None:
        for path in sorted(self._compiled_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            artifact = _compiled_research_artifact_from_payload(payload)
            self._artifacts[artifact.artifact_id] = artifact


class FileBackedCompiledResearchArtifactLintRepository(InMemoryCompiledResearchArtifactLintRepository):
    """Compiled research artifact lint repository with JSON persistence."""

    def __init__(self, root_dir: str | Path) -> None:
        super().__init__()
        self._root_dir = Path(root_dir)
        self._lint_dir = self._root_dir / "compiled-lint"
        self._lint_dir.mkdir(parents=True, exist_ok=True)
        self._load_lints()

    def list_lints_for_owner(self, owner_id: str) -> tuple[CompiledResearchArtifactLint, ...]:
        normalized_owner = owner_id.strip().lower()
        return tuple(
            lint
            for lint in self.list_all_lints()
            if lint.owner_id.strip().lower() == normalized_owner
        )

    def save_lint(self, lint: CompiledResearchArtifactLint) -> CompiledResearchArtifactLint:
        saved = super().save_lint(lint)
        self._lint_path(lint.lint_id).write_text(
            json.dumps(_compiled_research_artifact_lint_payload(saved), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return saved

    def _lint_path(self, lint_id: str) -> Path:
        return self._lint_dir / f"{lint_id}.json"

    def _load_lints(self) -> None:
        for path in sorted(self._lint_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            lint = _compiled_research_artifact_lint_from_payload(payload)
            self._lints[lint.lint_id] = lint
            self._artifact_to_lint[lint.artifact_id] = lint.lint_id


def create_file_backed_research_persistence(root_dir: str | Path) -> ResearchPersistence:
    """Build the Deep Research persistence bundle from JSON-backed repositories."""

    root = Path(root_dir)
    root.mkdir(parents=True, exist_ok=True)
    return ResearchPersistence(
        jobs=FileBackedResearchJobRepository(root),
        results=FileBackedResearchResultRepository(root),
        progress=FileBackedResearchProgressEventStore(root),
        compiled=FileBackedCompiledResearchArtifactRepository(root),
        compiled_lint=FileBackedCompiledResearchArtifactLintRepository(root),
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



def _query_class_from_payload(value: object) -> ResearchQueryClass:
    normalized = str(value or ResearchQueryClass.GENERAL.value)
    if normalized == "unknown":
        normalized = ResearchQueryClass.GENERAL.value
    return ResearchQueryClass(normalized)


def _problem_analysis_payload(analysis: ProblemAnalysis | None) -> dict[str, object] | None:
    if analysis is None:
        return None
    return {
        "query_class": analysis.query_class.value,
        "complexity": analysis.complexity.value,
        "goal": analysis.goal,
        "focus_areas": list(analysis.focus_areas),
        "constraints": list(analysis.constraints),
        "analysis_version": analysis.analysis_version,
    }


def _problem_analysis_from_payload(payload: object) -> ProblemAnalysis | None:
    if not isinstance(payload, dict):
        return None
    return ProblemAnalysis(
        query_class=_query_class_from_payload(payload.get("query_class", ResearchQueryClass.GENERAL.value)),
        complexity=ResearchComplexity(str(payload.get("complexity", ResearchComplexity.MEDIUM.value))),
        goal=str(payload.get("goal", "")),
        focus_areas=tuple(str(item) for item in payload.get("focus_areas", [])),
        constraints=tuple(str(item) for item in payload.get("constraints", [])),
        analysis_version=str(payload.get("analysis_version", "problem_analyzer_v1")),
    )


def _execution_plan_payload(plan: ResearchExecutionPlan | None) -> dict[str, object] | None:
    if plan is None:
        return None
    return {
        "plan_version": plan.plan_version,
        "strategy": plan.strategy.value,
        "objective": plan.objective,
        "steps": [
            {
                "step_id": step.step_id,
                "kind": step.kind,
                "objective": step.objective,
                "depends_on": list(step.depends_on),
            }
            for step in plan.steps
        ],
    }


def _execution_plan_from_payload(payload: object) -> ResearchExecutionPlan | None:
    if not isinstance(payload, dict):
        return None
    return ResearchExecutionPlan(
        plan_version=str(payload.get("plan_version", "planner_v2")),
        strategy=ResearchPlanStrategy(str(payload.get("strategy", ResearchPlanStrategy.DIRECT_ANSWER.value))),
        objective=str(payload.get("objective", "")),
        steps=tuple(
            ResearchExecutionPlanStep(
                step_id=str(item.get("step_id", "")),
                kind=str(item.get("kind", "")),
                objective=str(item.get("objective", "")),
                depends_on=tuple(str(dep) for dep in item.get("depends_on", [])),
            )
            for item in payload.get("steps", []) if isinstance(item, dict)
        ),
    )


def _evidence_pack_payload(pack: ResearchEvidencePack | None) -> dict[str, object] | None:
    if pack is None:
        return None
    return {
        "pack_version": pack.pack_version,
        "query_class": pack.query_class.value,
        "core": [asdict(item) for item in pack.core],
        "supporting": [asdict(item) for item in pack.supporting],
        "background": [asdict(item) for item in pack.background],
        "has_direct_procedural_evidence": pack.has_direct_procedural_evidence,
    }


def _evidence_pack_from_payload(payload: object) -> ResearchEvidencePack | None:
    if not isinstance(payload, dict):
        return None
    def _finding_tuple(key: str) -> tuple[ResearchFinding, ...]:
        return tuple(
            ResearchFinding(
                url=str(item.get("url", "")),
                title=str(item.get("title", "")),
                summary=str(item.get("summary", "")),
            )
            for item in payload.get(key, []) if isinstance(item, dict)
        )
    return ResearchEvidencePack(
        pack_version=str(payload.get("pack_version", "evidence_pack_v1")),
        query_class=_query_class_from_payload(payload.get("query_class", ResearchQueryClass.GENERAL.value)),
        core=_finding_tuple("core"),
        supporting=_finding_tuple("supporting"),
        background=_finding_tuple("background"),
        has_direct_procedural_evidence=bool(payload.get("has_direct_procedural_evidence", False)),
    )


def _branch_proposal_set_payload(proposals: ResearchBranchProposalSet | None) -> dict[str, object] | None:
    if proposals is None:
        return None
    return {
        "proposal_version": proposals.proposal_version,
        "eligible": proposals.eligible,
        "reason": proposals.reason,
        "branches": [asdict(item) for item in proposals.branches],
    }


def _branch_proposal_set_from_payload(payload: object) -> ResearchBranchProposalSet | None:
    if not isinstance(payload, dict):
        return None
    return ResearchBranchProposalSet(
        proposal_version=str(payload.get("proposal_version", "branch_proposal_v1")),
        eligible=bool(payload.get("eligible", False)),
        reason=str(payload.get("reason", "not_eligible")),
        branches=tuple(
            ResearchBranchProposal(
                branch_id=str(item.get("branch_id", "")),
                label=str(item.get("label", "")),
                objective=str(item.get("objective", "")),
            )
            for item in payload.get("branches", []) if isinstance(item, dict)
        ),
    )


def _branch_evaluation_payload(evaluation: ResearchBranchEvaluation | None) -> dict[str, object] | None:
    if evaluation is None:
        return None
    return {
        "evaluation_version": evaluation.evaluation_version,
        "selected_branch_ids": list(evaluation.selected_branch_ids),
        "scores": [
            {
                "branch_id": item.branch_id,
                "coverage_score": item.coverage_score,
                "evidence_fit_score": item.evidence_fit_score,
                "priority_score": item.priority_score,
                "combined_score": item.combined_score,
            }
            for item in evaluation.scores
        ],
    }


def _branch_evaluation_from_payload(payload: object) -> ResearchBranchEvaluation | None:
    if not isinstance(payload, dict):
        return None
    return ResearchBranchEvaluation(
        evaluation_version=str(payload.get("evaluation_version", "branch_evaluator_v1")),
        selected_branch_ids=tuple(str(item) for item in payload.get("selected_branch_ids", [])),
        scores=tuple(
            ResearchBranchScore(
                branch_id=str(item.get("branch_id", "")),
                coverage_score=float(item.get("coverage_score", 0.0)),
                evidence_fit_score=float(item.get("evidence_fit_score", 0.0)),
                priority_score=float(item.get("priority_score", 0.0)),
                combined_score=float(item.get("combined_score", 0.0)),
            )
            for item in payload.get("scores", []) if isinstance(item, dict)
        ),
    )


def _reflection_payload(reflection: ResearchReflection | None) -> dict[str, object] | None:
    if reflection is None:
        return None
    return {
        "reflection_version": reflection.reflection_version,
        "goal_coverage": reflection.goal_coverage,
        "missing_topics": list(reflection.missing_topics),
        "weak_evidence_areas": list(reflection.weak_evidence_areas),
        "should_follow_up": reflection.should_follow_up,
        "recommended_follow_up": reflection.recommended_follow_up,
    }


def _reflection_from_payload(payload: object) -> ResearchReflection | None:
    if not isinstance(payload, dict):
        return None
    return ResearchReflection(
        reflection_version=str(payload.get("reflection_version", "reflection_v1")),
        goal_coverage=str(payload.get("goal_coverage", "partial")),
        missing_topics=tuple(str(item) for item in payload.get("missing_topics", [])),
        weak_evidence_areas=tuple(str(item) for item in payload.get("weak_evidence_areas", [])),
        should_follow_up=bool(payload.get("should_follow_up", False)),
        recommended_follow_up=_optional_str(payload.get("recommended_follow_up")),
    )


def _evaluation_payload(evaluation: ResearchEvaluationArtifact | None) -> dict[str, object] | None:
    if evaluation is None:
        return None
    return {
        "query_class": evaluation.query_class.value,
        "source_quality_verdict": evaluation.source_quality_verdict.value,
        "source_quality_reasons": list(evaluation.source_quality_reasons),
        "relevance_verdict": evaluation.relevance_verdict.value,
        "relevance_risks": list(evaluation.relevance_risks),
        "truthfulness_verdict": evaluation.truthfulness_verdict.value,
        "overclaim_risks": list(evaluation.overclaim_risks),
        "missing_checks": list(evaluation.missing_checks),
        "recommended_next_check": evaluation.recommended_next_check,
        "should_revise_report": evaluation.should_revise_report,
    }


def _evaluation_from_payload(payload: object) -> ResearchEvaluationArtifact | None:
    if not isinstance(payload, dict):
        return None
    return ResearchEvaluationArtifact(
        query_class=_query_class_from_payload(payload.get("query_class", ResearchQueryClass.GENERAL.value)),
        source_quality_verdict=ResearchEvaluationVerdict(str(payload.get("source_quality_verdict", ResearchEvaluationVerdict.MIXED.value))),
        source_quality_reasons=tuple(str(item) for item in payload.get("source_quality_reasons", [])),
        relevance_verdict=ResearchEvaluationVerdict(str(payload.get("relevance_verdict", ResearchEvaluationVerdict.MIXED.value))),
        relevance_risks=tuple(str(item) for item in payload.get("relevance_risks", [])),
        truthfulness_verdict=ResearchEvaluationVerdict(str(payload.get("truthfulness_verdict", ResearchEvaluationVerdict.MIXED.value))),
        overclaim_risks=tuple(str(item) for item in payload.get("overclaim_risks", [])),
        missing_checks=tuple(str(item) for item in payload.get("missing_checks", [])),
        recommended_next_check=str(payload.get("recommended_next_check", "")),
        should_revise_report=bool(payload.get("should_revise_report", False)),
    )

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
        "problem_analysis": _problem_analysis_payload(job.problem_analysis),
        "execution_plan": _execution_plan_payload(job.execution_plan),
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
        problem_analysis=_problem_analysis_from_payload(payload.get("problem_analysis")),
        execution_plan=_execution_plan_from_payload(payload.get("execution_plan")),
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
        "problem_analysis": _problem_analysis_payload(result.problem_analysis),
        "execution_plan": _execution_plan_payload(result.execution_plan),
        "evidence_pack": _evidence_pack_payload(result.evidence_pack),
        "branch_proposals": _branch_proposal_set_payload(result.branch_proposals),
        "branch_evaluation": _branch_evaluation_payload(result.branch_evaluation),
        "reflection": _reflection_payload(result.reflection),
        "evaluation": _evaluation_payload(result.evaluation),
        "created_at": result.created_at,
        "completed_at": result.completed_at,
    }


def _compiled_research_artifact_payload(artifact: CompiledResearchArtifact) -> dict[str, object]:
    return {
        "artifact_id": artifact.artifact_id,
        "source_job_id": artifact.source_job_id,
        "owner_id": artifact.owner_id,
        "query": artifact.query,
        "query_class": artifact.query_class.value,
        "title": artifact.title,
        "summary": artifact.summary,
        "current_answer": artifact.current_answer,
        "key_claims": [asdict(claim) for claim in artifact.key_claims],
        "supporting_evidence": [asdict(ref) for ref in artifact.supporting_evidence],
        "open_questions": list(artifact.open_questions),
        "next_checks": list(artifact.next_checks),
        "source_refs": [asdict(source) for source in artifact.source_refs],
        "problem_analysis_snapshot": _problem_analysis_payload(artifact.problem_analysis_snapshot),
        "execution_plan_snapshot": _execution_plan_payload(artifact.execution_plan_snapshot),
        "reflection_snapshot": _reflection_payload(artifact.reflection_snapshot),
        "evaluation_snapshot": _evaluation_payload(artifact.evaluation_snapshot),
        "created_at": artifact.created_at,
    }



def _compiled_research_artifact_lint_payload(lint: CompiledResearchArtifactLint) -> dict[str, object]:
    return {
        "lint_id": lint.lint_id,
        "artifact_id": lint.artifact_id,
        "owner_id": lint.owner_id,
        "status": lint.status.value,
        "completeness_verdict": lint.completeness_verdict.value,
        "evidence_verdict": lint.evidence_verdict.value,
        "followup_verdict": lint.followup_verdict.value,
        "risk_flags": list(lint.risk_flags),
        "missing_sections": list(lint.missing_sections),
        "recommended_repairs": list(lint.recommended_repairs),
        "recommended_next_action": lint.recommended_next_action,
        "created_at": lint.created_at,
    }



def _compiled_research_artifact_lint_from_payload(payload: dict[str, object]) -> CompiledResearchArtifactLint:
    return CompiledResearchArtifactLint(
        lint_id=str(payload["lint_id"]),
        artifact_id=str(payload["artifact_id"]),
        owner_id=str(payload["owner_id"]),
        status=CompiledResearchArtifactLintStatus(str(payload.get("status", CompiledResearchArtifactLintStatus.NEEDS_REVIEW.value))),
        completeness_verdict=ResearchEvaluationVerdict(str(payload.get("completeness_verdict", ResearchEvaluationVerdict.MIXED.value))),
        evidence_verdict=ResearchEvaluationVerdict(str(payload.get("evidence_verdict", ResearchEvaluationVerdict.MIXED.value))),
        followup_verdict=ResearchEvaluationVerdict(str(payload.get("followup_verdict", ResearchEvaluationVerdict.MIXED.value))),
        risk_flags=tuple(str(item) for item in payload.get("risk_flags", [])),
        missing_sections=tuple(str(item) for item in payload.get("missing_sections", [])),
        recommended_repairs=tuple(str(item) for item in payload.get("recommended_repairs", [])),
        recommended_next_action=str(payload.get("recommended_next_action", "")),
        created_at=str(payload.get("created_at", "")),
    )



def _compiled_research_artifact_from_payload(payload: dict[str, object]) -> CompiledResearchArtifact:
    return CompiledResearchArtifact(
        artifact_id=str(payload["artifact_id"]),
        source_job_id=str(payload["source_job_id"]),
        owner_id=str(payload["owner_id"]),
        query=str(payload["query"]),
        query_class=_query_class_from_payload(payload.get("query_class", ResearchQueryClass.GENERAL.value)),
        title=str(payload.get("title", "")),
        summary=str(payload.get("summary", "")),
        current_answer=str(payload.get("current_answer", "")),
        key_claims=tuple(
            CompiledResearchClaim(
                text=str(item.get("text", "")),
                evidence_refs=tuple(str(ref) for ref in item.get("evidence_refs", [])),
            )
            for item in payload.get("key_claims", []) if isinstance(item, dict)
        ),
        supporting_evidence=tuple(
            CompiledResearchEvidenceRef(
                url=str(item.get("url", "")),
                title=str(item.get("title", "")),
                summary=str(item.get("summary", "")),
            )
            for item in payload.get("supporting_evidence", []) if isinstance(item, dict)
        ),
        open_questions=tuple(str(item) for item in payload.get("open_questions", [])),
        next_checks=tuple(str(item) for item in payload.get("next_checks", [])),
        source_refs=tuple(
            ResearchSource(
                url=str(item.get("url", "")),
                title=str(item.get("title", "")),
                image=_optional_str(item.get("image")),
            )
            for item in payload.get("source_refs", []) if isinstance(item, dict)
        ),
        problem_analysis_snapshot=_problem_analysis_from_payload(payload.get("problem_analysis_snapshot")),
        execution_plan_snapshot=_execution_plan_from_payload(payload.get("execution_plan_snapshot")),
        reflection_snapshot=_reflection_from_payload(payload.get("reflection_snapshot")),
        evaluation_snapshot=_evaluation_from_payload(payload.get("evaluation_snapshot")),
        created_at=str(payload.get("created_at", "")),
    )



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
            pre_extraction_sources_seen=int(stats_payload.get("pre_extraction_sources_seen", 0)),
            pre_extraction_sources_kept=int(stats_payload.get("pre_extraction_sources_kept", 0)),
            pre_extraction_sources_dropped=int(stats_payload.get("pre_extraction_sources_dropped", 0)),
            authority_policy_applied=bool(stats_payload.get("authority_policy_applied", False)),
            authority_filter_fallback_used=bool(stats_payload.get("authority_filter_fallback_used", False)),
            dropped_source_types=tuple(str(item) for item in stats_payload.get("dropped_source_types", [])),
            packed_core_count=int(stats_payload.get("packed_core_count", 0)),
            packed_supporting_count=int(stats_payload.get("packed_supporting_count", 0)),
            packed_background_count=int(stats_payload.get("packed_background_count", 0)),
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
        problem_analysis=_problem_analysis_from_payload(payload.get("problem_analysis")),
        execution_plan=_execution_plan_from_payload(payload.get("execution_plan")),
        evidence_pack=_evidence_pack_from_payload(payload.get("evidence_pack")),
        branch_proposals=_branch_proposal_set_from_payload(payload.get("branch_proposals")),
        branch_evaluation=_branch_evaluation_from_payload(payload.get("branch_evaluation")),
        reflection=_reflection_from_payload(payload.get("reflection")),
        evaluation=_evaluation_from_payload(payload.get("evaluation")),
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
        "query_list": list(event.query_list),
        "providers_attempted": list(event.providers_attempted),
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
        query_list=tuple(str(item) for item in (payload.get("query_list") or ())),
        providers_attempted=tuple(str(item) for item in (payload.get("providers_attempted") or ())),
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
    "FileBackedCompiledResearchArtifactLintRepository",
    "FileBackedCompiledResearchArtifactRepository",
    "FileBackedResearchJobRepository",
    "FileBackedResearchProgressEventStore",
    "FileBackedResearchResultRepository",
    "create_file_backed_research_persistence",
    "recover_interrupted_research_jobs",
]
