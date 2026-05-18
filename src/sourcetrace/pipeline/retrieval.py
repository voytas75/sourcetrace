"""Minimal retrieval runtime implementations."""

import re
from dataclasses import dataclass

from sourcetrace.domain.chunks import DocumentChunk
from sourcetrace.domain.retrieval import RetrievalHit, RetrievalQuery, RetrievalResultSet
from sourcetrace.storage.interfaces import DocumentRepository


_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class LexicalChunkRetriever:
    """Rank persisted chunks with a small lexical overlap score."""

    documents: DocumentRepository
    retrieval_method: str = "lexical"
    snippet_chars: int = 240

    def __call__(self, query: RetrievalQuery) -> RetrievalResultSet:
        candidates = self._candidate_chunks(query)
        query_terms = _tokenize(query.query_text)
        scored_chunks = tuple(
            (score, chunk)
            for chunk in candidates
            if (score := _score_chunk(query_terms, chunk)) > 0
        )
        ranked_chunks = sorted(
            scored_chunks,
            key=lambda item: (-item[0], item[1].document_id, item[1].chunk_index),
        )
        requested = max(query.requested_k, 0)
        method = query.retrieval_method or self.retrieval_method
        hits = tuple(
            RetrievalHit(
                case_id=chunk.case_id,
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                rank=rank,
                snippet=_snippet(chunk.raw_text, self.snippet_chars),
                score=score,
                query_text=query.query_text,
                retrieval_method=method,
            )
            for rank, (score, chunk) in enumerate(ranked_chunks[:requested], start=1)
        )
        return RetrievalResultSet(
            query_id=query.query_id,
            case_id=query.case_id,
            hits=hits,
            returned_k=len(hits),
            retrieval_method=method,
        )

    def _candidate_chunks(self, query: RetrievalQuery) -> tuple[DocumentChunk, ...]:
        if query.document_ids:
            chunks_by_id: dict[str, DocumentChunk] = {}
            for document_id in query.document_ids:
                for chunk in self.documents.list_chunks_for_document(
                    query.case_id,
                    document_id,
                ):
                    chunks_by_id.setdefault(chunk.chunk_id, chunk)
            return tuple(
                sorted(
                    chunks_by_id.values(),
                    key=lambda chunk: (chunk.document_id, chunk.chunk_index),
                )
            )

        list_chunks_for_case = getattr(self.documents, "list_chunks_for_case", None)
        if callable(list_chunks_for_case):
            return tuple(list_chunks_for_case(query.case_id))
        return ()


def _tokenize(text: str) -> frozenset[str]:
    return frozenset(_TOKEN_PATTERN.findall(text.lower()))


def _score_chunk(query_terms: frozenset[str], chunk: DocumentChunk) -> float:
    if not query_terms:
        return 0.0
    chunk_terms = _tokenize(chunk.raw_text)
    if not chunk_terms:
        return 0.0
    overlap = query_terms & chunk_terms
    return len(overlap) / len(query_terms)


def _snippet(text: str, max_chars: int) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max(max_chars - 3, 0)].rstrip() + "..."


__all__ = [
    "LexicalChunkRetriever",
]
