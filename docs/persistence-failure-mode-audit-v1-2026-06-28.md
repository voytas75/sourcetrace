# SourceTrace v2 persistence failure-mode audit v1 — 2026-06-28

## Goal

Inspect the current JSONL/readback persistence posture for partial, stale, and marker/artifact mismatch states before deciding whether a bounded reliability fix is needed.

## Scope checked

Reviewed and verified:
- `src/sourcetrace_v2/adapters/storage/jsonl.py`
- `src/sourcetrace_v2/app/services/readback.py`
- operator readback path in `src/sourcetrace_v2/operator/readback.py`
- persistence/readback tests around JSONL, HTTP projection, and operator readback

## What the system already handles honestly

### 1. Artifact-only persistence is surfaced as partial / incomplete
Current behavior:
- if result artifact exists but marker does not,
- readback returns `INCOMPLETE`
- persistence completeness is `partial`
- HTTP path returns `202`

Verdict:
- good
- this is already operationally honest

### 2. Marker-only persistence is surfaced as partial / incomplete
Current behavior:
- if marker exists but artifact does not,
- readback returns `INCOMPLETE`
- persistence completeness is `partial`
- HTTP path returns `202`

Verdict:
- good
- again, operationally honest

### 3. Fully absent state is not confused with partial or found
Current behavior:
- no artifact + no marker + no receipts => `NOT_FOUND`
- persistence completeness `absent`
- HTTP path returns `404`

Verdict:
- good
- the surface distinguishes absence from incomplete persistence cleanly

### 4. Found state requires both artifact and marker
Current behavior:
- `FOUND` is not inferred from artifact presence alone
- marker state is explicit in the read model and projection

Verdict:
- strong improvement over earlier posture
- this was the right design correction

## What is still weaker than production-grade posture

### 1. JSONL append path is simple append-only, not crash-hardened
Observed behavior:
- `_append_jsonl(...)` writes directly with append mode
- there is no temp-file + rename pattern
- there is no fsync/flush discipline described here
- there is no bounded corruption-recovery path in the repository layer

Interpretation:
- this is acceptable as a proof-grade persistence seam
- it is not yet a strong durability story under abrupt crash/interruption assumptions

### 2. Truncated/corrupted JSONL line handling is not graceful
Observed behavior:
- `_read_jsonl(...)` directly `json.loads(...)` every non-empty line
- one malformed line can raise and break the read path

Interpretation:
- honest in the sense that it fails loudly
- but not resilient
- still a real operational weakness if crash-corrupted append lines are plausible

### 3. Compiled artifact presence is not part of persistence completeness semantics
Observed behavior:
- execution completeness is based on artifact + marker
- compiled artifact presence is projected, but not part of the completeness decision

Interpretation:
- this may be acceptable if compiled artifact is intentionally secondary
- but it is still a boundary worth making explicit in operator posture: a run can be `FOUND` while compiled readback is still absent or stale

### 4. Retention / cleanup / growth posture is still mostly implicit
Observed behavior:
- append-only JSONL files accumulate indefinitely within the chosen artifacts dir
- this audit did not find bounded retention/rotation/cleanup semantics in the current path

Interpretation:
- not an immediate correctness lie
- but still a production-operations gap

## Verification

Focused persistence/readback tests passed:
- `tests/unit/v2/test_readback.py`
- `tests/unit/v2/test_api_readback_projection.py`
- `tests/unit/v2/test_jsonl_storage.py`
- `tests/unit/v2/test_operator_readback.py`

Result: `14 passed`

Also corrected one stale expectation in `tests/unit/v2/test_readback.py`:
- stage receipts count is now `10`, not `8`, because the explicit retrieval stage is part of the current v2 flow

## Practical verdict

Current posture:
- **honest enough for bounded operator use and further production-readiness work**
- **not yet a strong durability story**

That means:
- do not rewrite storage yet
- but do treat JSONL as a still-limited persistence substrate
- the next storage-facing step should target one real weakness, not broad platform churn

## Recommended next bounded slice

`jsonl-corruption-tolerance-v1`

Goal:
- add a narrow, explicit posture for malformed/truncated trailing JSONL lines so readback can fail more gracefully or skip clearly broken tail entries without pretending corruption did not happen
