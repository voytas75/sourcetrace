# SourceTrace Real-Data Campaign Corpus v1

Status: frozen corpus ledger for the first controlled 10-document campaign
Parent SSOT: `docs/plans/2026-05-21-real-data-test-use-ssot.md`
Last updated: 2026-05-21

## Purpose
This file freezes the first-pass real-data corpus for SourceTrace controlled test-use.

It exists to make the campaign reproducible and to keep article selection separate from later observation notes.

## Selection rules used
- Keep the first pass English-first for easier comparison across notes.
- Prefer accessible mainstream news text before specialized PDFs or paywalled longform.
- Cover the four campaign buckets from the execution SSOT.
- Include at least:
  - short factual briefs,
  - longer analytical/political-economic articles,
  - quotes/caveats/mixed-certainty articles,
  - weaker or secondary-source shapes.
- Keep a few deliberately imperfect inputs so credibility and caution behavior can be observed, not just best-case extraction.
- Avoid using the same article in multiple buckets.
- Mark metadata gaps explicitly instead of silently inventing them.

## Bucket distribution
- Bucket A — straightforward factual briefs: 3
- Bucket B — longer analytical articles: 3
- Bucket C — quotes / caveats / mixed certainty: 2
- Bucket D — weak / secondary / noisy source shapes: 2
- Total frozen items: 10

## Campaign items

### A1
- `case_id`: `campaign-a1-reuters-south-africa-risks`
- `document_id`: `doc-a1-reuters-south-africa-risks`
- `bucket`: `A — straightforward factual brief`
- `publisher`: `Reuters`
- `title`: `S&P says it is watching South Africa coalition, Middle East conflict risks for wider Africa`
- `url`: `https://www.reuters.com/world/africa/sp-says-it-is-watching-south-africa-coalition-middle-east-conflict-risks-wider-2026-05-13/`
- `published_at`: `2026-05-13T12:35:41Z`
- `language`: `en`
- `selection_reason`: short factual macro/politics brief with a few attributable statements and numeric facts; good baseline for concise extraction.

### A2
- `case_id`: `campaign-a2-bbc-us-inflation-energy-shock`
- `document_id`: `doc-a2-bbc-us-inflation-energy-shock`
- `bucket`: `A — straightforward factual brief`
- `publisher`: `BBC`
- `title`: `US inflation jumps to 3.8% as energy costs surge from Iran war`
- `url`: `https://www.bbc.com/news/articles/c202pgxx89lo`
- `published_at`: `2026-05-12`
- `language`: `en`
- `selection_reason`: compact factual macro brief with numeric facts, a clear main event, and limited interpretive branching; good second baseline after Reuters A1.

### A3
- `case_id`: `campaign-a3-bbc-us-jobs-april`
- `document_id`: `doc-a3-bbc-us-jobs-april`
- `bucket`: `A — straightforward factual brief`
- `publisher`: `BBC`
- `title`: `US jobs data beats expectations for second month in a row`
- `url`: `https://www.bbc.com/news/articles/cx21664lp32o`
- `published_at`: `do weryfikacji exact date in ledger; search result confirms active BBC article in May 2026`
- `language`: `en`
- `selection_reason`: short labor-market brief with clean numeric facts, expectation-vs-outcome framing, and a few attributed forecasts; good factual extraction stress without long analytical drift.

### B1
- `case_id`: `campaign-b1-ap-trump-tax-cuts-inflation`
- `document_id`: `doc-b1-ap-trump-tax-cuts-inflation`
- `bucket`: `B — longer analytical article`
- `publisher`: `AP News`
- `title`: `Tax cuts collide with inflation as voters weigh Trump's economy in the midterms`
- `url`: `https://apnews.com/article/trump-north-carolina-senate-big-beautiful-bill-09c3d170f57f56c74a7e4e35d6cf2dee`
- `published_at`: `do weryfikacji exact timestamp from extracted article body`
- `language`: `en`
- `selection_reason`: longer analytical political-economy piece with argumentation, examples, claims of exaggeration, and mixed perspectives.

### B2
- `case_id`: `campaign-b2-bbc-global-economy-tariffs-2026`
- `document_id`: `doc-b2-bbc-global-economy-tariffs-2026`
- `bucket`: `B — longer analytical article`
- `publisher`: `BBC`
- `title`: `How tariffs will continue to reshape the global economy in 2026`
- `url`: `https://www.bbc.com/news/articles/czejp3gep63o`
- `published_at`: `2026-01-07`
- `language`: `en`
- `selection_reason`: long explanatory macro article with many causal links, expert viewpoints, and paraphrase risk across trade, inflation, and growth themes.

