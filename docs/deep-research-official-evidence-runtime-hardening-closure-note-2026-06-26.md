# Deep Research official-evidence runtime hardening closure note — 2026-06-26

## Goal
Stabilize SourceTrace official/public-law evidence handling so canonical official pages survive retrieval, selection, packing, and user-facing source projection.

## What changed
- Added LLM-backed official-evidence judging for official/public-law search hits.
- Propagated official evidence verdicts through pre-extraction, extracted findings, and evidence packing.
- Added LLM-backed official family consolidation to separate canonical official pages from collateral official pages.
- Added runtime trace for:
  - query path selection
  - official evidence verdicts
  - family activation
  - family consolidation output
- Hardened final packer so official collateral pages cannot enter `core`.
- Fixed user-facing `result.sources` ordering so canonical official case pages appear before collateral PDFs and before media/generic noise.
- Cleaned report-generation test debt and refreshed official/institutional query-shaping expectations.
- Added `tmp/README.md` to document ad hoc validation helpers.

## Key bounded slices completed
- official_supporting_hygiene_v1
- official_query_shaping_v1
- official_query_path_trace_v1
- official_public_law_procedural_bridge_v1
- official provider relevance rescue v1
- llm_official_evidence_judge_v1
- llm_official_evidence_judge_enforcement_v1
- llm_official_evidence_packing_v1
- llm_official_evidence_family_consolidation_v1
- llm_official_evidence_family_runtime_wiring_v1
- family_consolidation_trace_v1
- canonical_family_enforcement_in_packer_v1
- official_first_sources_ordering_v1
- canonical_sources_projection_v1

## Live validation summary
Three sequential live validation runs were used as the final regression sweep.

### 1. Tax / MF-KAS / podatki.gov.pl
Outcome:
- canonical official tax pages surfaced first
- official tax core was correct
- family trace activated

### 2. GetBack / NIK
Outcome:
- canonical official case pages reached `core`
- collateral official pages were removed from `core`
- final visible sources no longer started with media or collateral PDFs
- family activation and consolidation trace worked live

### 3. Afera podkarpacka / prokuratura
Outcome:
- correct official prosecution source remained first
- family trace count was zero, which was acceptable because no meaningful official family needed consolidation

## Current status
This front is operationally stable enough to pause.

What is now true:
- official/public-law query routing is no longer the main blocker
- canonical official pages can win retrieval-to-core-to-sources end-to-end
- family consolidation is active live and traceable
- collateral official pages are prevented from polluting `core`
- user-facing `result.sources` now better reflects the official-first outcome

## Remaining non-blocking quality gap
Small remaining polish item:
- ordering within an already-good official family can still be slightly non-ideal in some cases (for example, two good NIK pages where page #1 vs #2 could still be refined)

This is not considered a blocker.

## Small cleanup completed after hardening
- report prompt test alignment fixed
- official/institutional query-variant regression expectations refreshed
- `tmp/README.md` added

## Recommended next posture
Do not keep pushing this same front blindly.

Reasonable next options:
1. leave a small polish ticket for intra-family canonical ordering
2. move to the next larger SourceTrace bottleneck
3. revisit provider-side official retrieval quality later only if fresh evidence shows regression
