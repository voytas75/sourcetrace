# SourceTrace v2 trust metadata contract — 2026-07-19

## Decision

The operator trust projection must not infer jurisdiction from a URL host, title, public suffix, or a differing institutional authority. Those are source cues, not legal or administrative scope evidence.

`jurisdiction_mixed_selected_institutional_pair` is emitted only when each selected institutional source carries an explicit, sufficiently confident `jurisdiction_id` and the normalized identifiers differ.

## Contract

`SourceTraceTrustMetadata` is an optional provider-neutral context carried from a retrieved candidate into compiled selected evidence:

- `authority_id` — stable authority or organization identifier, when known;
- `jurisdiction_id` — normalized jurisdiction identifier, when known;
- `scope` — for example `national`, `regional`, `local`, `supranational`, `multi`, or `unknown`;
- `provenance` — how the metadata was established;
- `confidence` — `high`, `medium`, `low`, or `unassessed`.

Only non-empty `jurisdiction_id` values with `high` or `medium` confidence participate in the mismatch rule. Different `authority_id` values alone never imply a jurisdiction mismatch. Missing or unassessed metadata is deliberately non-blocking.

Metadata is persisted in result and compiled JSONL artifacts and exposed through selected-evidence and compiled-artifact projections. Existing JSONL rows without it remain compatible and load as `None`.

## Deliberate boundary

This slice adds no country/domain table, public-suffix inference, external identity service, or automatic resolver. Current search adapters leave the context unassessed by default. That is a precision-first trade-off: SourceTrace stops making false jurisdiction claims but does not yet detect every real cross-jurisdiction pair.
