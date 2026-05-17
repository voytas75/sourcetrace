from sourcetrace.domain.types import (
    CredibilityBand,
    INFORMATION_CREDIBILITY_FIELD,
    ProvenanceDistance,
    SOURCE_RELIABILITY_FIELD,
)


def test_credibility_band_values() -> None:
    assert [band.value for band in CredibilityBand] == [
        "high",
        "medium",
        "low",
        "unknown",
    ]


def test_provenance_distance_values() -> None:
    assert [distance.value for distance in ProvenanceDistance] == [
        "primary",
        "near_primary",
        "secondary",
        "unknown",
    ]


def test_osint_credibility_field_names() -> None:
    assert SOURCE_RELIABILITY_FIELD == "source_reliability"
    assert INFORMATION_CREDIBILITY_FIELD == "information_credibility"
