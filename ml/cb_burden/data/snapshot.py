"""학습 입력 스냅샷.

DB 는 바뀐다. 같은 모델을 다시 만들려면 **그때 무엇을 읽었는지**가 파일로 남아야 한다.
스냅샷은 덮어쓰지 않는다 — 새 스냅샷은 새 파일명으로 만든다. 덮어쓰면 과거 실행의
run.json 이 가리키는 해시와 실제 파일이 갈라져 재현성이 무너진다(원칙 IV).
"""
import csv
import gzip
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

KST = timezone(timedelta(hours=9))


def meta_path(path):
    """snap.csv.gz -> snap.meta.json"""
    name = Path(path).name
    for suffix in ('.csv.gz', '.gz', '.csv'):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    return Path(path).parent / (name + '.meta.json')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def write(path, features, rows, source_view, db_info=None):
    """rows 는 split·cv_fold·care_burden + 변수들을 담은 dict 목록."""
    path = Path(path)
    if path.exists():
        raise ValueError(
            f'스냅샷이 이미 있습니다: {path}\n'
            f'  스냅샷은 덮어쓰지 않습니다. 새 파일명으로 만드세요')
    path.parent.mkdir(parents=True, exist_ok=True)

    header = ['split', 'cv_fold', 'care_burden'] + list(features)
    with gzip.open(path, 'wt', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow([r[c] for c in header])

    counts = {}
    for r in rows:
        counts[r['split']] = counts.get(r['split'], 0) + 1

    # 원칙 III — 접속 정보는 호스트·DB 이름까지만. 비밀번호는 어디에도 남기지 않는다.
    safe_db = {k: v for k, v in (db_info or {}).items() if k in ('host', 'port', 'database')}
    meta = {
        'created_at': datetime.now(KST).isoformat(timespec='seconds'),
        'source_view': source_view,
        'rows': len(rows),
        'features': len(features),
        'split': counts,
        'sha256': sha256(path),
        'db': safe_db,
    }
    meta_path(path).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    return meta


def read(path):
    """스냅샷을 읽고 해시를 대조한다. 다르면 ValueError."""
    path = Path(path)
    meta = json.loads(meta_path(path).read_text(encoding='utf-8'))
    actual = sha256(path)
    if actual != meta['sha256']:
        raise ValueError(
            f'스냅샷 해시가 메타와 다릅니다. 파일이 바뀌었습니다.\n'
            f'  메타 {meta["sha256"]}\n  실제 {actual}')

    with gzip.open(path, 'rt', encoding='utf-8', newline='') as f:
        rd = csv.reader(f)
        header = next(rd)
        body = list(rd)

    features = header[3:]
    return {
        'features': features,
        'X': np.array([[float(v) for v in r[3:]] for r in body], dtype=np.float64),
        'y': np.array([int(r[2]) for r in body]),
        'split': np.array([r[0] for r in body]),
        'cv_fold': np.array([int(r[1]) for r in body]),
        'meta': meta,
    }