### B3
- `case_id`: `campaign-b3-bbc-gulf-economies-iran-conflict`
- `document_id`: `doc-b3-bbc-gulf-economies-iran-conflict`
- `bucket`: `B — longer analytical article`
- `publisher`: `BBC`
- `title`: `Gulf economies face long-term hit from Iran conflict`
- `url`: `https://www.bbc.com/news/articles/c0k257g8jk5o`
- `published_at`: `2026-05-06`
- `language`: `en`
- `selection_reason`: long regional economic analysis with multi-sector impacts, projections, and expert interpretation; useful for checking whether analytical claims stay traceable.

### C1
- `case_id`: `campaign-c1-bbc-uk-growth-risks`
- `document_id`: `doc-c1-bbc-uk-growth-risks`
- `bucket`: `C — quotes / caveats / mixed certainty`
- `publisher`: `BBC`
- `title`: `UK growth forecast upgraded by IMF but 'risks' remain`
- `url`: `https://www.bbc.com/news/articles/cm2p72mmddyo`
- `published_at`: `2026-05-21`
- `language`: `en`
- `selection_reason`: explicit institutional attribution, forecast revisions, hedging language, and multiple risk statements; good test of caveat preservation.

### C2
- `case_id`: `campaign-c2-bbc-uk-inflation-expected-rise`
- `document_id`: `doc-c2-bbc-uk-inflation-expected-rise`
- `bucket`: `C — quotes / caveats / mixed certainty`
- `publisher`: `BBC`
- `title`: `Inflation falls to 2.8%, but is expected to rise from here`
- `url`: `https://www.bbc.com/news/articles/c4g0e0p4p2go`
- `published_at`: `do weryfikacji exact date in ledger; article body confirms May 2026`
- `language`: `en`
- `selection_reason`: mixes hard stats with forecast language, expert quotes, and conditional policy interpretation; good overconfidence/flattening test.

### D1
- `case_id`: `campaign-d1-ap-einpresswire-war-market-trends`
- `document_id`: `doc-d1-ap-einpresswire-war-market-trends`
- `bucket`: `D — weak / secondary / noisy source`
- `publisher`: `AP News / EIN Presswire mirror`
- `title`: `7 Historical Stock Market Trends Triggered By The Impact Of Wars`
- `url`: `https://apnews.com/press-release/ein-presswire-newsmatics/7-historical-stock-market-trends-triggered-by-the-impact-of-wars-2f663c743ed6be026e581bd5ade65dc5`
- `published_at`: `2026-05-08T00:00:00Z`
- `language`: `en`
- `selection_reason`: promotional press-release framing with broad claims and weaker evidentiary posture; useful for credibility caution behavior.

### D2
- `case_id`: `campaign-d2-ap-photo-gallery-romania-hat-walk`
- `document_id`: `doc-d2-ap-photo-gallery-romania-hat-walk`
- `bucket`: `D — weak / secondary / noisy source`
- `publisher`: `AP News`
- `title`: `Photos: Romania tips its hat to World Hat Walk`
- `url`: `https://apnews.com/photo-gallery/photos-romania-tips-hat-world-hat-walk-c84ec4558065424c9962981bfab98287`
- `published_at`: `2026-05-11T03:23:37Z`
- `language`: `en`
- `selection_reason`: intentionally noisy repeated-caption text; useful to see whether prepare/extraction can recognize a low-value input shape and how credibility/usefulness degrades.

## Operational reading
- **Confirmed and frozen enough to execute now:** all 10 selected items above.
- **Still do weryfikacji but non-blocking before execution:**
  - exact publication date for A3
  - exact publication timestamp for B1
  - exact publication date for C2
- **Resolved during freeze:**
  - removed duplicate use of the same Reuters/AP articles across multiple buckets
  - replaced placeholder / unresolved items with concrete URLs where possible
  - kept D bucket intentionally weak/noisy rather than “interesting but strong”

## Freeze verdict
- The first 10-document campaign corpus is now frozen enough to start execution.
- Diversity is acceptable across buckets and source shapes.
- Metadata gaps are explicit and small enough not to block the first pass.
- This ledger is suitable as the campaign SSOT for document selection.

## Recommended execution order
1. A1
2. A2
3. A3
4. C1
5. C2
6. B1
7. B2
8. B3
9. D1
10. D2

Rationale:
- start with cleaner factual items,
- then test caveat/hedging preservation before deeper analytical drift,
- then pressure-test longer analysis,
- end with weak/noisy inputs once normal behavior is already known.

## Next step
Use this file as the frozen corpus ledger and begin observation-note execution document by document through `PYTHONPATH=src ./.venv/bin/python -m sourcetrace.www_control start --mode local-launcher`.
