from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CaseRecord:
    """Metadata-only root aggregate for a v2 investigation."""

    case_id: str
    title: str
    description: str | None = None


@dataclass(frozen=True)
class DocumentRecord:
    """Metadata-only source reference attached to one v2 case."""

    document_id: str
    case_id: str
    source_type: str
    source_locator: str
    title: str | None = None
