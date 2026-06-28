# SourceTrace v2 authority-relevance source typing v4-or-stop check — 2026-06-28

## Goal

Decide whether another small source-typing refinement is still justified after `source-typing-v3`, or whether tuning should pause until a concrete live failure appears.

This slice is a stop-check, not an automatic v4 implementation.

## Method

Re-ran the representative live weak-case family and inspected the current `source_type` distribution in execution/readback candidates.

Queries checked:
- remote work reporting
- legal hold steps
- identity / break-glass
- breach notification

## Result

The residual `unknown` bucket is now small enough that another immediate refinement does **not** look justified by default.

Observed counts:
- remote work reporting: `unknown_count = 1`
- legal hold steps: `unknown_count = 0`
- identity / break-glass: `unknown_count = 0`
- breach notification: `unknown_count = 0`

The only remaining unknown in this stop-check set was:
- `Implementing Remote Work for Employees Based in Poland`
- `https://easyeor.pl/pl-hr-guide-remote-work/`

## Interpretation

This is no longer a broad recurring unknown bucket.
It now looks like a narrow residue of advisory/commercial guidance sites that are plausible but not urgent enough to justify another classifier refinement on their own.

That is the key decision point:
- before v3, unknown still represented a meaningful recurring cluster
- after v3, unknown is small and narrow enough that more tuning would start looking like overfitting

## Practical verdict

**Stop here for now.**

Do not add `source-typing-v4` by default.
Wait for one of these before resuming classifier work:
- a concrete live failure where `unknown` meaningfully harms source-mix shaping or evidence quality
- a repeated new source family that clearly escapes the current markers
- a stronger need from downstream consumers for finer source typing

## Recommendation

Pause source-typing refinement and return focus to broader retrieval/evidence quality only when new evidence justifies it.
