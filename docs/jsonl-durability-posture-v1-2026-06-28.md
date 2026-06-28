# SourceTrace v2 JSONL durability posture v1 — 2026-06-28

## Goal

Decide explicitly whether the current JSONL persistence substrate is acceptable for the present deployment posture under stated limits, or whether one more bounded durability fix is required before calling the storage line good enough.

## Current substrate

The current v2 JSONL posture now includes:
- explicit artifact + marker semantics for `FOUND`
- honest partial-state readback (`absent / partial / complete`)
- repo-owned operator readback path
- bounded tolerance for malformed/truncated trailing JSONL tail lines
- loud failure on broader/non-trailing corruption

## Durability verdict

### Acceptable now — but only under explicit limits

The current JSONL substrate is **good enough for the present bounded operator/development deployment posture** if all of the following remain true:

- single-host local storage
- no strong concurrency expectations across many writers
- operator understands this is a bounded persistence seam, not a hardened database
- append-only growth is still modest and manageable within the current artifacts directory usage
- recovery expectations remain limited to:
  - honest partial-state surfacing
  - tolerance for a broken trailing append line
  - loud failure on broader corruption

Under those limits, I would call the storage line:
- **operationally honest**
- **boundedly durable enough**
- **not production-grade in the database sense**

### Not claimed by this posture

This posture still does **not** claim:
- crash-safe atomic multi-file commit semantics
- strong concurrent-writer correctness
- broad corruption recovery
- retention/rotation lifecycle discipline
- hard guarantees for large-scale or long-lived artifact accumulation

## Decision

**Do not add another immediate storage fix right now.**

Reason:
- the last two storage-facing slices already improved the sharpest real weaknesses
- current remaining weaknesses are real, but they are mostly posture/boundary limits rather than the next obvious bounded bug
- another storage patch right now would likely create more motion than value

## What to do instead

Treat JSONL as the current bounded persistence substrate for v2 and move attention back to the broader production-readiness line.

If storage work returns later, it should be triggered by one of:
- concrete concurrency pain
- artifact growth/retention pain
- real corruption events beyond trailing append damage
- need for stronger deployment guarantees than the current local/operator posture

## Verification

Focused persistence/readback tests passed:
- `tests/unit/v2/test_jsonl_storage.py`
- `tests/unit/v2/test_readback.py`
- `tests/unit/v2/test_operator_readback.py`
- `tests/unit/v2/test_api_readback_projection.py`

Result: `16 passed`

## Practical verdict

This is the point to stop chewing on storage.
The JSONL line is now honest enough and boundedly durable enough for the current stage.
The next meaningful production gap is elsewhere.

## Recommended next bounded slice

`deployment-readiness-gap-review-v1`

Goal:
- re-rank the remaining non-storage production gaps after the recent retrieval, regression, trust-contract, and storage-posture work,
- and choose the next highest-value slice from the remaining live gaps rather than continuing storage polish
