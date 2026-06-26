# tmp utilities

Small ad hoc runtime helpers used during live SourceTrace validation.

## Keep
- `live_query_case.py` — generic helper to run one local research query against the local launcher and print JSON with `job_id`, `result`, and a few runtime file mtimes.
- `live_rerun_check.py` — existing ad hoc rerun helper.

## Candidate for removal later
- `live_single_case.py` — narrow one-off wrapper for the GetBack/NIK known-case check. Its behavior is now covered by `live_query_case.py` with explicit arguments, so keep only if we still want a hardcoded smoke case.

## Notes
- These are operator scripts, not product/runtime code.
- If we keep them longer, the next cleanup step should be either:
  1. remove `live_single_case.py`, or
  2. fold all three scripts into a tiny documented `tmp/tools/` layout.
