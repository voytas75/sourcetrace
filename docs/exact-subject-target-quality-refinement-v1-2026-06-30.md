# SourceTrace v2 exact-subject-target-quality-refinement-v1 — 2026-06-30

## Verdict

This is the right next bounded slice.

The fresh Poland live pass shows that the main remaining quality gap is no longer:
- missing official/institutional evidence upstream,
- nor primarily provider volatility,
- nor selected-evidence policy semantics.

The sharper gap is:
- **exact-subject target quality inside already-official institutional pools**.

In plain terms:
- the system now often finds the right official family,
- but still lets broader adjacent institutional pages outrank a more exact-subject official candidate.

## Why this slice, specifically

Fresh 2026-06-30 live diagnostics showed:
- canonical query -> `gov.pl` + `Biznes.gov.pl` survive cleanly, but selected shape is still broad/adjacent
- regulator-targeted query -> same pattern; no longer a CEJSH/publication-led failure mode
- Polish labour-law query -> correct `PIP` PDF is present, but loses rank-1 to a broader adjacent `PARP` page
- employer-duty / FAQ query -> healthiest run, but still broad ministry pages rather than a narrow employer-obligations winner

So the next useful move is not broader retrieval retuning.
It is a bounded improvement to how target quality is recognized **after official survival is already achieved**.

## Goal

Improve ranking/shaping preference for the most exact-subject official candidate when multiple official/institutional candidates are already present.

## Non-goals

Do not in this slice:
- change `selected_evidence` contract or reopen policy experimentation
- change trust semantics or compiled-artifact meaning
- broadly retune Poland retrieval windows across unrelated families
- solve PDF quality extraction as a separate program here
- re-run a full production-readiness review

## Problem statement

Current behavior is too willing to treat these as roughly equivalent:
- a broad but authoritative official/institutional page
- a narrower official/institutional page that matches the user’s exact subject more directly

That creates two observed failure shapes:

1. **selected_but_too_broad**
- the selected winner is official and not wrong,
- but still too general to feel like the best exact-subject answer.

2. **present_but_under_ranked_in_shaping**
- the right exact-subject official page is already in the pool,
- but a broader adjacent institutional page outranks it.

## Target family for this slice

Primary calibration family:
- Poland remote work / employer obligations / official guidance

Anchor bad case:
- `praca zdalna obowiązki pracodawcy zgłoszenie oficjalne gov.pl pip`
  - observed pattern: `PIP` PDF present, but broader adjacent `PARP` page wins rank-1

Anchor “healthy but still broad” cases:
- `remote work reporting obligations Poland employer official guidance`
- `Poland remote work employer reporting obligations official guidance site:gov.pl OR site:pip.gov.pl OR site:zus.pl`
- `Poland employer remote work obligations labour ministry official faq`

## Working hypothesis

Once official survival is satisfied, current target-quality behavior still underweights:
- title exactness,
- focused path specificity,
- subject closeness within the same institutional class,
- and penalties for adjacent-but-broader institutional pages.

In other words:
- institutional authority is now good enough,
- but exact-subject discrimination inside institutional candidates is still too weak.

## Bounded design direction

Prefer a small refinement in retrieval/target-quality scoring or shaping that strengthens exact-subject preference **within institutional candidates**.

The intended move is conservative:
- preserve current selection basis and trust posture
- improve upstream candidate ordering / shaping pressure
- make the better official candidate easier to survive and easier to rank above adjacent broad pages

## Candidate signals to strengthen

Only consider a narrow subset of signals:

1. **Focused title overlap**
- stronger reward when title directly names the query subject
- especially for terms equivalent to remote work / employer obligations / labour-law duty framing

2. **Focused path specificity**
- stronger reward for URLs/paths that look like direct subject pages rather than broad institutional article pages
- example intuition:
  - direct `remote-work` / `praca-zdalna` style page
  - should beat a broader adjacent thematic page when both are institutional

3. **Adjacent-broad institutional penalty**
- modest penalty when a candidate is institutional but topically adjacent/general rather than exact-subject
- this should be applied only when a more exact-subject institutional candidate is also present

4. **Intra-institution exact-subject preference**
- when comparing two official/institutional candidates of similar authority class,
- prefer the one with clearer subject specificity instead of treating authority as the dominant differentiator

## Signals to avoid in this slice

Do not rely on:
- downstream synthesis semantics
- broad LLM policy judgments as the primary fix
- new selector contract dimensions
- PDF favoritism as a general rule
- hardcoded Poland-only one-off exceptions if a generic institutional exact-subject rule can cover the case

## Likely implementation surface

Most likely surfaces to inspect first:
- retrieval target-quality shaping
- candidate ranking heuristics before selected-evidence handoff
- any current scoring helpers already used by:
  - `test_retrieval_target_quality.py`
  - `test_institutional_evidence_precision.py`
  - `test_quality_regression_pack_v4.py`

Default preference:
- patch the smallest upstream scoring/shaping seam that can flip the bad case
- do not spread logic across retrieval, judge, and selector unless evidence forces it

## Evidence standard

A good outcome for this slice is not “more official overall.”
That part is already mostly working.

A good outcome is:
- the more exact-subject institutional candidate wins within an already-official pool,
- especially in the Polish labour-law case,
- without regressing the healthier FAQ/canonical cases.

## Suggested acceptance checks

Minimum focused checks:

1. Poland labour-law bad case
- `praca zdalna obowiązki pracodawcy zgłoszenie oficjalne gov.pl pip`
- desired shift:
  - `PIP` remote-work source should outrank broader adjacent institutional material

2. Canonical official-guidance case
- `remote work reporting obligations Poland employer official guidance`
- desired shift:
  - retain official/institutional pool quality
  - avoid regressing into advisory/commercial drift

3. Employer-duty / FAQ case
- `Poland employer remote work obligations labour ministry official faq`
- desired shift:
  - preserve official shape
  - improve subject precision if possible
  - at minimum, do not regress

4. Existing focused unit/regression coverage
- update or add the smallest tests needed to pin:
  - exact-subject institutional candidate beating adjacent broad institutional candidate
  - no selector-contract expansion
  - no regression back to publication/advisory-led winners in the calibrated family

## Definition of done

This slice is done when:
- the Polish labour-law bad case no longer prefers the broader adjacent institutional result over the more exact-subject official candidate
- healthier Poland official cases remain official and do not regress toward advisory/commercial material
- the change remains bounded to retrieval/target-quality behavior
- `selected_evidence` SSOT stays unchanged
- focused tests clearly pin the intended discrimination behavior

## Rollback condition

Rollback or narrow further if:
- official survival gets worse in the healthier Poland cases
- selector/compiled-artifact semantics need to change to make the slice work
- the fix starts depending on broad PDF bias or hardcoded case-specific exceptions

## Practical recommendation

Proceed with this slice next.

But keep it narrow.
The goal is not to make the system more aggressive.
The goal is to make it less sloppy once it is already inside the right official neighborhood.
