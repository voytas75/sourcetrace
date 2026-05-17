"""Retrieval result domain records."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalQuery:
    """Minimal retrieval request metadata without execution behavior."""

    query_id: str
    case_id: str
    query_text: str
    requested_k: int
    retrieval_method: str | None = None
    document_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RetrievalHit:
    """Retrieved chunk candidate metadata without retrieval behavior."""

    case_id: str
    document_id: str
    chunk_id: str
    rank: int
    snippet: str | None = None
    score: float | None = None
    query_text: str | None = None
    retrieval_method: str | None = None


@dataclass(frozen=True)
class RetrievalResultSet:
    """Minimal retrieval outcome metadata without execution behavior."""

    query_id: str
    case_id: str
    hits: tuple[RetrievalHit, ...]
    returned_k: int | None = None
    retrieval_method: str | None = None


__all__ = [
    "RetrievalHit",
    "RetrievalQuery",
    "RetrievalResultSet",
]
