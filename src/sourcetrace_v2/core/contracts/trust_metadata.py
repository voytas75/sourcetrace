from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceTraceTrustMetadata:
    """Optional provider-neutral identity and scope evidence for operator trust."""

    authority_id: str = ""
    jurisdiction_id: str = ""
    scope: str = "unknown"
    provenance: str = "unassessed"
    confidence: str = "unassessed"
