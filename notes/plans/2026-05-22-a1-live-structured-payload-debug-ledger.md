# A1 live structured-payload debug ledger — 2026-05-22

## Scope
Bounded ledger for the current blocker on A1 live extraction after the grounding heuristic slice.

## Trigger
`POST /api/documents/{document_id}/extract-claims` intermittently returns `500 internal_server_error` on the Reuters A1-shaped document during live WWW runs.

## Confirmed facts
- Repo: `/home/voytas/projects/sourcetrace`
- Branch during diagnosis: `main`
- Runtime route failing: `POST /api/documents/{document_id}/extract-claims`
- Failing document family: Reuters A1 South Africa / wider Africa risks shaped input
- Stable traceback seam:
  - `src/sourcetrace/web/api.py`
  - `src/sourcetrace/web/delivery.py`
  - `src/sourcetrace/application/extraction_runtime.py`
  - `src/sourcetrace/llm/extraction.py`
  - `src/sourcetrace/llm/structured_generation.py`
- Stable exception:
  - `sourcetrace.llm.errors.LlmSchemaError: structured payload for ClaimExtractionPayload must be a mapping`

## Confirmed diagnosis
The `500` is not caused by the new claim→chunk grounding heuristic.
The failing seam is earlier: provider/LiteLLM structured-output materialization before extraction-runtime post-processing.

## Root-cause hypothesis
The live provider response sometimes arrives in a shape that the current adapter did not fully normalize:
- not only `message.parsed` mapping,
- not only `message.content` as JSON string,
- but also `message.content` as a list of content parts containing JSON text.

This causes `_extract_structured_payload(...)` to return a non-mapping payload, which then trips:
- `src/sourcetrace/llm/structured_generation.py`
- guard: `structured payload for ClaimExtractionPayload must be a mapping`

## Bounded fix added in this slice
File changed:
- `src/sourcetrace/llm/litellm_client.py`

Behavior added:
- parse structured payload from `message.content` when content is a list,
- collect `text` / `output_text` parts,
- join text fragments,
- attempt `json.loads(...)`,
- then pass the parsed object through existing claim-payload normalization.

## Regression added
File changed:
- `tests/unit/llm/test_litellm_client.py`

New regression covers:
- `message.content = [{"type": "output_text", "text": "<json>"}]`
- expected result: normalized mapping payload, not plain content passthrough.

## Verification completed
- Focused tests:
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q tests/unit/llm/test_litellm_client.py tests/unit/application/test_application_extraction_runtime.py`
  - result: `38 passed`
- Full baseline:
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q`
  - result: `277 passed`

## Still unresolved / do weryfikacji
- Live WWW on standard `sourcetrace-www-start` at `:8000` was initially still reproducing `500` after the first adapter patch.
- Additional live capture then proved a second concrete payload variant: the provider returned a JSON string wrapped in markdown code fences.
- A second bounded adapter fix was added to strip fenced JSON blocks before `json.loads(...)`.
- After that second fix, the same standard WWW path on `:8000` succeeded for the A1 live rerun.

## Second bounded fix added after live capture
Files changed:
- `src/sourcetrace/llm/litellm_client.py`
- `src/sourcetrace/web/api.py`

Behavior added:
- debug markers now emit with `flush=True` so live WWW logs capture the failing shape reliably,
- structured-content parsing now also handles JSON wrapped in markdown fences like:
  - `````json ... `````.

## Additional regression added
File changed:
- `tests/unit/llm/test_litellm_client.py`

New regression covers:
- `message.content = "```json\n{...}\n```"`
- expected result: parsed mapping payload, not raw string passthrough.

## Final live verification
Standard WWW runtime:
- entrypoint: `.venv/bin/sourcetrace-www-start`
- endpoint: `http://127.0.0.1:8000`

A1 live rerun result after second fix:
- `prepare_chunk_count`: `4`
- `extract_claim_count`: `22`
- `case_claim_count`: `22`
- `unknown_count`: `0`
- observed chunk distribution:
  - `chunk-2`: `5`
  - `chunk-3`: `3`
  - `chunk-4`: `14`
- sample spans confirmed live:
  - `claim-1` → `chunk-2 / p2`
  - `claim-6` → `chunk-3 / p3`
  - `claim-7` → `chunk-4 / p4`

## Important interpretation
Current state should now be classified as:
- **potwierdzone**: two real structured-payload seam bugs were found and patched,
- **potwierdzone**: standard WWW live extraction for the A1-shaped document now succeeds,
- **potwierdzone**: the A1 rerun no longer collapses to `chunk-span:unknown` on this live path,
- **potwierdzone**: bounded longer-form B1/B2 live smoke inputs also pass on the same standard WWW runtime without `500` and without `chunk-span:unknown`,
- **do weryfikacji**: whether broader article families show any further provider-output variants beyond list-parts and fenced-JSON forms.

## Next bounded step if live still fails
1. Force durable debug emission for live WWW path (`flush=True` / stderr-safe markers if needed).
2. Capture one real failing payload artifact from the standard `www-start` process.
3. Patch only the exact additional payload shape observed.
4. Re-run A1 live extraction and then reassess unknown-span distribution.
