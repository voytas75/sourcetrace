# SourceTrace Real-Data Campaign Runbook v1

Status: operational runbook for the first controlled 10-document campaign
Parent SSOT: `docs/plans/2026-05-21-real-data-test-use-ssot.md`
Corpus ledger: `docs/plans/2026-05-21-real-data-campaign-corpus-v1.md`
Observation template: `docs/plans/test-use-observation-template.md`

## Purpose
This runbook turns the real-data test-use SSOT into a repeatable operator sequence.

It is intentionally narrow:
- one frozen 10-document corpus,
- one observation note per document,
- evidence-first recording,
- no product-boundary changes during the pass.

## Runtime SSOT
Use the repo-owned launcher wrapper via repo `.venv`:

```bash
cd /home/voytas/projects/sourcetrace
PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher
PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control wait --host 127.0.0.1 --port 8000 --timeout-seconds 15
```

Optional checks:

```bash
curl http://127.0.0.1:8000/api/ready
curl http://127.0.0.1:8000/api/runtime
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ./.venv/bin/python -m sourcetrace.smoke_flow --pretty
```

Stop when the session slice is complete:

```bash
cd /home/voytas/projects/sourcetrace
PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control stop --mode local-launcher
```

## Campaign order
Run documents in this order:
1. `campaign-a1-reuters-south-africa-risks`
2. `campaign-a2-bbc-us-inflation-energy-shock`
3. `campaign-a3-bbc-us-jobs-april`
4. `campaign-c1-bbc-uk-growth-risks`
5. `campaign-c2-bbc-uk-inflation-expected-rise`
6. `campaign-b1-ap-trump-tax-cuts-inflation`
7. `campaign-b2-bbc-global-economy-tariffs-2026`
8. `campaign-b3-bbc-gulf-economies-iran-conflict`
9. `campaign-d1-ap-einpresswire-war-market-trends`
10. `campaign-d2-ap-photo-gallery-romania-hat-walk`

## Per-document execution contract
For each document:
1. Create or reuse the campaign case/document IDs from the corpus ledger.
2. Seed the document metadata and source text into the running process.
3. Run:
   - prepare
   - extract-claims
   - credibility
   - relevant read-back endpoints / HTML views if needed
   - for longer analytical documents, prefer stepwise API calls over one all-in-one script and allow larger client ti...[truncated]4. Save one observation note using the canonical template.
5. Classify the document exactly as one of:
   - `usable`
   - `usable-with-caveats`
   - `engineering-smoke-only`
   - `failed`
6. Capture at least one pasteable evidence block.

## Minimum evidence per note
A note is strong enough for follow-up only if it includes at least one of:
- raw source paragraph,
- prepared chunk snippet,
- final persisted `exact_text`,
- route diagnostics snapshot,
- credibility note excerpt,
- HTTP/API payload excerpt,
- HTML/UI snapshot text.

## Seam classification rule
Every notable issue must be tagged as one of:
- prepare/chunking issue,
- extraction quality issue,
- normalization quality issue,
- credibility quality issue,
- verification/review usefulness gap,
- API/HTML delivery contract issue,
- runtime/bootstrap/operator issue.

## Session slicing rule
Do not try to finish all 10 documents in one undifferentiated pass.

Recommended slice size:
- 1 to 3 documents per session,
- then checkpoint findings,
- then continue with the next bucket/order.

## First execution slice
Recommended first slice:
- `campaign-a1-reuters-south-africa-risks`
- `campaign-a2-bbc-us-inflation-energy-shock`
- `campaign-a3-bbc-us-jobs-april`

Reason:
- establish best-case factual baseline before pressure-testing caveats, analysis, and noisy inputs.

## Exit condition for the campaign
The first campaign is complete when:
- all 10 documents have notes,
- findings are grouped by seam,
- at least one repeated/high-confidence failure mode is identified,
- the next bounded engineering slice can be chosen from observed evidence.
