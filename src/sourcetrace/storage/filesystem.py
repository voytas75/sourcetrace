"""Filesystem-backed persistence adapters for lightweight local durability."""

import json
from contextlib import suppress
from dataclasses import asdict, dataclass
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
            "active": _continuity_pack_outcome_payload(continuity_pack),
            "latest_previous": _continuity_pack_outcome_payload(
                self.get_latest_previous_continuity_pack(case_id)
            ),
        }
        self._continuity_pack_path(case_id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_continuity_packs(self) -> None:
        for path in sorted(self._continuity_pack_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            case_id = path.stem
            active_payload = payload.get("active")
            latest_previous_payload = payload.get("latest_previous")

            if active_payload is not None:
                self._continuity_packs[case_id] = _continuity_pack_outcome_from_payload(active_payload)
            if latest_previous_payload is not None:
                self._latest_previous_continuity_packs[case_id] = _continuity_pack_outcome_from_payload(
                    latest_previous_payload
                )

    def continuity_pack_persistence_status(self) -> ContinuityPackPersistenceStatus:
        """Return operational diagnostics for continuity-pack persistence."""

        return ContinuityPackPersistenceStatus(
            enabled=True,
            backend=self.__class__.__name__,
            root_dir=str(self._root_dir),
        )

    def clear_continuity_pack(self, case_id: str) -> None:
        super().clear_continuity_pack(case_id)
        with suppress(FileNotFoundError):
            self._continuity_pack_path(case_id).unlink()


def _continuity_pack_outcome_payload(
    continuity_pack: ContinuityPackOutcome | None,
) -> dict[str, object] | None:
    if continuity_pack is None:
        return None
    return {
        "request": asdict(continuity_pack.request),
        "continuity_pack": asdict(continuity_pack.continuity_pack),
    }


def _continuity_pack_outcome_from_payload(
    payload: dict[str, object],
) -> ContinuityPackOutcome:
    request_payload = payload["request"]
    pack_payload = payload["continuity_pack"]
    if not isinstance(request_payload, dict) or not isinstance(pack_payload, dict):
        raise ValueError("Continuity-pack persistence payload must include request and continuity_pack objects.")
    return ContinuityPackOutcome(
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


__all__ = ["ContinuityPackPersistenceStatus", "FileBackedCaseRepository"]
