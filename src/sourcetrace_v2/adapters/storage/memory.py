from __future__ import annotations

from dataclasses import dataclass, field

from sourcetrace_v2.core.contracts.compiled_artifacts import CompiledResearchArtifact
from sourcetrace_v2.core.domain.case_documents import CaseRecord, DocumentRecord
from sourcetrace_v2.core.domain.models import (
    LlmExecutionReceipt,
    ResearchResultArtifact,
    RunPersistenceMarker,
    StageExecutionReceipt,
)


@dataclass
class InMemoryResultArtifactRepository:
    artifacts: dict[tuple[str, str], ResearchResultArtifact] = field(
        default_factory=dict[tuple[str, str], ResearchResultArtifact]
    )
    compiled_artifacts: dict[tuple[str, str], CompiledResearchArtifact] = field(
        default_factory=dict[tuple[str, str], CompiledResearchArtifact]
    )
    markers: dict[tuple[str, str], RunPersistenceMarker] = field(
        default_factory=dict[tuple[str, str], RunPersistenceMarker]
    )

    def save_result(self, artifact: ResearchResultArtifact) -> ResearchResultArtifact:
        self.artifacts[(artifact.job_id, artifact.run_id)] = artifact
        return artifact

    def get_result(self, *, job_id: str, run_id: str) -> ResearchResultArtifact | None:
        return self.artifacts.get((job_id, run_id))

    def save_compiled_artifact(
        self, artifact: CompiledResearchArtifact
    ) -> CompiledResearchArtifact:
        self.compiled_artifacts[(artifact.job_id, artifact.run_id)] = artifact
        return artifact

    def get_compiled_artifact(
        self, *, job_id: str, run_id: str
    ) -> CompiledResearchArtifact | None:
        return self.compiled_artifacts.get((job_id, run_id))

    def save_run_marker(self, marker: RunPersistenceMarker) -> RunPersistenceMarker:
        self.markers[(marker.job_id, marker.run_id)] = marker
        return marker

    def get_run_marker(
        self, *, job_id: str, run_id: str
    ) -> RunPersistenceMarker | None:
        return self.markers.get((job_id, run_id))


@dataclass
class InMemoryReceiptRepository:
    stage_receipts: dict[tuple[str, str], list[StageExecutionReceipt]] = field(
        default_factory=dict[tuple[str, str], list[StageExecutionReceipt]]
    )
    llm_receipts: dict[tuple[str, str], list[LlmExecutionReceipt]] = field(
        default_factory=dict[tuple[str, str], list[LlmExecutionReceipt]]
    )

    def append_stage(self, receipt: StageExecutionReceipt) -> StageExecutionReceipt:
        self.stage_receipts.setdefault((receipt.job_id, receipt.run_id), []).append(
            receipt
        )
        return receipt

    def append_llm(self, receipt: LlmExecutionReceipt) -> LlmExecutionReceipt:
        self.llm_receipts.setdefault((receipt.job_id, receipt.run_id), []).append(
            receipt
        )
        return receipt

    def list_stage_receipts(
        self, *, job_id: str, run_id: str
    ) -> tuple[StageExecutionReceipt, ...]:
        return tuple(self.stage_receipts.get((job_id, run_id), []))

    def list_llm_receipts(
        self, *, job_id: str, run_id: str
    ) -> tuple[LlmExecutionReceipt, ...]:
        return tuple(self.llm_receipts.get((job_id, run_id), []))


@dataclass
class InMemoryCaseDocumentRepository:
    cases: dict[str, CaseRecord] = field(default_factory=dict[str, CaseRecord])
    documents: dict[str, DocumentRecord] = field(
        default_factory=dict[str, DocumentRecord]
    )

    def save_case(self, case: CaseRecord) -> CaseRecord:
        self.cases[case.case_id] = case
        return case

    def get_case(self, *, case_id: str) -> CaseRecord | None:
        return self.cases.get(case_id)

    def save_document(self, document: DocumentRecord) -> DocumentRecord:
        self.documents[document.document_id] = document
        return document

    def get_document(self, *, document_id: str) -> DocumentRecord | None:
        return self.documents.get(document_id)

    def list_documents_for_case(self, *, case_id: str) -> tuple[DocumentRecord, ...]:
        return tuple(
            sorted(
                (
                    document
                    for document in self.documents.values()
                    if document.case_id == case_id
                ),
                key=lambda document: document.document_id,
            )
        )
