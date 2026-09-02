"""릴리스 승격.

학습은 models/runs/<run_id>/ 에만 쓴다. 배포본을 바꾸는 것은 이 함수뿐이고,
검증을 통과하지 못하면 **아무 파일도 건드리지 않는다**.

2026-09-01 에 최상위 models/ 가 실험 모델로 바뀌어 있던 사고를 구조적으로 막는다.
"""
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))
REQUIRED_FILES = ['model_v1.json', 'golden_v1.json']


def current(models_dir):
    """현재 배포 릴리스 이름. 없으면 None."""
    p = Path(models_dir) / 'current.json'
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding='utf-8')).get('release')


def promote(run_dir, models_dir, release_name, validator):
    run_dir, models_dir = Path(run_dir), Path(models_dir)
    target = models_dir / release_name

    if target.exists():
        raise ValueError(f'릴리스가 이미 있습니다: {target}. 릴리스는 불변입니다')

    for name in REQUIRED_FILES:
        if not (run_dir / name).exists():
            raise ValueError(f'{name} 이 없어 승격할 수 없습니다 ({run_dir})')

    run = json.loads((run_dir / 'run.json').read_text(encoding='utf-8'))
    sc = run.get('success_criteria') or {}
    if not sc:
        raise ValueError('평가 기록이 없습니다. evaluate 를 먼저 실행하세요')
    failed = [k for k, v in sc.items() if not v]
    if failed:
        raise ValueError(f'성공 기준 미달로 승격할 수 없습니다: {", ".join(sorted(failed))}')

    validator(run_dir)          # 스키마·정합 검증. 실패하면 예외가 올라온다

    # 여기까지 통과해야 파일을 만든다
    shutil.copytree(run_dir, target)
    (models_dir / 'current.json').write_text(json.dumps({
        'release': release_name,
        'run_id': run.get('run_id'),
        'promoted_at': datetime.now(KST).isoformat(timespec='seconds'),
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    return target
