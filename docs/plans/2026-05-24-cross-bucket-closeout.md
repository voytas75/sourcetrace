# SourceTrace real-data campaign closeout — cross-bucket verdict after Bucket B prompt grouping fix

Status: cross-bucket refresh after Bucket A / B / C checkpoints, B3 debug capture, prompt grouping fix, post-fix B2-style rerun, B1 post-fix confirmation rerun, and credibility inline continuity slice
Parent SSOT: `docs/plans/2026-05-21-real-data-test-use-ssot.md`
Related checkpoints:
- `docs/plans/2026-05-23-bucket-a-checkpoint.md`
- `docs/plans/2026-05-23-bucket-b-checkpoint.md`
- `docs/plans/2026-05-23-bucket-c-checkpoint.md`

## Executive decision
The current SourceTrace test-use state is **usable-with-caveats across Buckets A, B, and C**.

The product is no longer showing evidence of broad assistant-style drift or wholesale attribution collapse in these tested families. The dominant remaining weaknesses are now narrower and more product-shape-specific:
- Bucket A: factual over-splitting / granularity smoothing
- Bucket C: forecast/caveat lead-in smoothing
- Bucket B: longer analytical anchoring / source-span fidelity weakness after material grouping improvement, now reduced further after the focused B1 live anchoring retest
- Cross-bucket credibility: typed structure is healthier than before because inline continuity now survives missing-chunk fallback, but structured fields still deserve a stronger reliability/credibility contract

## Cross-bucket ranking
### Healthiest current path
1. **Bucket A** — healthiest operationally, with the main risk being thinner-than-ideal factual grouping rather than provenance collapse.

### Next healthiest
2. **Bucket C** — usable and stable, with mild caveat/forecast smoothing still present but not catastrophic.

### Weakest but improved
3. **Bucket B** — still the weakest tested bucket, but no longer ambiguous after the prompt grouping fix and post-fix reruns.

## What is confirmed
- A, B, and C all completed controlled end-to-end test-use passes.
- No tested bucket currently shows dominant assistant/helpdesk prose drift in final extracted claims.
- Weak-source / low-yield cautions behave appropriately as diagnostics for D-style inputs and were not incorrectly triggered on A/B/C.
- Bucket A is good enough for controlled factual-brief use, but still tends to over-split compact factual/context paragraphs.
- Bucket C is good enough for mixed-certainty / caveat-heavy use, but still smooths some sentence-head framing and source lead-ins.
- Bucket B was the main risk area, and its core grouping/attribution problem is now materially reduced:
  - exact B3 debug proved the original issue lived in upstream extraction output,
  - prompt contract tightening improved live B3 materially,
  - post-fix B2-style rerun showed positive generalization evidence beyond B3,
  - post-fix B1 confirmation rerun showed that the harshest analytical variant is no longer dominated by thin analytical flattening, with the main remaining gap shifting to shorter-claim anchoring fidelity.
- Credibility inline continuity is now materially healthier on the live path:
  - `src/sourcetrace/web/api.py` now auto-prepares stored inline content when credibility runs without prepared chunks,
  - live reruns stayed coherent across strong/weak source examples (`high/medium` for strong-source dev reruns, `low/low` for weak-source rumor-style blog).

## What changed during this cycle
The most important reclassification from the earlier campaign framing is this:
- the main problem is **not** broad attribution collapse across the product,
- the main problem is now **bucket-specific extraction quality weaknesses**.

In practice:
- A does not need broad alarm; it needs tighter factual grouping.
- C does not justify a collapse framing; it needs lead-in / caveat preservation.
- B remains the priority bucket, but now looks fixable through bounded prompt/runtime quality work rather than structural redesign.

## Remaining main gaps
### 1. Structured credibility output is still underpowered across otherwise usable runs
Across A and C, and also within B notes, useful signal often lives in free-text `notes` while typed fields such as:
- `assessment.source_reliability`
- `assessment.information_credibility`
remain product-important but still not fully decision-settled.

The inline continuity slice reduced one real product failure mode: credibility can now recover stored inline content even when prepared chunks are missing. Fresh live reruns also failed to reproduce the older broad typed-field-loss theory; typed fields now survive on representative live paths, including metadata-rich vs metadata-light contrasts.

So the remaining gap is narrower than the earlier framing:
- less about typed fields disappearing entirely,
- more about whether the current metadata-sensitive scoring contract is the right operator-facing behavior.

This remains one of the clearest cross-bucket product gaps.

### 2. Extraction quality is still uneven by source shape
- A: compact factual multi-clause paragraphs can still split too thinly
- C: caveat/forecast lead-ins can still be partially clipped
- B: the harshest B1-style analytical variant is no longer mainly a grouping failure, and the focused live voter-example retest also recovered later-chunk anchoring cleanly; any remaining risk now looks narrower and more edge-case-like than an active bucket-level blocker

## Campaign-level decision
Treat the current product state as:
- **usable-with-caveats for controlled test-use across A/B/C**
- **not yet analyst-ready without qualification**
- **no longer blocked by the earlier broad-failure framing**

## Recommended next slice
The most proportional next slice is now **not another broad discovery campaign**.

Best next product move:
1. treat the current metadata-sensitive credibility contract as the working default unless a fresh operator-facing case disproves it,
2. do not reopen Bucket B anchoring without a new failing long-form case,
3. otherwise move to the next bounded quality target outside this already clarified A/B/C campaign question.

## Decision-ready summary
### Potwierdzone
- A/B/C all classify as `usable-with-caveats`
- B remains weakest, but improved materially after the prompt grouping fix and post-fix B1/B2/B3 reruns
- the broad earlier attribution-collapse framing is no longer the right top-line story
- credibility inline continuity on the live path is materially healthier after stored-inline auto-prepare fallback
- fresh live credibility reruns did not reproduce broad typed-field disappearance
- cross-bucket credibility now looks more like a metadata-sensitive scoring/design question than a generic parser-loss bug

### Do weryfikacji
- whether a concrete operator-facing metadata-light case emerges that justifies reopening scoring-policy tuning
- whether a fresh failing long-form Bucket B case appears that reopens anchoring work beyond the now-healthy focused B1 live retest

## Recommended operational next step
If the goal is campaign closure: treat this campaign as decision-ready and move on.

Only reopen Bucket B anchoring if a new failing long-form case appears; otherwise the remaining higher-value open thread is metadata-sensitive credibility policy.
