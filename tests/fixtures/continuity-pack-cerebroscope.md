# SourceTrace Research Continuity Pack — alternative active pack

Source artifact: `tests/fixtures/source-artifact.md`

## Potwierdzone
- Alternative continuity-pack fixture exists for replace/clear case flows.
- This fixture represents the secondary active pack used in tests instead of a public docs artifact.

## Przypuszczenia
- Replacing the active pack should preserve latest-previous continuity-pack history.

## Do weryfikacji
- Whether a richer source-artifact label is ever needed for UI assertions.

## Recommended next test
- Reassign this fixture after Reuters A1 and confirm latest-previous state still points to the prior public artifact.

## Decision snapshot
- Use fixture-backed alternative packs for replace-path tests; keep public docs focused on repo-facing artifacts.
