# SourceTrace v2 live LLM runtime path v1 — 2026-06-28

## Goal

Turn the current LLM seam into a real env-backed runtime path without breaking provider-agnostic config posture.

## What changed

- opened a separate `v2-production-readiness-track`
- added `provider_model_id` to `RuntimeProfile`
- mapped Azure profiles through provider-specific model ids instead of assuming raw logical model names are provider-ready
- added a real LiteLLM-backed live runtime path
- fixed `research_fast` compatibility for Azure `gpt-5.4-mini` by setting a compatible profile temperature in config (`1.0`)

## Why this is still provider-agnostic enough

- logical model names remain in config
- provider-specific model/deployment ids now live in config too
- the adapter chooses provider call shape from profile data instead of hardcoding Azure-only names into the core flow

## Verification posture

Expected verification for this slice:
- focused runtime-path tests pass
- bounded live smoke run should get farther than the earlier planning-only pass and ideally complete end-to-end

## Out of scope

- PDF/document read seam
- broader provider fan-out
- packaging/deployment polish
- evidence-policy changes
