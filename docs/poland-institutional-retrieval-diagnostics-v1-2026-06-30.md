# SourceTrace v2 poland-institutional-retrieval-diagnostics-v1 — 2026-06-30

## Goal

Inspect why the Poland remote-work / employer-obligations family is still unstable even after:
- query-handoff repair,
- institutional retrieval window widening,
- source typing,
- and publication-like institutional penalties.

This is a diagnostic slice, not a policy-change slice.

## Scope

Target family:
- Poland remote-work / employer-obligations / official-guidance retrieval

Out of scope:
- selector-policy changes
- trust-policy changes
- broad institutional retrieval retuning outside the Poland family
- production-readiness re-review in the same slice

## Queries to inspect

1. Canonical
   - `remote work reporting obligations Poland employer official guidance`

2. Public-institutional / regulator-targeted phrasing
   - `Poland remote work employer reporting obligations official guidance site:gov.pl OR site:pip.gov.pl OR site:zus.pl`

3. Polish labour-law angle
   - `praca zdalna obowiązki pracodawcy zgłoszenie oficjalne gov.pl pip`

4. Employer-duty / exact-subject phrasing
   - `Poland employer remote work obligations labour ministry official faq`

## What to inspect for each query

For each query, capture only these checkpoints:

1. Raw provider output
   - top 10–12 results
   - whether `gov.pl`, `biznes.gov.pl`, `pip.gov.pl`, or `zus.pl` appears at all

2. Retrieval-stage pool after current v2 shaping/window logic
   - final bounded candidate pool
   - candidate order
   - source types

3. Selected evidence shape
   - final selected pair or selected top item

4. One-line diagnosis bucket
   - `missing_upstream`
   - `present_but_provider_volatile`
   - `present_but_under_ranked_in_shaping`
   - `selected_but_too_broad`

## Check matrix

| Query | Best Poland institutional hit upstream | Upstream rank | Survives into v2 pool? | Pool rank | Selected? | Diagnosis |
|---|---|---:|---|---:|---|---|
| canonical | `gov.pl` / Ministry of Family, Labour and Social Policy / Remote work | 1 in fresh live run | yes | 1 | yes | `selected_but_too_broad` |
| regulator-targeted | `gov.pl` / Ministry of Family, Labour and Social Policy / Remote work | 1 in fresh live run | yes | 1 | yes | `selected_but_too_broad` |
| polish-labour-law | `pip.gov.pl` PDF `Praca zdalna - Państwowa Inspekcja Pracy` | 2 in fresh live run | yes | 2 | yes, but behind PARP | `present_but_under_ranked_in_shaping` |
| employer-duty-faq | `gov.pl` / Ministry of Family, Labour and Social Policy / Remote work | 1 in fresh live run | yes | 1 | yes | `selected_but_too_broad` |

## Key questions

1. Is the best Poland institutional source absent upstream, or merely unstable in provider ordering?
2. If present upstream, does it enter the widened retrieval window but still lose during shaping?
3. If it survives shaping, does it still lose because the surviving official page is too broad rather than exact-subject?
4. Are current source-type labels truthful for Poland public/institutional domains in this family?

## Expected decision after diagnosis

Choose exactly one primary next move:

1. `query-phrasing-refinement-v1`
   - if the issue is mainly upstream phrasing / search-surface volatility

2. `poland-host-typing-fix-v1`
   - if Poland public/institutional sources are surfacing but are mislabeled or under-weighted because of typing gaps

3. `exact-subject-target-quality-refinement-v1`
   - if the right institutional sources are present but still lose to broader official/advisory pages inside current shaping

4. `volatility-note-no-policy-change`
   - if the case is too provider-volatile to justify a bounded code change yet

## Definition of done

This slice is complete when:
- all 4 queries have a filled diagnosis row,
- each row names the best upstream Poland institutional hit,
- each row is assigned one diagnosis bucket,
- and the note ends with one chosen next bounded slice.

## Current evidence from prior bounded checkpoints

Already established before this note:
- canonical Poland remote-work reporting is **not** a pure upstream miss:
  - earlier diagnostics found a real `gov.pl` public-institutional source in raw SearxNG beyond the shallow top slice
  - retrieval-window widening improved survival once, but later evaluation still showed instability
- the current sharper open question is therefore no longer “does Poland institutional evidence exist at all?”
- the sharper open question is:
  - whether it is mainly **provider-order volatility**,
  - **under-ranking during shaping**,
  - or **selection of a still-too-broad official page** instead of a clean exact-subject winner
- earlier guided eval also showed `biznes.gov.pl` can surface as a top retrieval candidate, but that still does not fully close the exact-subject requirement for the employer-obligations family

## Fresh live evidence collected in this session

All four queries were rerun through the live v2 operator path after sourcing the shell env from `~/.bashrc`.

