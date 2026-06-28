# SourceTrace v2 authority-relevance query handoff contract v1 — 2026-06-28

## Goal

Repair the planning/query-refinement -> retrieval handoff without changing downstream authority/relevance selection policy.

## Contract

Retrieval must consume a bounded search-intent string derived directly from the original user seed text.

For the current minimal v2 flow, that means:
- normalize the seed query into a single-line string,
- pass that normalized seed-derived string into retrieval,
- do not let planning/query-refinement freeform prose become the retrieval query.

## What changed

- `execute_minimal_research_flow(...)` now builds retrieval input from normalized `seed_text`
- retrieval no longer searches with the current `query_refinement` output blob
- persisted `evidence_query` now reflects the bounded handoff string used by retrieval

## Explicit non-goals

- no change to downstream selected-evidence policy
- no change to authority or relevance scoring
- no change to synthesis behavior beyond the corrected retrieval input

## Verification

Focused regression coverage now proves:
- retrieval receives the normalized seed-derived query even when the LLM emits assistant-style prose
- minimal-flow and provider-backed retrieval tests now assert the persisted `evidence_query` reflects that bounded handoff
