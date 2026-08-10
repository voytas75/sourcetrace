from sourcetrace_v2.adapters.search.unified_search import (
    UnifiedSearchBootstrap,
    UnifiedSearchGateway,
)


def test_unified_search_gateway_skips_non_mapping_rows() -> None:
    def raw_rows(_: str, *, count: int) -> object:
        return [
            {"url": "https://example.test/valid", "title": "Valid"},
            "not-a-result-mapping",
        ]

    bootstrap = UnifiedSearchBootstrap(search_web=raw_rows)
    gateway = UnifiedSearchGateway(bootstrap=bootstrap)

    candidates = gateway.search(job_id="j", run_id="r", query="q", limit=2)

    assert [candidate.url for candidate in candidates] == ["https://example.test/valid"]
