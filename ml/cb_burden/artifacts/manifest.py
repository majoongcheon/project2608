"""실행 기록.

"이 모델은 어떻게 만들어졌나"에 답하는 파일이다. 스냅샷 해시·git 커밋·라이브러리 버전이
없으면 몇 주 뒤에 같은 모델을 다시 만들 수 없다(원칙 IV).
"""
import json
import platform
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cb_burden import config
from cb_burden.data.snapshot import sha256

KST = timezone(timedelta(hours=9))


def _git():
    def run(args):
        try:
            return subprocess.run(args, capture_output=True, text=True,
                                  timeout=5).stdout.strip()
        except Exception:
            return ''
    return {'sha': run(['git', 'rev-parse', '--short', 'HEAD']),
            'dirty': bool(run(['git', 'status', '--porcelain']))}


def _versions():
    v = {'python': platform.python_version()}
    for name in ('numpy', 'sklearn', 'joblib'):
        try:
            v[name] = __import__(name).__version__
        except Exception:
            v[name] = None
    import cb_burden
    v['cb_burden'] = cb_burden.__version__
    return v


def start(run_dir, snapshot_meta, snapshot_path, model_version, question_set_version):
    return {
        'run_id': Path(run_dir).name,
        'started_at': datetime.now(KST).isoformat(timespec='seconds'),
        'finished_at': None,
        'git': _git(),
        'snapshot': {'path': str(snapshot_path),
                     'sha256': (snapshot_meta or {}).get('sha256'),
                     'rows': (snapshot_meta or {}).get('rows')},
        'seed': config.SEED,
        'versions': _versions(),
        'stages': [],
        'artifacts': {},
        'success_criteria': {},
        'model_version': model_version,
        'question_set_version': question_set_version,
    }


def finish(run, run_dir):
    run_dir = Path(run_dir)
    run['finished_at'] = datetime.now(KST).isoformat(timespec='seconds')
    run['artifacts'] = {
        p.name: 'sha256:' + sha256(p)
        for p in sorted(run_dir.iterdir())
        if p.is_file() and p.name != 'run.json'
    }
    (run_dir / 'run.json').write_text(
        json.dumps(run, ensure_ascii=False, indent=2), encoding='utf-8')
    return run
