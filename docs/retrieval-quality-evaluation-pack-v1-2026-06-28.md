# SourceTrace v2 retrieval quality evaluation pack v1 — 2026-06-28

## Goal

Run a broader live retrieval-quality pack across representative queries and identify where the current retrieval path is already healthy versus still unstable.

This slice is evaluation/stabilization, not a new heuristic patch.

## Live pack

Queries checked:
- break glass account guidance conditional access official best practice
- data breach notification checklist authority official guidance
- legal hold steps records retention official guidance
- remote work reporting obligations Poland employer official guidance
- records retention policy official guidance public sector
- incident response plan official guidance public sector
- official tax filing deadline guidance for small business
- cross border data transfer official guidance

## Main results

### Clearly healthy / mostly healthy
- **breach notification**
  - institutional / institutional pair
  - strong shape
- **records retention policy**
  - institutional / institutional pair
  - healthy shape
- **incident response**
  - institutional / institutional pair
  - strong shape
- **break-glass**
  - official source survives clearly
  - second source remains weaker/non-institutional, but the overall shape is still acceptable

### Still unstable / weak
- **legal hold**
  - this run fell back to vendor / vendor again
  - retrieval quality is not stable enough yet for this case
- **remote-work Poland**
  - this run stayed advisory/commercial rather than public-institutional
  - still unstable
- **cross-border data transfer**
  - selected pair was advisory/commercial rather than clearly official/institutional
  - this is a real weak case, not just a cosmetic one

### Ambiguous / needs better targeting
- **tax deadline guidance for small business**
  - both selected hits were institutional, but they were jurisdictionally mixed (`IRS` + `SARS`)
  - this is not a clean failure, but it shows retrieval is still weak on jurisdiction targeting / answer-shape discipline

## Important interpretation

### 1. Retrieval quality is genuinely mixed, not simply bad everywhere
There are now multiple representative cases where the retrieval path is clearly healthy enough.
That matters.
The system is no longer failing in a uniformly broad way.

### 2. The remaining failures are still mostly retrieval-side, not selector-side
The weak cases continue to look like poor candidate-pool composition or weak jurisdiction/topic targeting.
This does **not** point back to selector surgery as the first move.

### 3. The current trust contract is useful but still shallow
A notable observation from this pack:
- some clearly weak retrieval shapes still surfaced as `usable`
- others came through as `weak` mainly because of degraded LLM calls, not because retrieval quality itself was poor

Interpretation:
- the current trust contract improves honesty, but it is still only a first pass
- it is not yet strongly aligned with retrieval/evidence quality

## Practical verdict

The next best bounded move is **not** another generic retrieval heuristic patch.
It is also **not** immediate trust-policy expansion in the abstract.

The sharpest next step is:
- strengthen the quality baseline so these unstable cases are pinned more explicitly,
- then use that stronger baseline to decide the next retrieval refinement without drifting into local heuristic patches.

## Recommended next bounded slice

`quality-regression-pack-v2`

Goal:
- expand the regression pack with the newly exposed unstable/ambiguous live cases:
  - legal hold fallback to vendor/vendor
  - remote-work Poland instability
  - cross-border data transfer advisory/commercial drift
  - jurisdiction-mixed tax deadline result shape
- make the next retrieval refinement decision against a stronger shared baseline instead of another anecdotal live check
