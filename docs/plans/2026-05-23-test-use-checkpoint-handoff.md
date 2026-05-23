# 2026-05-23 SourceTrace test-use checkpoint / handoff

## Status
- Można przerwać development i przejść do testowania użycia.
- Runtime quality slices z tej serii są domknięte na poziomie checkpointu roboczego.
- Runtime jest zatrzymany.

## Co zmieniono
### Extraction usefulness controls
- anchoring fallback: `chunk-span:unknown` nie blokuje już fallbacku do `position_reference`
- prompt contract: extraction prompt zachowuje attribution-bearing wording (`X said`, `according to`, named institution ownership)
- outcome diagnostics: `ClaimExtractionOutcome.review_cautions`
- review cautions v1/v2/v3:
  - `weak_source_posture`
  - `low_yield_repeated_captions`
- API surfacing:
  - `review_cautions` wychodzi w extraction diagnostics payload

### Continuity pack slice
- dodane guidance docs dla continuity pack
- dodane przykładowe continuity packi
- dodany seam/capability pod continuity pack preview w SourceTrace
- readiness/runtime/capabilities pokazują continuity pack support

## Co zweryfikowano
### Unit / baseline
- pełny suite: `PYTHONPATH=src pytest -q`
- wynik przy checkpoint closeout: `326 passed`

### Live-confirmed
- C1 / B3:
  - attribution-bearing wording wróciło do extracted claims
  - `chunk-span:unknown = 0`
- D1:
  - `review_cautions = ["weak_source_posture"]`
- D2:
  - `review_cautions = ["low_yield_repeated_captions"]`
  - case domknięty po reclassify na single-chunk gallery seam

## Najważniejsze reclassify z tej serii
1. problem attribution nie był tylko runtime fallbackem — część flatteningu siedziała w prompt contract
2. low-yield miss nie był problemem surfacingu ani exact-string mismatch
3. prawdziwy D2 seam okazał się:
   - `title = Photo gallery`
   - `chunk_count = 1`
   - `claim_count >= 2`
   - banalne observational claims z jednego chunku
4. wcześniejszy warunek `len(chunks) >= 2` był błędnym założeniem i został usunięty

## Gotowe do test-use
Można teraz przejść do:
- realnych prób użycia
- oceny, czy `review_cautions` pomagają operatorowi
- sprawdzenia, czy caution signals są wystarczające na szerszym corpusie

## Nadal do weryfikacji w usage
- coverage heurystyk poza D1/D2
- czy same diagnostics wystarczą, czy później potrzebny jest review/report UX surfacing
- czy continuity pack preview powinien dostać osobny endpoint assemble-preview

## Najbardziej proporcjonalne next slices po test-use
1. usage feedback / observation pass na realnych przypadkach
2. jeśli wyjdzie potrzeba: surfacing `review_cautions` do review/report UX
3. osobny API slice: `assemble-preview` endpoint dla continuity packs
