# Continuity pack with diagnostics

Source artifact: `tests/fixtures/source-artifact.md`

## Potwierdzone
- Fixture-backed continuity pack can render verification diagnostics in HTML.

## Przypuszczenia
- The fixture is sufficient to keep decision-support rendering stable.

## Do weryfikacji
- Whether richer fixture coverage is needed later.

## Recommended next test
- Keep one fixture-backed render path that exercises verification diagnostics before changing the continuity-pack view contract.

## Verification diagnostics
- Support rationale counts: exact lexical match=1
- Contradiction diagnostics: contradicted claim count=0

## Decision snapshot
- Keep diagnostics visible before decision snapshot in the rendered view.
