# SourceTrace docs posture — v2 active, v1 legacy (2026-06-27)

## Purpose

Make the current docs stance explicit:
- `sourcetrace_v2` is the active implementation line,
- current `deep research` / v1 runtime docs are legacy reference material,
- legacy docs remain useful for migration context and operator history, but should stop reading like the forward path.

## Active line

Treat these as the active implementation track:
- `docs/STATUS.md`
- `docs/sourcetrace-v2-full-closure-map-2026-06-27.md`
- `docs/sourcetrace-v2-broader-migration-plan-2026-06-27.md`
- `docs/sourcetrace-v2-*.md` created during the 2026-06-27 v2 slices
- `src/sourcetrace_v2/**`

## Legacy line

Treat these as legacy/reference unless explicitly needed for migration or live-runtime support:
- current `deep-research-*` implementation/history notes
- `docs/deep-research-status-checkpoint-2026-06-22.md`
- v1 local-launcher / current-runtime operator notes
- `src/sourcetrace/**` runtime internals outside bounded migration lookup

## Practical reading rule

When deciding what to build next:
1. start from `docs/STATUS.md`
2. then `docs/sourcetrace-v2-full-closure-map-2026-06-27.md`
3. then the relevant `docs/sourcetrace-v2-*` contract/brief/checkpoint note
4. use v1/deep-research docs only as legacy reference or migration evidence

## Non-goal

This posture does **not** delete or rewrite the legacy docs corpus yet.
It only makes the active-vs-legacy split explicit so future work stops reading the whole repo as one equally-current documentation surface.
