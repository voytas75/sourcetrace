# SourceTrace v2 authority-relevance source-mix shaping v1 — 2026-06-28

## Goal

Make one bounded upstream change that improves the odds that official/institutional candidates survive into the bounded candidate pool for queries that explicitly imply official/institutional intent.

This slice stays upstream.
It does not change downstream selected-evidence policy.

## Change made

Added a narrow source-mix shaping step in `RetrievalStage`.

Behavior:
- only activates when the query text implies official/institutional intent (for example: `official`, `authority`, `guidance`, `regulation`, `policy`, `commission`, `ministry`)
- lightly reorders retrieval candidates before later promotion/selection
- prefers candidates whose source/host looks more institutional (for example: `.gov`, `europa.eu`, `archives.gov`, `ftc.gov`, `ico.org.uk`, `learn.microsoft.com`)
- preserves a bounded shape by re-ranking only the retrieved candidate tuple; it does not change the selected-evidence contract or judgment dimensions

## Why this is the right scope

The previous diagnostics showed:
- query handoff drift was already repaired
- remaining weak live cases were caused by source-mix / source-ordering under plain retrieval
- institutional candidates sometimes existed in raw provider output but lost before they could reliably survive top-N and later selection

So the smallest honest next move was to shape the candidate pool upstream, not add more downstream selector heuristics.

## Verification

### Focused tests
Focused shaping and regression tests passed:
- `tests/unit/v2/test_source_mix_shaping.py`
- `tests/unit/v2/test_query_handoff_contract.py`
- `tests/unit/v2/test_minimal_flow.py`

Result: `4 passed`

### Live check
Ran a small live check on two representative queries.

#### Breach notification
Selected remained strong and institutional:
- FTC breach response guide
- ICO personal data breaches guide

Interpretation:
- no regression on the strongest case

#### Legal hold steps
Selected changed to:
- OpenText practical legal-holds PDF
- Venio legal-hold best-practices guide

Interpretation:
- still not a clearly public-institutional pair
- but the top item shifted toward a more document-like/structured result rather than the previous commentary-only practical stack
- this suggests the shaping move has some effect, but does not by itself fully solve institutional-source scarcity/ranking for this topic class

## Practical verdict

This slice is useful and bounded.
It improves upstream candidate shaping for official-intent queries without contaminating downstream selector policy.

It is also not the end-state.
The remaining gap is now narrower:
- source classification is still very shallow
- institutional preference is still approximate
- some topic classes still need stronger official-source survival than this first shaping pass guarantees

## Recommended next bounded slice

`authority-relevance-source-typing-v1`

Goal:
- add explicit source-type metadata (institutional / vendor / commentary / unknown) early enough to support cleaner upstream shaping and diagnostics
- keep selector policy unchanged in the same slice
