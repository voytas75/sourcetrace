import json
import urllib.request

BASE = 'http://127.0.0.1:8000'


def post_json(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f'{BASE}{path}',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))


def post_empty(path: str) -> dict:
    req = urllib.request.Request(f'{BASE}{path}', data=b'', method='POST')
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode('utf-8'))


def get_json(path: str) -> dict:
    with urllib.request.urlopen(f'{BASE}{path}', timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))


def run_case(owner: str, query: str) -> tuple[str, dict]:
    started = post_json('/api/research/start', {'owner_id': owner, 'query': query})
    job_id = started['job']['job_id']
    post_empty(f'/api/research/run/{job_id}')
    result = get_json(f'/api/research/result/{job_id}')
    return job_id, result


def summarize(label: str, job_id: str, payload: dict) -> None:
    result = payload.get('result') or {}
    stats = result.get('stats') or {}
    sources = result.get('sources') or []
    print(f'## {label} {job_id}')
    print('completion_mode=', result.get('completion_mode'))
    print('search_providers=', stats.get('search_providers'))
    print('pre_extraction_seen=', stats.get('pre_extraction_sources_seen'))
    print('pre_extraction_kept=', stats.get('pre_extraction_sources_kept'))
    print('authority_filter_fallback_used=', stats.get('authority_filter_fallback_used'))
    print('top_sources=')
    for item in sources[:5]:
        print('-', item.get('url'))
    print('report_head=')
    print((result.get('result') or '')[:700].replace(chr(10), ' '))
    print()


def main() -> int:
    same_job, same_result = run_case('wojtek_live_same_v2', 'Co ustaliła NIK w sprawie Szpitala Południowego w Warszawie?')
    other_job, other_result = run_case('wojtek_live_other_v2', 'Wpływ pracy zdalnej na zdrowie psychiczne pracowników po 2023 roku')
    summarize('same', same_job, same_result)
    summarize('other', other_job, other_result)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
