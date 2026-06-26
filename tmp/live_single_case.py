import json
import sys
import urllib.request

BASE = 'http://127.0.0.1:8000'
OWNER = 'wojtek_known_case'
QUERY = 'Co ustaliła NIK w sprawie nadzoru KNF nad spółką GetBack S.A.? Skup się na oficjalnych ustaleniach, nie na doniesieniach medialnych.'


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


started = post_json('/api/research/start', {'owner_id': OWNER, 'query': QUERY})
job_id = started['job']['job_id']
post_empty(f'/api/research/run/{job_id}')
result = get_json(f'/api/research/result/{job_id}')

from pathlib import Path

def latest_mtime(path: str) -> float:
    try:
        return Path(path).stat().st_mtime
    except FileNotFoundError:
        return -1.0

print(json.dumps({
    'job_id': job_id,
    'result': result,
    'server_mtimes': {
        'research_runtime_py': latest_mtime('src/sourcetrace/application/research_runtime.py'),
        'research_runtime_pyc': latest_mtime('src/sourcetrace/application/__pycache__/research_runtime.cpython-313.pyc'),
        'local_launcher_py': latest_mtime('src/sourcetrace/local_launcher.py'),
    }
}, ensure_ascii=False))
