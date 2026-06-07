# Closeout — credibility metadata-sensitive policy thread

Status: bounded policy closeout
Date: 2026-05-24
Parent SSOT: `docs/plans/2026-05-21-real-data-test-use-ssot.md`
Related checkpoints:
- `docs/plans/2026-05-24-credibility-typed-fields-checkpoint.md`
- `docs/plans/2026-05-24-credibility-metadata-sensitive-contract-checkpoint.md`
- `docs/plans/2026-05-24-cross-bucket-closeout.md`
Related stable docs:
- `docs/plans/2026-05-24-credibility-inline-continuity-ssot.md`
- `docs/plans/2026-05-26-source-trace-research-to-backlog-plan.md`

## Decision
Treat the current metadata-sensitive credibility behavior as the **working product default** for controlled test-use.

Operationally this means:
- typed credibility fields are considered healthy unless a fresh current-runtime case proves otherwise,
- metadata-light note-style inputs may legitimately score lower on `source_reliability`,
- this is not an active parser-loss or web-nulling bug on current evidence,
- no scoring change should be opened by default without a concrete operator-facing counterexample.

## Confirmed basis
The closeout rests on four already-verified facts:
1. credibility inline continuity is materially fixed on the live path,
2. fresh reruns did not reproduce broad typed-field disappearance,
3. metadata-rich vs metadata-light contrast changed `source_reliability` but kept typed fields alive,
4. weak-source and strong-source contrast still behaved coherently (`low/low` vs `high/medium`).

## Product contract to use now
### Interpret as intended behavior when
- `source_reliability` drops on metadata-light note-style input,
- `information_credibility` stays non-low,
- typed fields and factor arrays are still present,
- the input lacks direct provenance metadata such as source URL / publisher / publication date.

### Do not treat as intended behavior when
- typed fields come back `null`,
- the parser/runtime loses a clearly present typed assessment,
- or a clearly well-attributed metadata-light source shape still lands at an obviously too-harsh rating.

## Reclassify
### Potwierdzone
- the broad typed-field disappearance theory is parked
- the active credibility question has been narrowed from plumbing to product policy
- the current conservative source-reliability posture is coherent enough to keep as the default until contradicted by new evidence

### Do weryfikacji
- whether a concrete operator-facing metadata-light case emerges that justifies bounded scoring-policy tuning
- whether future product usage shows that the current `low` posture is too harsh for intended analyst workflows

## Closure rule
Do not reopen this thread for general discovery.

Reopen only if one of these happens:
1. a fresh live case reproduces `null` typed fields,
2. a clearly attributable metadata-light case still scores in a way that is obviously too harsh,
3. product requirements change and explicitly require a less conservative reliability posture.

## Next proportional move
Treat this credibility policy thread as closed for now.

If another bounded slice is needed later, it should be:
- a concrete scoring-policy adjustment based on a failing operator-facing example,
- not another generic parser-loss investigation.
