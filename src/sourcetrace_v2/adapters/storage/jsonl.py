from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from sourcetrace_v2.core.contracts.compiled_artifacts import (
    CompiledEvidenceSnapshot,
    CompiledResearchArtifact,
    EvidenceJudgmentDimension,
    EvidenceJudgmentSnapshot,
    PdfEvidenceContextSnapshot,
)
from sourcetrace_v2.core.domain.identifiers import DegradationReason, ReceiptCoverageStatus, StageId, StageStatus
from sourcetrace_v2.core.domain.models import LlmExecutionReceipt, PdfEvidenceContext, ResearchResultArtifact, RetrievedEvidenceCandidate, RunPersistenceMarker, StageExecutionReceipt


def _serialize_dataclass(instance: Any) -> dict[str, Any]:
    payload = asdict(instance)
    for key, value in list(payload.items()):
        if hasattr(value, "value"):
            payload[key] = value.value
    return payload


def _enum_value(enum_cls, value: str | None):
    if value is None:
        return None
    return enum_cls(value)


def _deserialize_judgment_dimension(payload: dict[str, Any] | None) -> EvidenceJudgmentDimension | None:
    if payload is None:
        return None
    return EvidenceJudgmentDimension(
        score=int(payload.get("score", 0)),
        band=str(payload.get("band", "none")),
        signals=tuple(str(item) for item in payload.get("signals", [])),
    )


def _deserialize_judgment_snapshot(payload: dict[str, Any] | None) -> EvidenceJudgmentSnapshot | None:
    if payload is None:
        return None
    authority = _deserialize_judgment_dimension(payload.get("authority"))
    topic_match = _deserialize_judgment_dimension(payload.get("topic_match"))
    specificity = _deserialize_judgment_dimension(payload.get("specificity"))
    answer_fit = _deserialize_judgment_dimension(payload.get("answer_fit"))
    if authority is None or topic_match is None or specificity is None or answer_fit is None:
        return None
    return EvidenceJudgmentSnapshot(
        contract_version=str(payload.get("contract_version", "")),
        authority=authority,
        topic_match=topic_match,
        specificity=specificity,
        answer_fit=answer_fit,
    )


def _deserialize_pdf_context(payload: dict[str, Any] | None) -> PdfEvidenceContext | None:
    if payload is None:
        return None
    return PdfEvidenceContext(
        document_scope=str(payload.get("document_scope", "") or ""),
        entity_match_summary=str(payload.get("entity_match_summary", "") or ""),
        key_findings=tuple(str(item) for item in payload.get("key_findings", [])),
    )


