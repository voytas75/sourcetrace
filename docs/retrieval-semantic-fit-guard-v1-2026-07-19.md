# SourceTrace v2 retrieval semantic-fit guard v1 — 2026-07-19

## What changed

SourceTrace v2 now persists the shaped retrieval pool from just before bounded trim and records a small semantic-fit diagnostic block alongside the trimmed evidence candidates.

The diagnostic is intentionally lexical and provider-neutral:

- use only generic semantic focus terms from the query after removing explicit search-operator clauses;
- score only whether any candidate in the pool covers enough of those focus terms;
- mark insufficiency as `upstream_candidate_pool` only when the pre-trim shaped pool itself is explicitly insufficient;
- mark `downstream_selection` only when the pre-trim pool is sufficient but the bounded trimmed window is not.

## Trust boundary

This guard is transparent only. It does not retry retrieval, reshape the query, or alter trimmed/selected evidence behavior.

Operator trust now uses exactly `retrieval_insufficient_semantic_fit` only for the explicit upstream pre-trim insufficiency case. Downstream selection issues remain diagnostic information rather than a new trust reason.

## Persistence and readback

- `ResearchResultArtifact` now carries both trimmed `evidence_candidates` and `pretrim_evidence_candidates`
- JSONL result persistence round-trips the new fields
- old JSONL rows still load, with the pre-trim pool projected from the legacy trimmed candidates and diagnostics left unavailable rather than fabricated
