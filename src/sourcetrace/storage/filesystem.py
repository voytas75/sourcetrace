"""Filesystem-backed persistence adapters for lightweight local durability."""

import json
from dataclasses import dataclass
from pathlib import Path

from sourcetrace.application.continuity import ContinuityPack, ContinuityPackOutcome, ContinuityPackRequest
from sourcetrace.domain.cases import Case
from sourcetrace.storage.memory import InMemoryCaseRepository


@dataclass(frozen=True)
class ContinuityPackPersistenceStatus:
    """Operational diagnostics for continuity-pack persistence."""

    enabled: bool
    backend: str
    root_dir: str | None


class FileBackedCaseRepository(InMemoryCaseRepository):
    """Case repository with JSON persistence for active continuity packs."""

    def __init__(self, root_dir: str | Path) -> None:
        super().__init__()
        self._root_dir = Path(root_dir)
        self._continuity_pack_dir = self._root_dir / "continuity_packs"
        self._continuity_pack_dir.mkdir(parents=True, exist_ok=True)
        self._load_continuity_packs()

    def save_case(self, case: Case) -> Case:
        saved = super().save_case(case)
        return saved

    def save_continuity_pack(
        self,
        case_id: str,
        continuity_pack: ContinuityPackOutcome,
    ) -> ContinuityPackOutcome:
        saved = super().save_continuity_pack(case_id, continuity_pack)
        self._write_continuity_pack(case_id, saved)
        return saved

    def _continuity_pack_path(self, case_id: str) -> Path:
        return self._continuity_pack_dir / f"{case_id}.json"

    def _write_continuity_pack(
        self,
        case_id: str,
        continuity_pack: ContinuityPackOutcome,
    ) -> None:
        payload = {
            "request": {
                "title": continuity_pack.request.title,
                "source_artifact_path": continuity_pack.request.source_artifact_path,
                "confirmed": list(continuity_pack.request.confirmed),
                "assumptions": list(continuity_pack.request.assumptions),
                "to_verify": list(continuity_pack.request.to_verify),
                "recommended_next_test": list(continuity_pack.request.recommended_next_test),
                "decision_snapshot": list(continuity_pack.request.decision_snapshot),
            },
            "continuity_pack": {
                "title": continuity_pack.continuity_pack.title,
                "source_artifact_path": continuity_pack.continuity_pack.source_artifact_path,
                "confirmed": list(continuity_pack.continuity_pack.confirmed),
                "assumptions": list(continuity_pack.continuity_pack.assumptions),
                "to_verify": list(continuity_pack.continuity_pack.to_verify),
                "recommended_next_test": list(continuity_pack.continuity_pack.recommended_next_test),
                "decision_snapshot": list(continuity_pack.continuity_pack.decision_snapshot),
            },
        }
        self._continuity_pack_path(case_id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_continuity_packs(self) -> None:
        for path in sorted(self._continuity_pack_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            request_payload = payload["request"]
            pack_payload = payload["continuity_pack"]
            case_id = path.stem
            self._continuity_packs[case_id] = ContinuityPackOutcome(
                request=ContinuityPackRequest(
                    title=str(request_payload["title"]),
                    source_artifact_path=str(request_payload["source_artifact_path"]),
                    confirmed=tuple(str(item) for item in request_payload.get("confirmed", [])),
                    assumptions=tuple(str(item) for item in request_payload.get("assumptions", [])),
                    to_verify=tuple(str(item) for item in request_payload.get("to_verify", [])),
                    recommended_next_test=tuple(
                        str(item) for item in request_payload.get("recommended_next_test", [])
                    ),
                    decision_snapshot=tuple(
                        str(item) for item in request_payload.get("decision_snapshot", [])
                    ),
                ),
                continuity_pack=ContinuityPack(
                    title=str(pack_payload["title"]),
                    source_artifact_path=str(pack_payload["source_artifact_path"]),
                    confirmed=tuple(str(item) for item in pack_payload.get("confirmed", [])),
                    assumptions=tuple(str(item) for item in pack_payload.get("assumptions", [])),
                    to_verify=tuple(str(item) for item in pack_payload.get("to_verify", [])),
                    recommended_next_test=tuple(
                        str(item) for item in pack_payload.get("recommended_next_test", [])
                    ),
                    decision_snapshot=tuple(
                        str(item) for item in pack_payload.get("decision_snapshot", [])
                    ),
                ),
            )

    def continuity_pack_persistence_status(self) -> ContinuityPackPersistenceStatus:
        """Return operational diagnostics for continuity-pack persistence."""

        return ContinuityPackPersistenceStatus(
            enabled=True,
            backend=self.__class__.__name__,
            root_dir=str(self._root_dir),
        )


__all__ = ["ContinuityPackPersistenceStatus", "FileBackedCaseRepository"]
