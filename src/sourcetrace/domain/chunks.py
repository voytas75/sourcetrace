"""Document chunk domain records."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentChunk:
    """Addressable document fragment used for retrieval and evidence links."""

    chunk_id: str
    case_id: str
    document_id: str
    raw_text: str
    start_char: int
    end_char: int
    chunk_index: int
    position_reference: str | None = None
    previous_chunk_id: str | None = None
    next_chunk_id: str | None = None


__all__ = [
    "DocumentChunk",
]