def _deserialize_pdf_context_snapshot(payload: dict[str, Any] | None) -> PdfEvidenceContextSnapshot | None:
    if payload is None:
        return None
    return PdfEvidenceContextSnapshot(
        document_scope=str(payload.get("document_scope", "") or ""),
        entity_match_summary=str(payload.get("entity_match_summary", "") or ""),
        key_findings=tuple(str(item) for item in payload.get("key_findings", [])),
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


class JsonlResultArtifactRepository:
    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.path = self.base_dir / "result_artifacts.jsonl"
        self.compiled_path = self.base_dir / "compiled_artifacts.jsonl"
        self.marker_path = self.base_dir / "run_markers.jsonl"

    def save_result(self, artifact: ResearchResultArtifact) -> ResearchResultArtifact:
        _append_jsonl(self.path, _serialize_dataclass(artifact))
        return artifact

    def get_result(self, *, job_id: str, run_id: str) -> ResearchResultArtifact | None:
        match: dict[str, Any] | None = None
        for row in _read_jsonl(self.path):
            if row.get("job_id") == job_id and row.get("run_id") == run_id:
                match = row
        if match is None:
            return None
        return ResearchResultArtifact(
            job_id=match["job_id"],
            run_id=match["run_id"],
            result_text=match["result_text"],
            summary=match.get("summary", ""),
            evidence_query=match.get("evidence_query", ""),
            evidence_candidates=tuple(
                RetrievedEvidenceCandidate(
                    candidate_id=candidate["candidate_id"],
                    job_id=candidate["job_id"],
                    run_id=candidate["run_id"],
                    provider=candidate["provider"],
                    query=candidate["query"],
                    title=candidate["title"],
                    url=candidate["url"],
                    snippet=candidate.get("snippet", ""),
                    rank=candidate.get("rank", 1),
                    source_type=str(candidate.get("source_type", "unknown") or "unknown"),
                    pdf_context=_deserialize_pdf_context(candidate.get("pdf_context")),
                )
                for candidate in match.get("evidence_candidates", [])
            ),
        )

    def save_compiled_artifact(self, artifact: CompiledResearchArtifact) -> CompiledResearchArtifact:
        _append_jsonl(self.compiled_path, _serialize_dataclass(artifact))
        return artifact

    def get_compiled_artifact(self, *, job_id: str, run_id: str) -> CompiledResearchArtifact | None:
        match: dict[str, Any] | None = None
        for row in _read_jsonl(self.compiled_path):
            if row.get("job_id") == job_id and row.get("run_id") == run_id:
                match = row
        if match is None:
            return None
        return CompiledResearchArtifact(
            artifact_id=match["artifact_id"],
            job_id=match["job_id"],
            run_id=match["run_id"],
            summary=match.get("summary", ""),
            selected_evidence=tuple(
                CompiledEvidenceSnapshot(
                    title=item["title"],
                    url=item["url"],
                    provider=item["provider"],
                    rank=item["rank"],
                    snippet=item.get("snippet", ""),
                    judgment=_deserialize_judgment_snapshot(item.get("judgment")),
                    pdf_context=_deserialize_pdf_context_snapshot(item.get("pdf_context")),
                )
                for item in match.get("selected_evidence", [])
            ),
            selected_evidence_contract_version=match.get("selected_evidence_contract_version"),
            confidence_note=match.get("confidence_note", "bounded_v2_compiled_artifact"),
        )

    def save_run_marker(self, marker: RunPersistenceMarker) -> RunPersistenceMarker:
        _append_jsonl(self.marker_path, _serialize_dataclass(marker))
        return marker

    def get_run_marker(self, *, job_id: str, run_id: str) -> RunPersistenceMarker | None:
        match: dict[str, Any] | None = None
        for row in _read_jsonl(self.marker_path):
            if row.get("job_id") == job_id and row.get("run_id") == run_id:
                match = row
        if match is None:
            return None
        return RunPersistenceMarker(
            job_id=match["job_id"],
            run_id=match["run_id"],
            status=match.get("status", "committed"),
        )


class JsonlReceiptRepository:
    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.stage_path = self.base_dir / "stage_receipts.jsonl"
        self.llm_path = self.base_dir / "llm_receipts.jsonl"

    def append_stage(self, receipt: StageExecutionReceipt) -> StageExecutionReceipt:
        _append_jsonl(self.stage_path, _serialize_dataclass(receipt))
        return receipt

    def append_llm(self, receipt: LlmExecutionReceipt) -> LlmExecutionReceipt:
        _append_jsonl(self.llm_path, _serialize_dataclass(receipt))
        return receipt

    def list_stage_receipts(self, *, job_id: str, run_id: str) -> tuple[StageExecutionReceipt, ...]:
        rows = [row for row in _read_jsonl(self.stage_path) if row.get("job_id") == job_id and row.get("run_id") == run_id]
        return tuple(
            StageExecutionReceipt(
                receipt_id=row["receipt_id"],
                job_id=row["job_id"],
                run_id=row["run_id"],
                stage_id=StageId(row["stage_id"]),
                call_site=row["call_site"],
                status=StageStatus(row["status"]),
                attempt=row.get("attempt", 1),
                round_number=row.get("round_number"),
                detail=row.get("detail", ""),
                degradation_reason=_enum_value(DegradationReason, row.get("degradation_reason")),
            )
            for row in rows
        )

    def list_llm_receipts(self, *, job_id: str, run_id: str) -> tuple[LlmExecutionReceipt, ...]:
        rows = [row for row in _read_jsonl(self.llm_path) if row.get("job_id") == job_id and row.get("run_id") == run_id]
        return tuple(
            LlmExecutionReceipt(
                receipt_id=row["receipt_id"],
                job_id=row["job_id"],
                run_id=row["run_id"],
                stage_id=StageId(row["stage_id"]),
                call_site=row["call_site"],
                profile=row["profile"],
                provider=row["provider"],
                model=row["model"],
                coverage_status=ReceiptCoverageStatus(row.get("coverage_status", "tracked")),
                input_tokens=row.get("input_tokens"),
                output_tokens=row.get("output_tokens"),
                total_tokens=row.get("total_tokens"),
                finish_reason=row.get("finish_reason"),
                degradation_reason=_enum_value(DegradationReason, row.get("degradation_reason")),
            )
            for row in rows
        )
