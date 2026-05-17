from dataclasses import FrozenInstanceError, is_dataclass

import pytest

from sourcetrace.domain.chunks import DocumentChunk


def test_document_chunk_is_importable_from_chunks_module() -> None:
    import sourcetrace.domain.chunks as chunks

    assert chunks.DocumentChunk is DocumentChunk


def test_document_chunk_stores_core_chunk_metadata() -> None:
    chunk = DocumentChunk(
        chunk_id="chunk-1",
        case_id="case-1",
        document_id="doc-1",
        raw_text="The bridge reopened on May 17, 2026.",
        start_char=128,
        end_char=168,
        chunk_index=3,
        position_reference="page=2;paragraph=4",
        previous_chunk_id="chunk-0",
        next_chunk_id="chunk-2",
    )

    assert is_dataclass(chunk)
    assert chunk.chunk_id == "chunk-1"
    assert chunk.case_id == "case-1"
    assert chunk.document_id == "doc-1"
    assert chunk.raw_text == "The bridge reopened on May 17, 2026."
    assert chunk.start_char == 128
    assert chunk.end_char == 168
    assert chunk.chunk_index == 3
    assert chunk.position_reference == "page=2;paragraph=4"
    assert chunk.previous_chunk_id == "chunk-0"
    assert chunk.next_chunk_id == "chunk-2"


def test_document_chunk_sequence_links_default_to_absent() -> None:
    chunk = DocumentChunk(
        chunk_id="chunk-1",
        case_id="case-1",
        document_id="doc-1",
        raw_text="One short standalone chunk.",
        start_char=0,
        end_char=27,
        chunk_index=0,
    )

    assert chunk.position_reference is None
    assert chunk.previous_chunk_id is None
    assert chunk.next_chunk_id is None


def test_document_chunk_is_frozen() -> None:
    chunk = DocumentChunk(
        chunk_id="chunk-1",
        case_id="case-1",
        document_id="doc-1",
        raw_text="One short standalone chunk.",
        start_char=0,
        end_char=27,
        chunk_index=0,
    )

    with pytest.raises(FrozenInstanceError):
        chunk.raw_text = "Updated text."
