# SourceTrace v2 restart note — 2026-06-28 — trust-selected-evidence-alignment

## Current repo state
- Repo: `/home/openclaw/projects/sourcetrace`
- Branch: `main`
- Current HEAD: `24b48ea` — `Refine official guidance source typing`
- Worktree: clean at save time

## What was completed just before this checkpoint
Already committed and pushed on `main`:
- `trust-jurisdiction-alignment-v1`
- `retrieval-query-refinement-handoff-v2`
- `retrieval-query-refinement-live-eval-v1`
- `quality-regression-pack-v4`
- `official-guidance-source-typing-v1`

Current posture after those slices:
- official-guidance retrieval is cleaner than before
- remaining weak cases are narrower than generic retrieval drift
- full v2 unit suite was green on current HEAD: `./.venv/bin/pytest -q tests/unit/v2` → `100 passed`

## Current best next bounded slice
- `trust-selected-evidence-alignment-v1`

## Why this is next
The sharpest remaining bounded correctness gap is now in the trust projection, not another retrieval tweak.

`project_operator_trust(...)` currently mixes two different evidence views:
- it counts selected evidence from `view.compiled_artifact.selected_evidence`
- but it evaluates source-type / jurisdiction shape against `artifact.evidence_candidates[:2]`

That can diverge from the actual selected pair because selected evidence is built through `decide_selected_evidence(...)`, which may choose:
- ranks `2 + 3` after minimal-content filtering
- ranks `1 + 3` after domain-diversity preference

So the operator trust contract can currently judge a different pair than the one actually selected and shown.

## Exact scope for the next slice
Implement `trust-selected-evidence-alignment-v1`:
- make `project_operator_trust(...)` evaluate the same selected pair used by compiled/readback selected evidence
- keep current trust statuses/reason names unless alignment alone changes them
- add focused tests for the two known divergence modes:
  - minimal-content case selecting `rank 2 + rank 3`
  - domain-diversity case selecting `rank 1 + rank 3`

## Non-scope
- no retrieval/query-refinement changes
- no new deterministic heuristics
- no selector policy redesign
- no source taxonomy expansion
- no live-pack expansion in the same slice

## Evidence for this checkpoint
Relevant files:
- `src/sourcetrace_v2/projections/api/trust.py`
- `src/sourcetrace_v2/app/services/compiled_artifacts.py`
- `src/sourcetrace_v2/projections/api/evidence.py`
- `tests/unit/v2/test_selected_evidence_policy.py`
- `tests/unit/v2/test_trust_quality_alignment.py`
- `docs/official-guidance-source-typing-v1-2026-06-28.md`
- `docs/quality-regression-pack-v4-2026-06-28.md`
- `docs/STATUS.md`

Key repo facts behind the rerank:
- selected evidence is built from `decide_selected_evidence(...)`
- trust still inspects raw `artifact.evidence_candidates[:2]`
- this mismatch is real because existing tests already prove selection can diverge from raw top-2

## Suggested resume message
```text
Pracujemy w repo: /home/openclaw/projects/sourcetrace

Kontynuujemy SourceTrace v2 od HEAD:
- 24b48ea — Refine official guidance source typing

Aktualny najlepszy następny bounded slice:
- trust-selected-evidence-alignment-v1

Zrób mały implementation pass:
1. wyrównaj `project_operator_trust(...)` do faktycznie wybranego `selected_evidence`
2. dodaj 2 testy na divergence cases (minimal-content => 2+3, domain-diversity => 1+3)
3. uruchom focused tests + `./.venv/bin/pytest -q tests/unit/v2`
4. zaktualizuj `docs/STATUS.md`
5. commit/push tylko jeśli green
```