### 1. Canonical query
Query:
- `remote work reporting obligations Poland employer official guidance`

Observed retrieval query:
- `Poland remote work employer reporting obligations official guidance site:gov.pl OR site:pip.gov.pl OR site:zus.pl`

Fresh candidate pool:
1. `Remote work - Ministry of Family, Labour and Social Policy - Gov.pl website` — `institutional`
2. `The rights and obligations of employers | Biznes.gov.pl` — `institutional`
3. `How to post a driver to Poland - State Labour Inspection` — `institutional`

Selected:
- `gov.pl` remote-work page
- `Biznes.gov.pl` employer-rights page

Interpretation:
- this is no longer best explained as provider volatility
- the stronger current diagnosis is that the system now retrieves official institutional sources reliably, but the selected pair is still **broad/adjacent rather than a clean exact-subject official winner**

### 2. Regulator-targeted query
Query:
- `Poland remote work employer reporting obligations official guidance site:gov.pl OR site:pip.gov.pl OR site:zus.pl`

Fresh candidate pool:
1. `Remote work - Ministry of Family, Labour and Social Policy - Gov.pl website` — `institutional`
2. `The rights and obligations of employers | Biznes.gov.pl` — `institutional`
3. `How to post a driver to Poland - State Labour Inspection` — `institutional`

Selected:
- `gov.pl` remote-work page
- `Biznes.gov.pl` employer-rights page

Interpretation:
- previous CEJSH-led shape did not repeat in this live run
- again, the active gap is not missing official survival; it is **exact-subject precision inside an already-official pool**

### 3. Polish-labour-law query
Query:
- `praca zdalna obowiązki pracodawcy zgłoszenie oficjalne gov.pl pip`

Observed retrieval query:
- `praca zdalna obowiązki pracodawcy zgłoszenie site:gov.pl OR site:pip.gov.pl OR site:zus.pl`

Fresh candidate pool:
1. `Prawo do bycia offline - PARP - Centrum Rozwoju MŚP` — `institutional`
2. `Praca zdalna - Państwowa Inspekcja Pracy` (PDF) — `institutional`
3. `Zgłoszenie oferty pracy - Urząd Pracy m.st. Warszawy - Wortal PSZ` — `institutional`

Selected:
- `PARP` article
- `PIP` PDF `Praca zdalna`

Interpretation:
- this row is the clearest remaining bad case
- the right official labour-law/PIP source is present, but it loses rank-1 to a broader adjacent institutional article (`PARP`)
- that is best classified as **present but under-ranked in shaping**, not missing upstream
- secondary note: this run also degraded in `evidence_judge` (`validation_fallback`), so the row is both quality-weak and less receipt-clean than the others

### 4. Employer-duty / exact-subject query
Query:
- `Poland employer remote work obligations labour ministry official faq`

Observed retrieval query:
- `Poland employer remote work obligations official labour ministry FAQ site:gov.pl OR site:gov.pl/web/rodzina-i-polityka-spoleczna OR site:gov.pl/web/rynek-pracy`

Fresh candidate pool:
1. `Remote work - Ministry of Family, Labour and Social Policy - Gov.pl` — `institutional`
2. `Remote work permanently included in the Labour Code. The President ...` — `institutional`
3. `Basic information on labour law - Gov.pl website - Gov.pl` — `institutional`

Selected:
- `gov.pl` remote-work page
- `gov.pl` labour-code article

Interpretation:
- this is the healthiest of the four runs
- but it still does not produce a narrow employer-obligations FAQ winner; it produces a pair of broad official pages from the same ministry family
- this is therefore still **selected but too broad**, though much healthier than the older advisory/commercial drift

## Updated synthesis

The fresh live pass changes the diagnosis materially:
- the dominant problem is **not provider volatility anymore**
- the dominant problem is now **exact-subject precision inside already-official institutional pools**
- the one clearest sub-problem is:
  - Polish labour-law phrasing can still surface the right PIP source, but the current shaping/ranking lets a broader adjacent institutional article outrank it

## Recommended next bounded slice

`exact-subject-target-quality-refinement-v1`

Why this is now the best next move:
- all four live runs surfaced official/institutional pools
- three of the four runs are mainly limited by broad-official selection rather than missing official survival
- the fourth run (`praca zdalna ...`) shows the sharper version of the same family problem: the best exact-subject official candidate is present but under-ranked

## What this next slice should target

Bounded goal:
- strengthen retrieval/shaping preference for the most exact-subject official candidate **within** an already-institutional pool
- without reopening broad selector-policy expansion
- without undoing the conservative selected-evidence contract rollback

Most likely focal signals:
- stronger penalty for adjacent-but-broad institutional pages when a more exact-subject institutional page is present
- stronger preference for title/path specificity over generic institutional authority once official survival is already satisfied
- keep the change bounded to retrieval/target-quality behavior, not downstream trust semantics
