# SourceTrace v2 retrieval semantic-scoring contract v1 — 2026-07-19

## Problem observed

A live quality pack found that the retrieval target-quality scorer tokenized search-engine constraints such as `site:gov.pl` as if `site`, `gov`, `pl`, and a constrained domain label were part of the user's substantive question. That allowed corpus-selection syntax to influence evidence relevance ranking.

The same scorer compared raw lexical forms, so natural variants such as `employers` and `employer` did not match.

## Decision

The raw refined query remains unchanged for the search provider. Before candidate relevance scoring only, SourceTrace now:

1. removes explicit search-operator clauses (`site:`, `domain:`, `inurl:`, `intitle:`); and
2. applies the existing bounded light token normalization pattern to both semantic query terms and candidate text.

This is provider-neutral and does not encode countries, domains, source-specific rules, or a separate reranking model.

## Intended effect

Search constraints continue to control the candidate corpus but cannot become evidence of topical support. Candidate ranking therefore depends on the semantic request and candidate title/snippet/path rather than the requested host restriction.

## Boundary

This slice does not claim that any retrieved source is substantively sufficient. It improves lexical relevance ranking only. Pair-level evidence sufficiency and operator trust remain separate concerns and must be judged from subsequent live evaluation.

## Verification

- search-operator clauses are absent from semantic focus tokens;
- a morphologically matching substantive result outranks a result that only matches a `site:` constraint;
- the existing retrieval target-quality suite remains green.
