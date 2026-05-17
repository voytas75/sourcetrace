from dataclasses import FrozenInstanceError, is_dataclass

import pytest

from sourcetrace.domain.retrieval import RetrievalHit, RetrievalQuery, RetrievalResultSet


def test_retrieval_query_is_importable_from_retrieval_module() -> None:
    import sourcetrace.domain.retrieval as retrieval

    assert retrieval.RetrievalQuery is RetrievalQuery


def test_retrieval_query_stores_minimal_request_metadata() -> None:
    query = RetrievalQuery(
        query_id="query-1",
        case_id="case-1",
        query_text="bridge reopening date",
        requested_k=5,
        retrieval_method="keyword",
        document_ids=("doc-1", "doc-2"),
    )

    assert is_dataclass(query)
    assert query.query_id == "query-1"
    assert query.case_id == "case-1"
    assert query.query_text == "bridge reopening date"
    assert query.requested_k == 5
    assert query.retrieval_method == "keyword"
    assert query.document_ids == ("doc-1", "doc-2")


def test_retrieval_query_optional_fields_default_to_absent() -> None:
    query = RetrievalQuery(
        query_id="query-1",
        case_id="case-1",
        query_text="bridge reopening date",
        requested_k=5,
    )

    assert query.retrieval_method is None
    assert query.document_ids == ()


def test_retrieval_query_stores_document_filter_as_tuple() -> None:
    query = RetrievalQuery(
        query_id="query-1",
        case_id="case-1",
        query_text="bridge reopening date",
        requested_k=5,
        document_ids=("doc-1",),
    )

    assert query.document_ids == ("doc-1",)


def test_retrieval_query_is_frozen() -> None:
    query = RetrievalQuery(
        query_id="query-1",
        case_id="case-1",
        query_text="bridge reopening date",
        requested_k=5,
    )

    with pytest.raises(FrozenInstanceError):
        query.requested_k = 10


def test_retrieval_hit_is_importable_from_retrieval_module() -> None:
    import sourcetrace.domain.retrieval as retrieval

    assert retrieval.RetrievalHit is RetrievalHit


def test_retrieval_hit_stores_minimal_candidate_metadata() -> None:
    hit = RetrievalHit(
        case_id="case-1",
        document_id="doc-1",
        chunk_id="chunk-1",
        rank=1,
        snippet="The bridge reopened on May 17, 2026.",
        score=0.91,
        query_text="bridge reopening date",
        retrieval_method="keyword",
    )

    assert is_dataclass(hit)
    assert hit.case_id == "case-1"
    assert hit.document_id == "doc-1"
    assert hit.chunk_id == "chunk-1"
    assert hit.rank == 1
    assert hit.snippet == "The bridge reopened on May 17, 2026."
    assert hit.score == 0.91
    assert hit.query_text == "bridge reopening date"
    assert hit.retrieval_method == "keyword"


def test_retrieval_hit_optional_fields_default_to_absent() -> None:
    hit = RetrievalHit(
        case_id="case-1",
        document_id="doc-1",
        chunk_id="chunk-1",
        rank=2,
    )

    assert hit.snippet is None
    assert hit.score is None
    assert hit.query_text is None
    assert hit.retrieval_method is None


def test_retrieval_hit_is_frozen() -> None:
    hit = RetrievalHit(
        case_id="case-1",
        document_id="doc-1",
        chunk_id="chunk-1",
        rank=1,
    )

    with pytest.raises(FrozenInstanceError):
        hit.rank = 2


def test_retrieval_result_set_is_importable_from_retrieval_module() -> None:
    import sourcetrace.domain.retrieval as retrieval

    assert retrieval.RetrievalResultSet is RetrievalResultSet


def test_retrieval_result_set_stores_minimal_outcome_metadata() -> None:
    hit = RetrievalHit(
        case_id="case-1",
        document_id="doc-1",
        chunk_id="chunk-1",
        rank=1,
    )
    result_set = RetrievalResultSet(
        query_id="query-1",
        case_id="case-1",
        hits=(hit,),
        returned_k=1,
        retrieval_method="keyword",
    )

    assert is_dataclass(result_set)
    assert result_set.query_id == "query-1"
    assert result_set.case_id == "case-1"
    assert result_set.hits == (hit,)
    assert result_set.returned_k == 1
    assert result_set.retrieval_method == "keyword"


def test_retrieval_result_set_stores_hits_as_tuple() -> None:
    first_hit = RetrievalHit(
        case_id="case-1",
        document_id="doc-1",
        chunk_id="chunk-1",
        rank=1,
    )
    second_hit = RetrievalHit(
        case_id="case-1",
        document_id="doc-2",
        chunk_id="chunk-2",
        rank=2,
    )
    result_set = RetrievalResultSet(
        query_id="query-1",
        case_id="case-1",
        hits=(first_hit, second_hit),
    )

    assert result_set.hits == (first_hit, second_hit)


def test_retrieval_result_set_optional_fields_default_to_absent() -> None:
    result_set = RetrievalResultSet(
        query_id="query-1",
        case_id="case-1",
        hits=(),
    )

    assert result_set.returned_k is None
    assert result_set.retrieval_method is None


def test_retrieval_result_set_is_frozen() -> None:
    result_set = RetrievalResultSet(
        query_id="query-1",
        case_id="case-1",
        hits=(),
    )

    with pytest.raises(FrozenInstanceError):
        result_set.returned_k = 1
