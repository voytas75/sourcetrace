# Deep Research benchmark harness polish — 2026-06-21

Status: completed bounded slice
Date: 2026-06-21
Scope: make benchmark reporting evaluator-aware now that Deep Research result artifacts expose structured evaluation output.

## 1. Goal

Improve the benchmark harness so it can consume the new post-result evaluator payload and produce a more useful benchmark summary without hand-scoring every dimension manually.

---

## 2. What was added

Added a small reporting utility:
- `scripts/deep_research_benchmark_report.py`

Current behavior:
- reads a benchmark result JSON file,
- scores each query on:
  - API correctness,
  - source quality,
  - relevance,
  - truthfulness,
  - report shape,
  - telemetry,
- uses evaluator verdicts when present,
- falls back gracefully when older payloads do not contain evaluation data,
- renders a markdown report with:
  - per-query score table,
  - query class,
  - providers,
  - findings count,
  - recommended next check,
  - evaluator notes when available.

---
\n## 3. Important observation

When run against the older benchmark payload saved before evaluator integration, the harness correctly falls back but shows:
- no evaluator notes,
- zero scores for evaluator-driven dimensions.

That is expected and correct.
It means the harness is backward-compatible rather than silently inventing evaluation signals.

When run against a payload that includes `result.evaluation`, the report becomes meaningfully richer and reflects the evaluator verdicts correctly.

---

## 4. Verification

### Manual harness verification
Verified two paths:
1. old benchmark payload without evaluator data,
2. synthetic benchmark payload with evaluator data.

Observed:
- old payloads render a valid report with graceful fallback,
- evaluator-bearing payloads render per-dimension scores and notes correctly.

### Repo gate\n- full repo gate remains green: `398 passed`

---

## 5. Verdict

This slice succeeded.

The benchmark workflow is now materially better because evaluator output can be turned into readable, structured benchmark reporting instead of staying trapped in raw result payloads.

This is enough for the next benchmark rerun to produce a more decision-ready artifact.

---

## 6. Recommended next step

Best next move:
- rerun the canonical 3-query benchmark pack through the current SourceTrace runtime,
- feed the fresh payload into `scripts/deep_research_benchmark_report.py`,
- save the generated markdown report as the new benchmark baseline.

That will give the first fully evaluator-aware benchmark artifact for Deep Research.
