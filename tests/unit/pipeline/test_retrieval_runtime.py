from sourcetrace.domain import DocumentChunk, RetrievalQuery
from sourcetrace.pipeline import LexicalChunkRetriever, RetrievalExecution
from sourcetrace.pipeline.retrieval import LexicalChunkRetriever as ModuleLexicalChunkRetriever
from sourcetrace.storage import create_in_memory_persistence


def test_pipeline_package_re_exports_lexical_retrieval_runtime() -> None:
    assert LexicalChunkRetriever is ModuleLexicalChunkRetriever


def test_lexical_chunk_retriever_ranks_persisted_chunks_by_overlap() -> None:
    persistence = create_in_memory_persistence()
    persistence.documents.save_chunks(
        (
            DocumentChunk(
                chunk_id="chunk-1",
                case_id="case-1",
                document_id="doc-1",
                raw_text="The bridge inspection report says repairs are pending.",
                start_char=0,
                end_char=56,
                chunk_index=1,
            ),
            DocumentChunk(
                chunk_id="chunk-2",
                case_id="case-1",
                document_id="doc-1",
                raw_text="Officials confirmed the bridge reopened after repairs.",
                start_char=57,
                end_char=112,
                chunk_index=2,
            ),
            DocumentChunk(
                chunk_id="chunk-3",
                case_id="case-1",
                document_id="doc-2",
                raw_text="Airport service expanded on Monday.",
                start_char=0,
                end_char=35,
                chunk_index=1,
            ),
        )
    )
    retriever = LexicalChunkRetriever(documents=persistence.documents)
    execution = RetrievalExecution(retrieve_chunks=retriever)

    result = execution.retrieve_chunks(
        RetrievalQuery(
            query_id="query-1",
            case_id="case-1",
            query_text="bridge reopened after repairs",
            requested_k=2,
            retrieval_method="runtime-lexical",
            document_ids=("doc-1",),
        )
    )

    assert result.returned_k == 2
    assert result.retrieval_method == "runtime-lexical"
    assert tuple(hit.chunk_id for hit in result.hits) == ("chunk-2", "chunk-1")
    assert tuple(hit.rank for hit in result.hits) == (1, 2)
    assert result.hits[0].score > result.hits[1].score
    assert result.hits[0].snippet == "Officials confirmed the bridge reopened after repairs."


def test_lexical_chunk_retriever_can_search_all_case_chunks_for_in_memory_storage() -> None:
    persistence = create_in_memory_persistence()
    persistence.documents.save_chunks(
        (
            DocumentChunk(
                chunk_id="chunk-1",
                case_id="case-1",
                document_id="doc-1",
                raw_text="The bridge reopened after safety checks.",
                start_char=0,
                end_char=41,
                chunk_index=1,
            ),
            DocumentChunk(
                chunk_id="chunk-2",
                case_id="case-2",
                document_id="doc-2",
                raw_text="The bridge reopened in another case.",
                start_char=0,
                end_char=38,
                chunk_index=1,
            ),
        )
    )

    result = LexicalChunkRetriever(documents=persistence.documents)(
        RetrievalQuery(
            query_id="query-1",
            case_id="case-1",
            query_text="bridge reopened",
            requested_k=5,
        )
    )

    assert tuple(hit.chunk_id for hit in result.hits) == ("chunk-1",)
