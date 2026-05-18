"""Lower-level pipeline dependency interfaces."""

from dataclasses import dataclass
from typing import Protocol

from sourcetrace.domain.retrieval import RetrievalQuery, RetrievalResultSet


class ChunkRetriever(Protocol):
    """Retrieval seam for returning ranked evidence candidates for a query."""

    def __call__(self, query: RetrievalQuery) -> RetrievalResultSet:
        ...


@dataclass(frozen=True)
class RetrievalExecution:
    """Retrieval seam bundle for explicit callable dependency wiring."""

    retrieve_chunks: ChunkRetriever


__all__ = [
    "ChunkRetriever",
    "RetrievalExecution",
]
