# SourceTrace v2 Poland official target-quality checkpoint — 2026-06-30

## Verdict

The bounded Poland follow-up is a real pass.

Two small fixes were applied and both produced live-visible improvement:
1. `exact-subject-target-quality-refinement-v1`
2. `official-pair-hygiene-v1`

This does **not** mean the whole Poland remote-work / employer-obligations family is fully solved.
But it does restore a more honest and materially better bounded posture:
- official/institutional candidates now win more often in the right places,
- the Polish exact-subject case no longer drifts toward broad adjacent institutional material in the same way,
- and the selected pair no longer gets needlessly polluted by a weaker diverse fallback when a stronger second official candidate is present.

## What changed

### 1) Retrieval / target-quality refinement
Implemented in:
- `src/sourcetrace_v2/execution/stages/retrieval.py`

Bounded changes:
- strengthened exact-subject preference inside institutional candidate pools
- added light penalty for adjacent-broad institutional pages
- added Polish official-intent markers so Polish labour-law / official-source phrasings actually activate the institutional-preference shaping path

What this was meant to fix:
- the sharper Poland gap was no longer total absence of official sources
- it was exact-subject discrimination inside already-official pools
- especially for Polish phrasing where the right official candidate could be present but under-ranked or displaced by a broader adjacent page

### 2) Selected-evidence official-pair hygiene
Implemented in:
- `src/sourcetrace_v2/core/policies/selected_evidence.py`

Bounded changes:
- domain diversity still applies by default
- but it no longer automatically displaces a stronger same-domain/same-host-family official candidate
- the exception is narrow: keep the same-domain candidate only when it is **strictly stronger** on judgment quality (`authority.score` / `answer_fit.score`) than the diverse alternative
- if quality is tied, diversity still wins

What this was meant to fix:
- after the target-quality improvement, a live FAQ-like case still showed a weaker external/non-institutional result entering the selected pair only because of diversity pressure
- that was a hygiene issue, not a reason to reopen the broader selected-evidence contract

## Verification done

### Focused repo-side gates
Passed:
- `./.venv/bin/pytest -q tests/unit/v2/test_retrieval_target_quality.py tests/unit/v2/test_institutional_evidence_precision.py tests/unit/v2/test_quality_regression_pack_v4.py`
  - result: `6 passed`
- `./.venv/bin/pytest -q tests/unit/v2/test_selected_evidence_policy.py tests/unit/v2/test_retrieval_target_quality.py tests/unit/v2/test_institutional_evidence_precision.py tests/unit/v2/test_quality_regression_pack_v4.py tests/unit/v2/test_minimal_flow.py`
  - result: `10 passed`

### Live verification highlights

#### Poland labour-law phrasing
Query:
- `praca zdalna obowiązki pracodawcy zgłoszenie oficjalne gov.pl pip`

Observed post-fix shape:
- top source moved to official `gov.pl` remote-work material
- candidate pool became:
  1. `Praca zdalna - Ministerstwo Rodziny, Pracy i Polityki Społecznej - Portal Gov.pl`
  2. `Praca zdalna - pytania i odpowiedzi - Ministerstwo Rodziny, Pracy i Polityki Społecznej - Portal Gov.pl`
  3. `Jak wdrożyć pracę zdalną w firmie | Biznes.gov.pl`

Interpretation:
- this is the main proof that exact-subject official ranking improved materially
- the earlier broad-adjacent institutional drift was reduced enough to change the live pool shape, not just a synthetic test

#### Employer-duty / FAQ follow-up
Query:
- `Poland employer remote work obligations labour ministry official faq`

Observed post-hygiene shape:
- selected pair became fully official/institutional
- weaker external/non-institutional FAQ fallback no longer displaced the stronger second official candidate

Interpretation:
- this confirms the selected-evidence hygiene fix did what it was supposed to do
- the improvement survived live execution, not just focused policy tests

## Current bounded posture

More honest current verdict:
- the recent Poland family work produced a real quality gain
- the active posture is stronger than before, but still bounded/operator-supervised
- the system is now less sloppy inside official Poland remote-work candidate pools
- however, it is still not appropriate to claim broad trust-sensitive completeness from this slice alone

## What remains open

The main open issue is now smaller and sharper:
- the Poland remote-work / employer-obligations family is improved,
- but the exact best official winner is still not guaranteed for every phrasing,
- and the returned evidence can still be somewhat broad even when it remains official and stable.

So the remaining risk is no longer:
- major publication-like drift,
- or obvious non-official contamination in the selected pair,

but rather:
- **residual breadth inside otherwise healthy official result sets**.

## Practical next move

Recommended next step:
- do **not** reopen broad policy work immediately
- keep this checkpoint as the current restart point for the Poland family
- when resuming, prefer either:
  1. a broader repo-side confirmation gate (`tests/unit/v2`), or
  2. a new bounded precision slice only if fresh live evidence shows a remaining exact-subject miss worth chasing

## Short restart summary

If resuming this Poland thread later:
- start from this checkpoint plus:
  - `docs/poland-institutional-retrieval-diagnostics-v1-2026-06-30.md`
  - `docs/exact-subject-target-quality-refinement-v1-2026-06-30.md`
- current trustworthy summary is:
  - exact-subject official top-1 improved,
  - official pair hygiene improved,
  - live reruns confirmed real progress,
  - remaining issue is now residual breadth, not obvious official-source survival failure.
