# SourceTrace v2 authority-relevance source-typing unknown-bucket diagnostics v1 — 2026-06-28

## Goal

Inspect the recurring live weak-case sources that still land in `source_type=unknown` before refining the classifier again.

This slice stays diagnostic-only.
No new source classes or selector-policy changes are bundled into it.

## Scope

Used a few representative live queries from the weak-case set and inspected the candidate/readback surface after the current source-typing-v2 classifier.

Focus:
- which sources still fall into `unknown`
- whether they look like recurring source families
- whether the next bounded refinement should add a few markers or split the bucket further

## Main findings

The remaining `unknown` bucket is not random noise.
It now looks like a few recurring real-world source families that the current shallow classifier still does not recognize cleanly.

### 1) Professional/practitioner consultancy sites
Example seen in live checks:
- `vansurksum.com`
- selected title shape: break-glass / Entra operational article

Interpretation:
- this is not institutional
- not clearly vendor in the current bounded taxonomy
- not caught by current commentary markers because it is not on a generic blog/social/law-firm host pattern
- this suggests a recurring **practitioner-consultancy/advisory** shape that is currently falling into `unknown`

### 2) Association / community / hosted document surfaces
Example seen in live checks:
- `cloc.org/wp-content/.../Practical-Guidance-on-Managing-Legal-Holds_Opentext_...pdf`

Interpretation:
- the document itself is vendor-authored/practical
- the host surface is an association/community site rather than a vendor host
- current bounded classifier misses this because host-only vendor markers do not catch the document provenance implied by title/path
- this is a real recurring source shape worth handling more explicitly if it keeps appearing

### 3) Practical commercial sites with neutral hosts
Example from the remote-work line:
- `getsix`-style practical guidance pages can still fall into `unknown`

Interpretation:
- these are neither institutional nor clearly social/blog commentary in the current marker set
- they are often advisory/commercial guidance pages with weakly distinctive host/title markers
- again, this points to a recurring professional/advisory bucket hiding inside `unknown`

## Main conclusion

The next bounded classifier refinement should probably **not** split the taxonomy broadly yet.

The sharper move is smaller:
- keep the current four buckets,
- but improve markers for a recurring professional/advisory shape,
- and improve document-provenance hints for hosted PDFs whose title/path clearly signal vendor/practical origin.

In other words:
- the unknown bucket is now narrow enough to reason about,
- and the next bounded improvement can still be marker-based rather than taxonomy-expanding.

## Practical verdict

Do not add a new class just because the unknown bucket still exists.
The current evidence does not yet force a broader taxonomy.

A smaller next move looks better:
- refine marker coverage for recurring advisory/professional hosts,
- and refine title/path-based vendor hints for hosted practical PDFs.

## Recommended next bounded slice

`authority-relevance-source-typing-v3`

Goal:
- keep the same four source-type buckets
- reduce `unknown` for recurring professional/advisory hosts and hosted vendor/practical PDFs
- keep downstream selector policy unchanged in the same slice
