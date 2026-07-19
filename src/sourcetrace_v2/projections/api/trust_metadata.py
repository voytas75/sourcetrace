from __future__ import annotations

from sourcetrace_v2.core.contracts.trust_metadata import SourceTraceTrustMetadata


def project_trust_metadata(metadata: SourceTraceTrustMetadata | None) -> dict[str, object] | None:
    if metadata is None:
        return None
    return {
        "authority_id": metadata.authority_id,
        "jurisdiction_id": metadata.jurisdiction_id,
        "scope": metadata.scope,
        "provenance": metadata.provenance,
        "confidence": metadata.confidence,
    }
