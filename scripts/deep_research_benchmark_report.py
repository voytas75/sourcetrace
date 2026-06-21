from __future__ import annotations

import argparse
import json
from pathlib import Path
from textwrap import shorten


def score_from_verdict(value: str | None) -> int:
    if value == 'strong':
        return 2
    if value == 'mixed':
        return 1
    return 0


def infer_query_class(query: str, evaluation: dict[str, object]) -> str:
    q = (query or '').lower()
    qclass = str(evaluation.get('query_class') or '')
    if qclass:
        return qclass
    if 'sccm' in q or 'configuration baseline' in q:
        return 'procedural_admin'
    if 'ethusdc' in q or 'ostatniego tygodnia' in q:
        return 'market_symbol'
    if 'architecture' in q:
        return 'broad_concept'
    return 'unknown'


def score_query(result_payload: dict[str, object]) -> dict[str, object]:
    result = result_payload.get('result', {}) if isinstance(result_payload, dict) else {}
    query = str(result.get('query', ''))
    stats = result.get('stats', {}) if isinstance(result.get('stats'), dict) else {}
    evaluation = result.get('evaluation', {}) if isinstance(result.get('evaluation'), dict) else {}
    report = str(result.get('result') or result.get('raw_report') or '')
    findings = result.get('raw_findings', []) if isinstance(result.get('raw_findings'), list) else []
    providers = [str(item) for item in stats.get('search_providers', [])]

    scores = {
        'api': 2 if str(result.get('status', '')) in {'done', 'error', 'cancelled'} else 0,
        'source_quality': score_from_verdict(str(evaluation.get('source_quality_verdict') or '')),
        'relevance': score_from_verdict(str(evaluation.get('relevance_verdict') or '')),
        'truthfulness': score_from_verdict(str(evaluation.get('truthfulness_verdict') or '')),
        'shape': 2 if all(marker in report for marker in ('## Current answer', '## Key findings', '## Uncertainty', '## Next checks')) else 0,
        'telemetry': 2 if providers and providers != ['stub-search'] else 0,
    }
    total = sum(scores.values())
    query_class = infer_query_class(query, evaluation)
    notes = []
    if evaluation:
        reasons = evaluation.get('source_quality_reasons') or []
        risks = evaluation.get('relevance_risks') or []
        overclaim = evaluation.get('overclaim_risks') or []
        missing_checks = evaluation.get('missing_checks') or []
        if reasons:
            notes.append('source: ' + '; '.join(str(item) for item in reasons[:2]))
        if risks:
            notes.append('relevance: ' + '; '.join(str(item) for item in risks[:2]))
        if overclaim:
            notes.append('truth: ' + '; '.join(str(item) for item in overclaim[:2]))
        if missing_checks:
            notes.append('next: ' + '; '.join(str(item) for item in missing_checks[:1]))
    if not notes:
        notes.append('No evaluator notes available.')

    return {
        'query': query,
        'query_class': query_class,
        'providers': providers,
        'scores': scores,
        'total': total,
        'findings_count': len(findings),
        'should_revise_report': bool(evaluation.get('should_revise_report', False)),
        'recommended_next_check': str(evaluation.get('recommended_next_check') or ''),
        'notes': notes,
        'report_preview': shorten(report.replace('\n', ' '), width=260, placeholder='…'),
    }


def render_markdown(scored: list[dict[str, object]]) -> str:
    lines = [
        '# Deep Research benchmark report',
        '',
        'Status: generated from benchmark result payloads',
        '',
        '| Query | Class | API | Source | Relevance | Truth | Shape | Telemetry | Total | Revise |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---|',
    ]
    for item in scored:
        s = item['scores']
        lines.append(
            f"| `{item['query']}` | `{item['query_class']}` | {s['api']} | {s['source_quality']} | {s['relevance']} | {s['truthfulness']} | {s['shape']} | {s['telemetry']} | {item['total']} | {'yes' if item['should_revise_report'] else 'no'} |"
        )
    lines.extend(['', '## Per-query notes', ''])
    for item in scored:
        lines.append(f"### {item['query']}")
        lines.append(f"- query_class: `{item['query_class']}`")
        lines.append(f"- providers: `{item['providers']}`")
        lines.append(f"- findings_count: `{item['findings_count']}`")
        lines.append(f"- recommended_next_check: {item['recommended_next_check'] or 'n/a'}")
        lines.append(f"- report_preview: {item['report_preview']}")
        for note in item['notes']:
            lines.append(f"- {note}")
        lines.append('')
    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='Path to benchmark result JSON file')
    parser.add_argument('--output', help='Optional markdown output path')
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text())
    if not isinstance(payload, list):
        raise SystemExit('expected top-level list of benchmark results')
    scored = [score_query(item.get('payload', item)) for item in payload if isinstance(item, dict)]
    markdown = render_markdown(scored)
    if args.output:
        Path(args.output).write_text(markdown)
    print(markdown)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
