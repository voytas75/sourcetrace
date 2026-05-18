from dataclasses import FrozenInstanceError

import pytest

from sourcetrace.domain import RetrievalHit, RetrievalQuery, RetrievalResultSet
from sourcetrace.pipeline import ChunkRetriever, RetrievalExecution
from sourcetrace.pipeline.interfaces import ChunkRetriever as InterfacesChunkRetriever
from sourcetrace.pipeline.interfaces import (
    RetrievalExecution as InterfacesRetrievalExecution,
)


def test_pipeline_package_re_exports_retrieval_seams() -> None:
    assert ChunkRetriever is InterfacesChunkRetriever
    assert RetrievalExecution is InterfacesRetrievalExecution


def test_retrieval_execution_container_shape_is_frozen_dataclass() -> None:
    assert getattr(RetrievalExecution, "__dataclass_fields__", None) is not None
    assert tuple(RetrievalExecution.__dataclass_fields__) == ("retrieve_chunks",)

    def retrieve_chunks(query: RetrievalQuery) -> RetrievalResultSet:
        return RetrievalResultSet(query_id=query.query_id, case_id=query.case_id, hits=())

    execution = RetrievalExecution(retrieve_chunks=retrieve_chunks)

    with pytest.raises(FrozenInstanceError):
        setattr(execution, "retrieve_chunks", retrieve_chunks)


def test_chunk_retriever_is_protocol_type_with_callable_entrypoint() -> None:
    assert getattr(ChunkRetriever, "_is_protocol", False) is True
    assert callable(ChunkRetriever.__call__)


def test_retrieval_seam_returns_ranked_domain_result_set() -> None:
    query = RetrievalQuery(
        query_id="query-1",
        case_id="case-1",
        query_text="claim evidence query",
        requested_k=2,
        retrieval_method="hybrid",
    )

    def retrieve_chunks(request: RetrievalQuery) -> RetrievalResultSet:
        return RetrievalResultSet(
            query_id=request.query_id,
            case_id=request.case_id,
            hits=(
                RetrievalHit(
                    case_id=request.case_id,
                    document_id="doc-1",
                    chunk_id="chunk-1",
                    rank=1,
                    score=0.91,
                    query_text=request.query_text,
                    retrieval_method=request.retrieval_method,
                ),
            ),
            returned_k=1,
            retrieval_method=request.retrieval_method,
        )

    execution = RetrievalExecution(retrieve_chunks=retrieve_chunks)
    result = execution.retrieve_chunks(query)

    assert result.query_id == "query-1"
    assert tuple(hit.rank for hit in result.hits) == (1,)
    assert result.hits[0].retrieval_method == "hybrid"


def test_retrieval_ranking_stays_inside_retrieval_contract_for_now() -> None:
    import sourcetrace.pipeline.interfaces as interfaces

    assert "EvidenceRanker" not in interfaces.__all__
