# SourceTrace v2 operator start here — 2026-06-27

## Start here

If you are resuming SourceTrace v2 work in a fresh session, read in this order:

1. `docs/STATUS.md`
2. `docs/sourcetrace-v2-release-closure-note-2026-06-27.md`
3. `docs/sourcetrace-v2-closure-packaging-checkpoint-2026-06-27.md`
4. `docs/sourcetrace-v2-evidence-policy-baseline-freeze-2026-06-27.md`

Then decide which of these modes you are in:
- **closure/packaging mode** — stay inside the bounded v2 baseline
- **post-baseline mode** — open a new named expansion track on purpose

## Current default posture

Default posture is:
- `sourcetrace_v2` is the active implementation line,
- v1 / deep-research runtime docs are legacy/reference,
- evidence-selection baseline is frozen,
- do not add policy heuristics by default.

## If continuing in closure/packaging mode

Allowed/default work:
- docs polish,
- restartability improvements,
- active-docs cleanup,
- small operator-facing packaging notes,
- bounded regression maintenance.

Avoid by default:
- new policy heuristics,
- broad provider expansion,
- v1 parity work,
- reopening architecture scope.

## If opening a post-baseline track

Name the track explicitly first.
Examples:
- authority/relevance policy track
- broader provider track
- product/runtime packaging track

Do not smuggle expansion work into the bounded closure line.

## One-line summary

Current v2 status: **bounded baseline closed enough; continue only with packaging polish or an explicitly named new track.**
