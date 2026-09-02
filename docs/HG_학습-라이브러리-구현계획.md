# 학습·추론 라이브러리 구현 계획

> **작업자에게:** 이 계획은 작업 단위로 실행한다. 각 단계는 체크박스(`- [ ]`)로 추적한다.
> 설계 근거는 `docs/HG_학습-라이브러리-설계.md` 를 먼저 읽을 것.

**목표** `ml/` 을 파이썬 패키지 `cb_burden` 으로 만들어 학습부터 추론 서비스 제공까지
책임지게 하고, 학습이 배포본을 덮을 수 없게 만든다.

**구조** 단계 함수는 값만 돌려주고 파일 쓰기는 `artifacts/`·`cli.py` 에만 둔다.
학습 산출물은 `models/runs/<run_id>/` 에만 쓰고, 릴리스 교체는 검증을 통과한 `promote`
명령으로만 한다. 추론은 `joblib` 을 읽는 FastAPI 서비스가 맡고, 판정 정책(임계값·가산점)은
Node 가 요청에 실어 보낸다.

**기술** Python 3.9 · scikit-learn 1.6.1 · joblib · FastAPI + uvicorn · pytest ·
Node 20 + Express 4 (기존)

**두 단계는 독립적이다.** Phase A 만 끝내도 그 자체로 가치가 있고 서비스에 영향이 없다.
Phase B 는 서비스를 건드리므로 A 가 끝난 뒤에 시작한다.

---

## 파일 구조

| 파일 | 책임 |
|---|---|
| `ml/pyproject.toml` | 패키지 메타데이터·진입점 |
| `ml/cb_burden/config.py` | 도메인 상수 (클래스·센티널·배제변수·성공기준·시드) |
| `ml/cb_burden/data/source_db.py` | DB 에서 원시 행을 읽는다. **스냅샷 생성에만 쓴다** |
| `ml/cb_burden/data/snapshot.py` | 스냅샷 쓰기·읽기·sha256 |
| `ml/cb_burden/data/integrity.py` | 행수·변수수·fold·배제변수 검증 |
| `ml/cb_burden/artifacts/validate.py` | 산출물 필수 키·자료형·범위·정합·척도 방향 검증 |
| `ml/cb_burden/artifacts/golden.py` | 골든 케이스 생성 |
| `ml/cb_burden/artifacts/release.py` | 승격 규칙과 `current.json` |
| `ml/cb_burden/data/record.py` | 성능 기록 (model_version 필수) |
| `ml/cb_burden/artifacts/manifest.py` | `run.json` 생성 |
| `ml/cb_burden/artifacts/release.py` | `promote` 규칙과 `current.json` |
| `ml/cb_burden/stages/*.py` | baseline·select·calibrate·export·evaluate |
| `ml/cb_burden/explain/saabas.py` | 기여도 계산 (`ml/saabas.py` 이관) |
| `ml/cb_burden/serve/engine.py` | joblib 로드 + 판정. 파일·DB 접근 없음 |
| `ml/cb_burden/serve/schema.py` | 요청·응답 스키마 |
| `ml/cb_burden/serve/app.py` | FastAPI 앱 (`/predict`·`/health`) |
| `ml/cb_burden/cli.py` | 명령 조립 |
| `backend/src/services/inferenceClient.ts` | 파이썬 서비스 호출 + 장애 처리 |

---

# Phase A — 학습 라이브러리

## Task A0: 의존성과 패키지 뼈대

**Files:**
- Modify: `ml/requirements.txt`
- Create: `ml/pyproject.toml`, `ml/cb_burden/__init__.py`, `ml/tests/__init__.py`

- [ ] **Step 1: 의존성 추가**

`ml/requirements.txt` 끝에 덧붙인다. `fastapi`·`uvicorn` 은 지금 사용자 계정에만 설치돼
있어 다른 장비에서 재현되지 않는다. `.pylibs` 로 벤더링한다.

```
pytest>=8.0
fastapi>=0.115
uvicorn>=0.30
httpx>=0.27
```

- [ ] **Step 2: 설치**

Run: `pip3 install --target ml/.pylibs -r ml/requirements.txt`
Expected: 설치 완료. 오류 없음

- [ ] **Step 3: 설치 확인**

Run:
```bash
PYTHONPATH=ml/.pylibs python3 -c "import pytest, fastapi, uvicorn, httpx; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: 패키지 파일 생성**

`ml/cb_burden/__init__.py`
```python
"""돌봄부담 진단 모델 — 학습·검증·추론 서비스.

배포되는 것은 models/<release>/ 의 산출물이다. 이 패키지 자체는 서비스에 실리지 않지만
serve 하위만은 예외로 추론 서비스로 구동된다.
"""
__version__ = '0.1.0'
```

`ml/tests/__init__.py` — 빈 파일

`ml/pyproject.toml`
```toml
[project]
name = "cb-burden"
version = "0.1.0"
description = "돌봄부담 진단 모델 학습·추론"
requires-python = ">=3.9"

[project.scripts]
cb-burden = "cb_burden.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 5: 커밋**

```bash
git add ml/requirements.txt ml/pyproject.toml ml/cb_burden/__init__.py ml/tests/__init__.py
git -c user.name="오현근" commit -m "chore(ml): cb_burden 패키지 뼈대와 테스트 의존성"
```

---

## Task A1: 도메인 상수

**Files:**
- Create: `ml/cb_burden/config.py`, `ml/tests/test_config.py`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`ml/tests/test_config.py`
```python
"""도메인 상수 — 헌법·스펙이 정한 값이라 실험으로 바꾸지 않는다."""
from cb_burden import config


def test_척도는_1이_최고부담인_역방향이다():
    assert config.CLASSES == [1, 2, 3, 4, 5]
    assert config.HIGH_BURDEN_LABELS == [1, 2]


def test_배제변수_6개가_그대로_있다():
    # FR-004b — target 과 같은 블록이라 입력에 쓰지 않는다
    assert len(config.EXCLUDED_FEATURES) == 6
    assert 'caregiver_life_satisfaction' in config.EXCLUDED_FEATURES


def test_성공기준이_스펙과_같다():
    sc = config.SUCCESS_CRITERIA
    assert sc['max_f1_loss'] == 0.03
    assert sc['max_recall_loss'] == 0.05
    assert sc['min_recall_abs'] == 0.70
    assert sc['max_undecidable_rate'] == 0.10


def test_임계값은_여기_없다():
    # 판정 임계값은 설정(cb_config_v1)이 소유한다. 코드에 못박지 않는다(FR-009c).
    assert not hasattr(config, 'TAU_CONF')
    assert not hasattr(config, 'TAU_DENS')
```

- [ ] **Step 2: 실패 확인**

Run: `PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests/test_config.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'cb_burden.config'`

- [ ] **Step 3: 구현**

`ml/cb_burden/config.py`
```python
"""도메인 상수.

여기 있는 값은 헌법(.specify/memory/constitution.md)과 스펙이 정한 것이다.
실험 결과로 바꾸지 않는다. 바꾸려면 스펙을 먼저 고친다.
"""

# 내부 라벨. 1 이 최고부담인 역방향 척도다 — 임계값 비교가 <= 인 이유.
CLASSES = [1, 2, 3, 4, 5]
HIGH_BURDEN_LABELS = [1, 2]

MISSING_SENTINEL = -1
TARGET = 'care_burden'

# FR-004b — target(I13) 과 같은 블록의 6변수. 입력·문항 어디에도 쓰지 않는다.
EXCLUDED_FEATURES = frozenset({
    'caregiver_life_satisfaction', 'care_difficulty_top1', 'needed_care_service_type',
    'work_care_gap_hours', 'work_care_gap_exp', 'integrated_care_awareness',
})

# SC-004 · SC-005 · SC-016
SUCCESS_CRITERIA = {
    'max_f1_loss': 0.03,
    'max_recall_loss': 0.05,
    'min_recall_abs': 0.70,
    'max_undecidable_rate': 0.10,
}

SEED = 42

# 데이터 실측 (2026-09-01 확인). integrity 검증에 쓴다.
EXPECTED_ROWS = 3000
EXPECTED_TRAIN = 2398
EXPECTED_TEST = 602
EXPECTED_FEATURES = 38
EXPECTED_FOLDS = [1, 2, 3, 4, 5]
```

- [ ] **Step 4: 통과 확인**

Run: `PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests/test_config.py -q`
Expected: `4 passed`

- [ ] **Step 5: 커밋**

```bash
git add ml/cb_burden/config.py ml/tests/test_config.py
git -c user.name="오현근" commit -m "feat(ml): 도메인 상수를 config.py 로 모은다"
```

---

## Task A2: 스냅샷 — 쓰기·읽기·해시

**Files:**
- Create: `ml/cb_burden/data/__init__.py`, `ml/cb_burden/data/snapshot.py`, `ml/tests/test_snapshot.py`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`ml/tests/test_snapshot.py`
```python
"""스냅샷 — 학습 입력을 파일로 고정한다. 해시가 다르면 학습을 시작하지 않는다."""
import json
import numpy as np
import pytest
from cb_burden.data import snapshot


def _sample():
    return {
        'features': ['a', 'b'],
        'rows': [
            {'split': 'train', 'cv_fold': 1, 'care_burden': 2, 'a': 1.0, 'b': -1.0},
            {'split': 'test', 'cv_fold': 0, 'care_burden': 3, 'a': 2.0, 'b': 5.0},
        ],
    }


def test_쓰고_읽으면_같은_값이_나온다(tmp_path):
    p = tmp_path / 'snap.csv.gz'
    snapshot.write(p, _sample()['features'], _sample()['rows'], source_view='v_test')
    got = snapshot.read(p)
    assert got['features'] == ['a', 'b']
    assert got['y'].tolist() == [2, 3]
    assert got['split'].tolist() == ['train', 'test']
    assert got['X'][0].tolist() == [1.0, -1.0]


def test_메타에_해시와_행수가_남는다(tmp_path):
    p = tmp_path / 'snap.csv.gz'
    snapshot.write(p, _sample()['features'], _sample()['rows'], source_view='v_test')
    meta = json.loads(p.with_suffix('').with_suffix('.meta.json').read_text(encoding='utf-8'))
    assert meta['rows'] == 2
    assert meta['features'] == 2
    assert meta['source_view'] == 'v_test'
    assert len(meta['sha256']) == 64


def test_비밀번호는_메타에_남기지_않는다(tmp_path):
    # 원칙 III — 저장 금지 항목은 남기지 않는다
    p = tmp_path / 'snap.csv.gz'
    snapshot.write(p, _sample()['features'], _sample()['rows'], source_view='v_test')
    raw = p.with_suffix('').with_suffix('.meta.json').read_text(encoding='utf-8')
    assert 'password' not in raw.lower()


def test_파일이_변조되면_읽기가_거부된다(tmp_path):
    p = tmp_path / 'snap.csv.gz'
    snapshot.write(p, _sample()['features'], _sample()['rows'], source_view='v_test')
    p.write_bytes(p.read_bytes() + b'\x00')
    with pytest.raises(ValueError, match='해시'):
        snapshot.read(p)
```

- [ ] **Step 2: 실패 확인**

Run: `PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests/test_snapshot.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'cb_burden.data'`

- [ ] **Step 3: 구현**

`ml/cb_burden/data/__init__.py` — 빈 파일

`ml/cb_burden/data/snapshot.py`
```python
"""학습 입력 스냅샷.

DB 는 바뀐다. 같은 모델을 다시 만들려면 **그때 무엇을 읽었는지**가 파일로 남아야 한다.
스냅샷은 덮어쓰지 않는다. 새 스냅샷은 새 파일명으로 만든다.
"""
import csv
import gzip
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np

KST = timezone(timedelta(hours=9))
META_SUFFIX = '.meta.json'


def _meta_path(path):
    # snap.csv.gz -> snap.meta.json
    return Path(str(path).replace('.csv.gz', '') + META_SUFFIX)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def write(path, features, rows, source_view, db_info=None):
    """rows 는 split·cv_fold·care_burden + 변수들을 담은 dict 목록."""
    path = Path(path)
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
    meta = {
        'created_at': datetime.now(KST).isoformat(timespec='seconds'),
        'source_view': source_view,
        'rows': len(rows),
        'features': len(features),
        'split': counts,
        'sha256': sha256(path),
        # 원칙 III — 접속 정보는 호스트·DB 이름까지만. 비밀번호는 남기지 않는다.
        'db': db_info or {},
    }
    _meta_path(path).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    return meta


def read(path):
    """스냅샷을 읽고 해시를 대조한다. 다르면 ValueError."""
    path = Path(path)
    meta = json.loads(_meta_path(path).read_text(encoding='utf-8'))
    actual = sha256(path)
    if actual != meta['sha256']:
        raise ValueError(
            f'스냅샷 해시가 메타와 다릅니다. 파일이 바뀌었습니다.\n'
            f'  메타 {meta["sha256"]}\n  실제 {actual}')

    with gzip.open(path, 'rt', encoding='utf-8', newline='') as f:
        rd = csv.reader(f)
        header = next(rd)
        body = [row for row in rd]

    features = header[3:]
    split = np.array([r[0] for r in body])
    fold = np.array([int(r[1]) for r in body])
    y = np.array([int(r[2]) for r in body])
    X = np.array([[float(v) for v in r[3:]] for r in body], dtype=np.float64)
    return {'features': features, 'X': X, 'y': y, 'split': split,
            'cv_fold': fold, 'meta': meta}
```

- [ ] **Step 4: 통과 확인**

Run: `PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests/test_snapshot.py -q`
Expected: `4 passed`

- [ ] **Step 5: 커밋**

```bash
git add ml/cb_burden/data ml/tests/test_snapshot.py
git -c user.name="오현근" commit -m "feat(ml): 학습 입력 스냅샷과 해시 검증"
```

---

## Task A3: 무결성 검증

**Files:**
- Create: `ml/cb_burden/data/integrity.py`, `ml/tests/test_integrity.py`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`ml/tests/test_integrity.py`
```python
"""무결성 — 기존 db.py 의 단언을 옮긴 것. 어긋나면 학습을 시작하지 않는다."""
import numpy as np
import pytest
from cb_burden.data import integrity


def _snap(features=None, n_train=2398, n_test=602):
    features = features or [f'f{i}' for i in range(38)]
    n = n_train + n_test
    return {
        'features': features,
        'X': np.zeros((n, len(features))),
        'y': np.ones(n, dtype=int),
        'split': np.array(['train'] * n_train + ['test'] * n_test),
        'cv_fold': np.array([(i % 5) + 1 for i in range(n_train)] + [0] * n_test),
    }


def test_정상_스냅샷은_통과한다():
    integrity.check(_snap())          # 예외가 없으면 통과


def test_행수가_다르면_거부한다():
    with pytest.raises(ValueError, match='train'):
        integrity.check(_snap(n_train=2000))


def test_변수가_38개가_아니면_거부한다():
    with pytest.raises(ValueError, match='설명변수'):
        integrity.check(_snap(features=['a', 'b']))


def test_배제변수가_섞여_있으면_거부한다():
    feats = [f'f{i}' for i in range(37)] + ['work_care_gap_hours']
    with pytest.raises(ValueError, match='FR-004b'):
        integrity.check(_snap(features=feats))
```

- [ ] **Step 2: 실패 확인**

Run: `PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests/test_integrity.py -q`
Expected: FAIL — `No module named 'cb_burden.data.integrity'`

- [ ] **Step 3: 구현**

`ml/cb_burden/data/integrity.py`
```python
"""스냅샷 무결성. ml/db.py 의 assert 를 옮겨 예외로 바꾼 것이다.

assert 는 python -O 에서 사라진다. 판정 근거가 걸린 검사라 예외로 둔다.
"""
from cb_burden import config


def check(snap):
    feats = snap['features']
    split = snap['split']
    n_train = int((split == 'train').sum())
    n_test = int((split == 'test').sum())

    if n_train != config.EXPECTED_TRAIN:
        raise ValueError(f'train 이 {config.EXPECTED_TRAIN} 이 아닙니다: {n_train}')
    if n_test != config.EXPECTED_TEST:
        raise ValueError(f'test 가 {config.EXPECTED_TEST} 가 아닙니다: {n_test}')
    if len(feats) != config.EXPECTED_FEATURES:
        raise ValueError(f'설명변수가 {config.EXPECTED_FEATURES}개가 아닙니다: {len(feats)}')

    folds = sorted(set(int(v) for v in snap['cv_fold'][split == 'train']))
    if folds != config.EXPECTED_FOLDS:
        raise ValueError(f'cv_fold 가 1~5 가 아닙니다: {folds}')

    leaked = config.EXCLUDED_FEATURES & set(feats)
    if leaked:
        raise ValueError(f'FR-004b 로 배제된 변수가 입력에 있습니다: {sorted(leaked)}')
```

- [ ] **Step 4: 통과 확인**

Run: `PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests/test_integrity.py -q`
Expected: `4 passed`

- [ ] **Step 5: 커밋**

```bash
git add ml/cb_burden/data/integrity.py ml/tests/test_integrity.py
git -c user.name="오현근" commit -m "feat(ml): 스냅샷 무결성 검증을 예외로 바꾼다"
```

---

## Task A4: 아티팩트 스키마와 검증기

**Files:**
- Create: `ml/cb_burden/artifacts/__init__.py`, `ml/cb_burden/artifacts/validate.py`, `ml/tests/test_artifacts_validate.py`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`ml/tests/test_artifacts_validate.py`
```python
"""아티팩트 검증 — 배포 전 마지막 관문. 백엔드 기동 검사와 같은 규칙을 갖는다."""
import copy
import pytest
from cb_burden.artifacts import validate


def _bundle():
    return {
        'model': {
            'model_version': 'v1.0.0', 'question_set_version': 'qs-v1.0.0',
            'family': 'logit', 'features': ['a', 'b'], 'classes': [1, 2, 3, 4, 5],
            'decision_weights': [1.1, 1.1, 1.0, 1.0, 1.0], 'missing_sentinel': -1,
            'categories': [[-1, 1], [1, 2]], 'spans': [[0, 2], [2, 2]],
            'coef': [[0.0] * 4 for _ in range(5)], 'intercept': [0.0] * 5,
            'expected_contrib': [[0.0] * 5 for _ in range(2)],
        },
        'selection': {'model_version': 'v1.0.0', 'selected': ['a', 'b']},
        'uncertainty': {'model_version': 'v1.0.0', 'tau_conf': 0.32,
                        'tau_dens': -2.43, 'freq_table': {'a': {'1': 0.5}}},
        'questions': {'question_set_version': 'qs-v1.0.0',
                      'questions': [{'feature': 'a'}, {'feature': 'b'}]},
        'contribution': {'min_threshold': 0.13},
    }


def test_정상_아티팩트는_통과한다():
    validate.check(_bundle())


def test_features_순서가_선별결과와_다르면_거부한다():
    b = _bundle()
    b['selection']['selected'] = ['b', 'a']
    with pytest.raises(ValueError, match='selection'):
        validate.check(b)


def test_문항_순서가_모델과_다르면_거부한다():
    b = _bundle()
    b['questions']['questions'] = [{'feature': 'b'}, {'feature': 'a'}]
    with pytest.raises(ValueError, match='questions'):
        validate.check(b)


def test_척도가_뒤집히면_거부한다():
    # 이 프로젝트에서 가장 실수하기 쉬운 지점이다
    b = _bundle()
    b['model']['classes'] = [5, 4, 3, 2, 1]
    with pytest.raises(ValueError, match='척도'):
        validate.check(b)


def test_확신도_임계값이_범위_밖이면_거부한다():
    b = _bundle()
    b['uncertainty']['tau_conf'] = 1.5
    with pytest.raises(ValueError, match='tau_conf'):
        validate.check(b)


def test_희소성_임계값이_양수면_거부한다():
    b = _bundle()
    b['uncertainty']['tau_dens'] = 0.5
    with pytest.raises(ValueError, match='tau_dens'):
        validate.check(b)


def test_필수_키가_없으면_거부한다():
    b = _bundle()
    del b['model']['decision_weights']
    with pytest.raises(ValueError, match='decision_weights'):
        validate.check(b)
```

- [ ] **Step 2: 실패 확인**

Run: `PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests/test_artifacts_validate.py -q`
Expected: FAIL — `No module named 'cb_burden.artifacts'`

- [ ] **Step 3: 구현**

`ml/cb_burden/artifacts/__init__.py` — 빈 파일

`ml/cb_burden/artifacts/validate.py`
```python
"""산출물 검증.

백엔드 modelLoader 가 기동 때 하던 정합 검사(①features 순서 ②문항 순서)를 그대로 갖고,
스키마·척도 방향·임계값 범위를 더한다. 어긋나면 승격하지 않는다.
"""
from cb_burden import config

REQUIRED = {
    'model': ['model_version', 'question_set_version', 'family', 'features', 'classes',
              'decision_weights', 'missing_sentinel'],
    'selection': ['model_version', 'selected'],
    'uncertainty': ['model_version', 'tau_conf', 'tau_dens', 'freq_table'],
    'questions': ['question_set_version', 'questions'],
    'contribution': ['min_threshold'],
}


def check(bundle):
    for name, keys in REQUIRED.items():
        if name not in bundle:
            raise ValueError(f'{name} 아티팩트가 없습니다')
        for k in keys:
            if k not in bundle[name]:
                raise ValueError(f'{name} 에 필수 키 {k} 가 없습니다')

    model, sel = bundle['model'], bundle['selection']
    q, unc = bundle['questions'], bundle['uncertainty']

    # ① 모델 features 순서 = 선별 결과 (백엔드 기동 검사와 동일)
    if list(model['features']) != list(sel['selected']):
        raise ValueError(
            f'model.features 가 selection.selected 와 다릅니다\n'
            f'  model  {model["features"]}\n  select {sel["selected"]}')

    # ② 문항 순서 = 모델 (백엔드 기동 검사와 동일)
    qf = [x['feature'] for x in q['questions']]
    if qf != list(model['features']):
        raise ValueError(f'questions 의 feature 순서가 모델과 다릅니다\n'
                         f'  model     {model["features"]}\n  questions {qf}')

    # ③ 척도 방향 — 1 이 최고부담인 역방향. 뒤집히면 이용자가 정반대로 이해한다.
    if list(model['classes']) != config.CLASSES:
        raise ValueError(f'척도가 {config.CLASSES} 가 아닙니다: {model["classes"]}')

    # ④ 임계값 범위
    if not 0.0 < float(unc['tau_conf']) < 1.0:
        raise ValueError(f'tau_conf 가 (0,1) 밖입니다: {unc["tau_conf"]}')
    if not float(unc['tau_dens']) < 0.0:
        raise ValueError(f'tau_dens 는 로그 평균이라 음수여야 합니다: {unc["tau_dens"]}')

    # ⑤ 계열과 가중치 길이
    if model['family'] not in ('logit', 'rf', 'et'):
        raise ValueError(f'지원하지 않는 계열입니다: {model["family"]}')
    if len(model['decision_weights']) != len(config.CLASSES):
        raise ValueError('decision_weights 길이가 클래스 수와 다릅니다')
    return True
```

- [ ] **Step 4: 통과 확인**

Run: `PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests/test_artifacts_validate.py -q`
Expected: `7 passed`

- [ ] **Step 5: 실제 배포본으로 확인**

Run:
```bash
PYTHONPATH=ml/.pylibs:ml python3 -c "
import json
from pathlib import Path
from cb_burden.artifacts import validate
m = Path('models')
b = {k: json.loads((m / f'{f}_v1.json').read_text(encoding='utf-8'))
     for k, f in [('model','model'),('selection','selection'),('uncertainty','uncertainty'),
                  ('questions','questions'),('contribution','contribution')]}
validate.check(b); print('v1.0.0 통과')
"
```
Expected: `v1.0.0 통과`

- [ ] **Step 6: 커밋**

```bash
git add ml/cb_burden/artifacts ml/tests/test_artifacts_validate.py
git -c user.name="오현근" commit -m "feat(ml): 아티팩트 검증기 — 스키마·정합·척도 방향"
```

---

## Task A5: run manifest

**Files:**
- Create: `ml/cb_burden/artifacts/manifest.py`, `ml/tests/test_manifest.py`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`ml/tests/test_manifest.py`
```python
"""run manifest — 어떤 데이터에 어떤 코드로 무엇을 만들었는지 남긴다."""
import json
from cb_burden.artifacts import manifest


def test_실행_정보가_모두_담긴다(tmp_path):
    run = manifest.start(run_dir=tmp_path, snapshot_meta={'sha256': 'abc', 'rows': 3000},
                         snapshot_path='data/snapshots/x.csv.gz',
                         model_version='v1.0.1', question_set_version='qs-v1.0.1')
    run['stages'].append({'name': 'baseline', 'duration_s': 1.0, 'metrics': {}})
    manifest.finish(run, tmp_path)

    got = json.loads((tmp_path / 'run.json').read_text(encoding='utf-8'))
    assert got['snapshot']['sha256'] == 'abc'
    assert got['model_version'] == 'v1.0.1'
    assert got['seed'] == 42
    assert 'python' in got['versions'] and 'sklearn' in got['versions']
    assert 'sha' in got['git']
    assert got['stages'][0]['name'] == 'baseline'
    assert got['finished_at']


def test_산출물_해시가_기록된다(tmp_path):
    (tmp_path / 'model_v1.json').write_text('{}', encoding='utf-8')
    run = manifest.start(run_dir=tmp_path, snapshot_meta={'sha256': 'abc', 'rows': 1},
                         snapshot_path='x', model_version='v1', question_set_version='q')
    manifest.finish(run, tmp_path)
    got = json.loads((tmp_path / 'run.json').read_text(encoding='utf-8'))
    assert got['artifacts']['model_v1.json'].startswith('sha256:')
```

- [ ] **Step 2: 실패 확인**

Run: `PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests/test_manifest.py -q`
Expected: FAIL — `No module named 'cb_burden.artifacts.manifest'`

- [ ] **Step 3: 구현**

`ml/cb_burden/artifacts/manifest.py`
```python
"""실행 기록.

"이 모델은 어떻게 만들어졌나"에 답하는 파일이다. 스냅샷 해시·git 커밋·라이브러리 버전이
없으면 몇 주 뒤에 같은 모델을 다시 만들 수 없다.
"""
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone, timedelta
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
                     'sha256': snapshot_meta.get('sha256'),
                     'rows': snapshot_meta.get('rows')},
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
```

- [ ] **Step 4: 통과 확인**

Run: `PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests/test_manifest.py -q`
Expected: `2 passed`

- [ ] **Step 5: 커밋**

```bash
git add ml/cb_burden/artifacts/manifest.py ml/tests/test_manifest.py
git -c user.name="오현근" commit -m "feat(ml): run manifest — 데이터·코드·버전을 실행마다 남긴다"
```

---

## Task A6: 승격 규칙

**Files:**
- Create: `ml/cb_burden/artifacts/release.py`, `ml/tests/test_promote_rules.py`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`ml/tests/test_promote_rules.py`
```python
"""승격 — 배포본을 바꾸는 유일한 경로. 하나라도 어긋나면 아무것도 바꾸지 않는다."""
import json
import pytest
from cb_burden.artifacts import release


def _run(tmp_path, sc=None, golden=True):
    d = tmp_path / 'runs' / 'r1'
    d.mkdir(parents=True)
    (d / 'model_v1.json').write_text('{}', encoding='utf-8')
    if golden:
        (d / 'golden_v1.json').write_text('{}', encoding='utf-8')
    (d / 'run.json').write_text(json.dumps({
        'success_criteria': sc if sc is not None else {'SC-004': True, 'SC-005': True,
                                                       'SC-016': True}}), encoding='utf-8')
    return d


def test_정상이면_릴리스와_current_가_만들어진다(tmp_path):
    d = _run(tmp_path)
    release.promote(d, tmp_path, 'v1.0.1', validator=lambda _: True)
    assert (tmp_path / 'v1.0.1' / 'model_v1.json').exists()
    cur = json.loads((tmp_path / 'current.json').read_text(encoding='utf-8'))
    assert cur['release'] == 'v1.0.1'


def test_골든이_없으면_거부한다(tmp_path):
    d = _run(tmp_path, golden=False)
    with pytest.raises(ValueError, match='golden'):
        release.promote(d, tmp_path, 'v1.0.1', validator=lambda _: True)
    assert not (tmp_path / 'v1.0.1').exists()


def test_성공기준_미달이면_거부한다(tmp_path):
    d = _run(tmp_path, sc={'SC-004': True, 'SC-005': False, 'SC-016': True})
    with pytest.raises(ValueError, match='SC-005'):
        release.promote(d, tmp_path, 'v1.0.1', validator=lambda _: True)
    assert not (tmp_path / 'v1.0.1').exists()


def test_이미_있는_릴리스는_거부한다(tmp_path):
    d = _run(tmp_path)
    (tmp_path / 'v1.0.1').mkdir()
    with pytest.raises(ValueError, match='이미'):
        release.promote(d, tmp_path, 'v1.0.1', validator=lambda _: True)


def test_검증_실패면_아무것도_바꾸지_않는다(tmp_path):
    d = _run(tmp_path)
    def bad(_):
        raise ValueError('스키마 오류')
    with pytest.raises(ValueError, match='스키마'):
        release.promote(d, tmp_path, 'v1.0.1', validator=bad)
    assert not (tmp_path / 'v1.0.1').exists()
    assert not (tmp_path / 'current.json').exists()
```

- [ ] **Step 2: 실패 확인**

Run: `PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests/test_promote_rules.py -q`
Expected: FAIL — `No module named 'cb_burden.artifacts.release'`

- [ ] **Step 3: 구현**

`ml/cb_burden/artifacts/release.py`
```python
"""릴리스 승격.

학습은 models/runs/<run_id>/ 에만 쓴다. 배포본을 바꾸는 것은 이 함수뿐이고,
검증을 통과하지 못하면 **아무 파일도 건드리지 않는다**.
"""
import json
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

KST = timezone(timedelta(hours=9))
REQUIRED_FILES = ['model_v1.json', 'golden_v1.json']


def promote(run_dir, models_dir, release_name, validator):
    run_dir, models_dir = Path(run_dir), Path(models_dir)
    target = models_dir / release_name

    if target.exists():
        raise ValueError(f'릴리스가 이미 있습니다: {target}. 릴리스는 불변입니다')

    for name in REQUIRED_FILES:
        if not (run_dir / name).exists():
            raise ValueError(f'{name} 이 없어 승격할 수 없습니다 ({run_dir})')

    run = json.loads((run_dir / 'run.json').read_text(encoding='utf-8'))
    failed = [k for k, v in run.get('success_criteria', {}).items() if not v]
    if failed:
        raise ValueError(f'성공 기준 미달로 승격할 수 없습니다: {", ".join(failed)}')

    validator(run_dir)          # 스키마·정합 검증. 실패하면 예외가 올라온다

    # 여기까지 통과해야 파일을 만든다
    shutil.copytree(run_dir, target)
    (models_dir / 'current.json').write_text(json.dumps({
        'release': release_name,
        'run_id': run.get('run_id'),
        'promoted_at': datetime.now(KST).isoformat(timespec='seconds'),
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    return target
```

- [ ] **Step 4: 통과 확인**

Run: `PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests/test_promote_rules.py -q`
Expected: `5 passed`

- [ ] **Step 5: 커밋**

```bash
git add ml/cb_burden/artifacts/release.py ml/tests/test_promote_rules.py
git -c user.name="오현근" commit -m "feat(ml): 승격 규칙 — 검증을 통과해야 배포본이 바뀐다"
```

---

## Task A7: 학습 단계 이관

**Files:**
- Create: `ml/cb_burden/stages/__init__.py`, `ml/cb_burden/stages/{baseline,select,calibrate,export,evaluate}.py`, `ml/cb_burden/explain/saabas.py`, `ml/tests/test_stages_smoke.py`, `ml/tests/fixtures/make_fixture.py`
- Read: `ml/train.py` (원본), `ml/saabas.py`

- [ ] **Step 1: 합성 픽스처 생성기를 쓴다**

`ml/tests/fixtures/make_fixture.py`
```python
"""테스트용 합성 스냅샷 300행. 실제 데이터가 아니다(원칙 III).

분포만 흉내 낸다. 이 파일로 만든 결과는 성능 판단에 쓰지 않는다.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from cb_burden.data import snapshot                      # noqa: E402

N, K = 300, 38
rng = np.random.RandomState(0)
features = [f'f{i}' for i in range(K)]
rows = []
for i in range(N):
    r = {'split': 'train' if i < 240 else 'test',
         'cv_fold': (i % 5) + 1 if i < 240 else 0,
         'care_burden': int(rng.choice([1, 2, 3, 4, 5], p=[.15, .39, .30, .13, .03]))}
    for j, f in enumerate(features):
        r[f] = float(rng.choice([-1, 1, 2, 3, 4, 5]))
    rows.append(r)

out = Path(__file__).parent / 'mini_snapshot.csv.gz'
snapshot.write(out, features, rows, source_view='synthetic')
print(f'생성 {out}')
```

Run: `PYTHONPATH=ml/.pylibs:ml python3 ml/tests/fixtures/make_fixture.py`
Expected: `생성 .../mini_snapshot.csv.gz`

- [ ] **Step 2: 실패하는 스모크 테스트를 쓴다**

`ml/tests/test_stages_smoke.py`
```python
"""단계 스모크 — 합성 300행으로 baseline→select→calibrate→export 가 끝까지 도는가.

성능을 보지 않는다. **끝까지 돌고 규약을 지킨 산출물이 나오는지**만 본다.
"""
import json
from pathlib import Path

from cb_burden.artifacts import validate
from cb_burden.data import snapshot
from cb_burden.stages import baseline, calibrate, export, select

FIX = Path(__file__).parent / 'fixtures' / 'mini_snapshot.csv.gz'


def test_전체_단계가_돌고_검증을_통과하는_산출물이_나온다(tmp_path):
    snap = snapshot.read(FIX)
    base = baseline.run(snap)
    assert base['family'] in ('logit', 'rf', 'et')

    sel = select.run(snap, base, max_drop=30)
    assert 1 <= len(sel['selected']) <= len(snap['features'])
    assert len(sel['weights']) == 5

    cal = calibrate.run(snap, sel)
    assert 0.0 < cal['tau_conf'] < 1.0
    assert cal['tau_dens'] < 0.0

    export.run(snap, base, sel, cal, out_dir=tmp_path,
               model_version='vtest', question_set_version='qs-test')

    names = {p.name for p in tmp_path.iterdir()}
    assert {'model_v1.json', 'selection_v1.json', 'uncertainty_v1.json',
            'questions_v1.json', 'contribution_v1.json', 'model_v1.joblib'} <= names

    b = {k: json.loads((tmp_path / f'{f}_v1.json').read_text(encoding='utf-8'))
         for k, f in [('model', 'model'), ('selection', 'selection'),
                      ('uncertainty', 'uncertainty'), ('questions', 'questions'),
                      ('contribution', 'contribution')]}
    validate.check(b)
```

- [ ] **Step 3: 실패 확인**

Run: `PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests/test_stages_smoke.py -q`
Expected: FAIL — `No module named 'cb_burden.stages'`

- [ ] **Step 4: `ml/train.py` 의 단계를 옮긴다**

원본 함수를 그대로 옮기되 **모듈 전역 상수 대신 인자로 받게** 바꾼다. 각 모듈의 공개 함수는
`run(...)` 하나이고 값만 돌려준다. 파일을 쓰는 것은 `export.run` 뿐이다.

| 새 파일 | 원본 위치 | 공개 함수 |
|---|---|---|
| `stages/baseline.py` | `train.py` 의 `stage_baseline` | `run(snap) -> {'family','results'}` |
| `stages/select.py` | `stage_select` | `run(snap, base, max_drop) -> {'selected','weights','history','dropped_order','stop_rule'}` |
| `stages/calibrate.py` | `stage_calibrate` | `run(snap, sel) -> {'tau_conf','tau_dens','rate','err_undecidable','err_decided','freq_table','cv'}` |
| `stages/export.py` | `stage_export` | `run(snap, base, sel, cal, out_dir, model_version, question_set_version) -> None` |
| `stages/evaluate.py` | `stage_evaluate` | `run(snap, payload, unc, sel) -> {'macro_f1','high_burden_recall','undecidable_rate','verdict'}` |
| `explain/saabas.py` | `ml/saabas.py` 전체 | `predict_proba`, `contributions` |

`export.run` 은 기존 JSON 6종에 더해 **joblib 을 쓴다**(이미 `train.py` 에 추가돼 있는
코드를 그대로 옮긴다). `evaluate.run` 은 **DB 를 건드리지 않는다** — 기록은 Task A8 의
`record` 가 맡는다.

- [ ] **Step 5: 통과 확인**

Run: `PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests/test_stages_smoke.py -q`
Expected: `1 passed`

- [ ] **Step 6: 커밋**

```bash
git add ml/cb_burden/stages ml/cb_burden/explain ml/tests/test_stages_smoke.py ml/tests/fixtures
git -c user.name="오현근" commit -m "feat(ml): 학습 단계를 모듈로 분리하고 스모크 테스트를 붙인다"
```

---

## Task A8: DB 기록 가드

**Files:**
- Create: `ml/cb_burden/data/record.py`, `ml/tests/test_record_guard.py`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`ml/tests/test_record_guard.py`
```python
"""DB 기록 — 2026-09-01 에 v1.0.0 성능 기록이 14문항 결과로 덮인 사고를 막는다."""
import pytest
from cb_burden.data import record


class FakeCursor:
    def __init__(self, existing): self.existing, self.calls = existing, []
    def execute(self, sql, args=None): self.calls.append((sql, args))
    def fetchone(self): return (1,) if self.existing else (0,)


class FakeConn:
    def __init__(self, existing=False): self.cur = FakeCursor(existing)
    def cursor(self): return self.cur
    def commit(self): pass
    def close(self): pass


def test_모델_버전이_없으면_거부한다():
    with pytest.raises(ValueError, match='model_version'):
        record.write(FakeConn(), model_version='', family='logit', qset='q',
                     f1=0.3, rec=0.8, und=0.02, notes='{}')


def test_이미_있는_행은_force_없이_거부한다():
    with pytest.raises(ValueError, match='이미'):
        record.write(FakeConn(existing=True), model_version='v1.0.0', family='logit',
                     qset='q', f1=0.3, rec=0.8, und=0.02, notes='{}')


def test_force_면_덮어쓴다():
    c = FakeConn(existing=True)
    record.write(c, model_version='v1.0.0', family='logit', qset='q',
                 f1=0.3, rec=0.8, und=0.02, notes='{}', force=True)
    assert any('INSERT' in sql for sql, _ in c.cur.calls)


def test_새_행은_그냥_기록된다():
    c = FakeConn(existing=False)
    record.write(c, model_version='v1.0.1', family='logit', qset='q',
                 f1=0.3, rec=0.8, und=0.02, notes='{}')
    assert any('INSERT' in sql for sql, _ in c.cur.calls)
```

- [ ] **Step 2: 실패 확인**

Run: `PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests/test_record_guard.py -q`
Expected: FAIL — `No module named 'cb_burden.data.record'`

- [ ] **Step 3: 구현**

`ml/cb_burden/data/record.py`
```python
"""성능 기록을 cb_model_version_v1 에 남긴다.

2026-09-01 에 MODEL_VERSION 을 주지 않아 v1.0.0 행이 14문항 평가 결과로 덮였다.
그래서 model_version 은 필수이고, 기존 행이 있으면 force 없이 덮지 않는다.
"""

INSERT = """INSERT INTO cb_model_version_v1
  (model_version, family, question_set_version, macro_f1, high_burden_recall,
   undecidable_rate, activated_at, deactivated_at, notes)
  VALUES (%s,%s,%s,%s,%s,%s,NOW(),NULL,%s)
  ON DUPLICATE KEY UPDATE family=VALUES(family), macro_f1=VALUES(macro_f1),
    high_burden_recall=VALUES(high_burden_recall),
    undecidable_rate=VALUES(undecidable_rate),
    activated_at=NOW(), deactivated_at=NULL, notes=VALUES(notes)"""


def write(conn, model_version, family, qset, f1, rec, und, notes, force=False):
    if not model_version:
        raise ValueError('model_version 은 필수입니다. 생략하면 다른 버전의 기록을 덮어씁니다')

    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM cb_model_version_v1 WHERE model_version = %s',
                (model_version,))
    if cur.fetchone()[0] and not force:
        raise ValueError(
            f'{model_version} 기록이 이미 있습니다. 덮어쓰려면 --force 를 주세요')

    cur.execute('UPDATE cb_model_version_v1 SET deactivated_at = NOW() '
                'WHERE deactivated_at IS NULL')
    cur.execute(INSERT, (model_version, family, qset, round(f1, 4), round(rec, 4),
                         round(und, 4), notes))
    conn.commit()
```

- [ ] **Step 4: 통과 확인**

Run: `PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests/test_record_guard.py -q`
Expected: `4 passed`

- [ ] **Step 5: 커밋**

```bash
git add ml/cb_burden/data/record.py ml/tests/test_record_guard.py
git -c user.name="오현근" commit -m "feat(ml): DB 기록에 model_version 필수·중복 거부 가드"
```

---

## Task A9: 골든 케이스 생성

**Files:**
- Create: `ml/cb_burden/artifacts/golden.py`, `ml/tests/test_golden_build.py`
- Read: `ml/parity.py` (원본)

`promote` 가 `golden_v1.json` 을 요구하는데 만드는 곳이 없었다. `ml/parity.py` 가 하던 일을
함수로 옮긴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`ml/tests/test_golden_build.py`
```python
"""골든 케이스 — 재학습 뒤에도 같은 답을 내는지 확인할 기준값을 만든다."""
import json
from pathlib import Path

import numpy as np
from cb_burden.artifacts import golden
from cb_burden.data import snapshot

FIX = Path(__file__).parent / 'fixtures' / 'mini_snapshot.csv.gz'


def test_모든_행의_확률이_기록된다(tmp_path, monkeypatch):
    snap = snapshot.read(FIX)
    payload = {'model_version': 'vtest', 'features': snap['features'][:2],
               'family': 'logit', 'classes': [1, 2, 3, 4, 5]}

    def fake_proba(_payload, row):
        return [0.2, 0.2, 0.2, 0.2, 0.2]

    monkeypatch.setattr(golden, 'predict_proba', fake_proba)
    out = golden.build(payload, snap, tmp_path)

    got = json.loads((tmp_path / 'golden_v1.json').read_text(encoding='utf-8'))
    assert got['model_version'] == 'vtest'
    assert got['n'] == len(snap['y'])
    assert len(got['cases']) == len(snap['y'])
    assert len(got['cases'][0]['proba']) == 5
    assert len(got['cases'][0]['input']) == 2
    assert out.name == 'golden_v1.json'
```

- [ ] **Step 2: 실패 확인**

Run: `PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests/test_golden_build.py -q`
Expected: FAIL — `No module named 'cb_burden.artifacts.golden'`

- [ ] **Step 3: 구현**

`ml/cb_burden/artifacts/golden.py`
```python
"""골든 케이스 생성.

TS 이식본이 사라지면 "패리티(두 구현 대조)"라는 이름이 뜻을 잃는다. 같은 파일 형식을
`golden_v1.json` 으로 만들어, **재학습·리팩터링 뒤에도 같은 답을 내는지** 확인하는 데 쓴다.
"""
import json
from pathlib import Path

from cb_burden.explain.saabas import predict_proba


def build(payload, snap, out_dir):
    idx = {f: i for i, f in enumerate(snap['features'])}
    cols = [idx[f] for f in payload['features']]
    cases = []
    for row in snap['X'][:, cols]:
        r = [float(v) for v in row]
        cases.append({'input': r, 'proba': list(predict_proba(payload, r))})

    out = Path(out_dir) / 'golden_v1.json'
    out.write_text(json.dumps({
        'model_version': payload['model_version'],
        'features': payload['features'],
        'n': len(cases),
        'cases': cases,
    }), encoding='utf-8')
    return out
```

- [ ] **Step 4: 통과 확인**

Run: `PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests/test_golden_build.py -q`
Expected: `1 passed`

- [ ] **Step 5: 커밋**

```bash
git add ml/cb_burden/artifacts/golden.py ml/tests/test_golden_build.py
git -c user.name="오현근" commit -m "feat(ml): 골든 케이스 생성 — parity.py 를 함수로 옮긴다"
```

---

## Task A10: CLI 조립과 이관 검증

**Files:**
- Create: `ml/cb_burden/cli.py`, `ml/cb_burden/__main__.py`
- Modify: `ml/README.md`

- [ ] **Step 1: CLI 를 쓴다**

`ml/cb_burden/__main__.py`
```python
from cb_burden.cli import main
main()
```

`ml/cb_burden/cli.py` — `argparse` 로 하위 명령을 만든다.

| 명령 | 인자 | 하는 일 |
|---|---|---|
| `snapshot` | `--out` | DB 에서 읽어 스냅샷과 메타를 만든다 |
| `train` | `--snapshot` `--model-version` `--question-set-version` `[--stage]` | `models/runs/<run_id>/` 에 산출물과 `run.json` |
| `evaluate` | `<run_dir>` `[--force]` | test 602건 평가. `run.json` 의 `success_criteria` 갱신 |
| `golden` | `<run_dir>` | `artifacts.golden.build` 로 `golden_v1.json` 생성 |
| `verify` | `<run_dir 또는 release>` | `artifacts.validate.check` |
| `promote` | `<run_dir>` `--as` | `artifacts.release.promote` |
| `record` | `--release` `--model-version` `[--force]` | `data.record.write` |

`run_id` 는 `datetime.now(KST).strftime('%Y-%m-%dT%H-%M') + '_' + git_sha[:6]`.

- [ ] **Step 2: 도움말이 뜨는지 확인**

Run: `PYTHONPATH=ml/.pylibs:ml python3 -m cb_burden --help`
Expected: 7개 하위 명령이 보인다

- [ ] **Step 3: 스냅샷을 만든다**

Run:
```bash
PYTHONPATH=ml/.pylibs:ml python3 -m cb_burden snapshot \
  --out data/snapshots/cb_dataset_2026-09-01.csv.gz
```
Expected: `rows 3000 · features 38 · sha256 …`

- [ ] **Step 4: 이관 합격 기준을 확인한다**

Run:
```bash
PYTHONPATH=ml/.pylibs:ml python3 -m cb_burden train \
  --snapshot data/snapshots/cb_dataset_2026-09-01.csv.gz \
  --model-version v1.0.0 --question-set-version qs-v1.0.0
```

그다음 새 산출물과 현재 배포본을 대조한다.

```bash
PYTHONPATH=ml/.pylibs:ml python3 -c "
import json, sys, glob
from pathlib import Path
run = sorted(glob.glob('models/runs/*'))[-1]
a = json.loads(Path(run, 'model_v1.json').read_text(encoding='utf-8'))
b = json.loads(Path('models/v1.0.0/model_v1.json').read_text(encoding='utf-8'))
assert a['features'] == b['features'], 'features 순서가 다르다'
import numpy as np
d = np.abs(np.array(a['coef']) - np.array(b['coef'])).max()
print(f'계수 최대 오차 {d:.3e}')
ua = json.loads(Path(run, 'uncertainty_v1.json').read_text(encoding='utf-8'))
ub = json.loads(Path('models/v1.0.0/uncertainty_v1.json').read_text(encoding='utf-8'))
print(f'tau_conf 차이 {abs(ua[\"tau_conf\"]-ub[\"tau_conf\"]):.3e}')
print(f'tau_dens 차이 {abs(ua[\"tau_dens\"]-ub[\"tau_dens\"]):.3e}')
"
```
Expected: 세 값 모두 `1e-09` 미만.
**어긋나면 진행하지 말고 원인을 문서로 남긴다.** 라이브러리 버전 차이일 수 있다.

- [ ] **Step 5: 전체 테스트**

Run: `PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests -q`
Expected: 전부 통과

- [ ] **Step 6: README 갱신**

`ml/README.md` 의 실행 예시를 새 CLI 로 바꾸고, **`train.py` 는 이관 중이라 남겨 둔다**고
적는다.

- [ ] **Step 7: 커밋**

```bash
git add ml/cb_burden/cli.py ml/cb_burden/__main__.py ml/README.md data/snapshots
git -c user.name="오현근" commit -m "feat(ml): cb_burden CLI 와 스냅샷 고정"
```

---

# Phase B — 추론 서비스

> Phase A 가 끝나고 합격 기준을 통과한 뒤에 시작한다. **서비스에 영향이 있다.**

## Task B1: 추론 엔진

**Files:**
- Create: `ml/cb_burden/serve/__init__.py`, `ml/cb_burden/serve/engine.py`, `ml/tests/test_engine_golden.py`

- [ ] **Step 1: 실패하는 골든 테스트를 쓴다**

`ml/tests/test_engine_golden.py`
```python
"""추론 엔진 — 배포본과 같은 답을 내는가. parity 테스트가 하던 역할을 잇는다."""
import json
from pathlib import Path

import numpy as np
import pytest
from cb_burden.serve import engine

RELEASE = Path('models')
# 승격된 릴리스는 golden_v1.json 을 갖는다. 현재 배포본(v1.0.0)은 이관 전에 만들어져
# parity_v1.json 만 있으므로 둘 다 받는다. Phase A 재학습 후에는 golden_v1.json 만 남는다.
GOLDEN = (RELEASE / 'golden_v1.json') if (RELEASE / 'golden_v1.json').exists() \
    else (RELEASE / 'parity_v1.json')


@pytest.fixture(scope='module')
def eng():
    return engine.Engine.load(RELEASE)


def test_확률이_골든과_1e_9_이내로_같다(eng):
    fx = json.loads(GOLDEN.read_text(encoding='utf-8'))
    worst = 0.0
    for c in fx['cases']:
        p = eng.proba(c['input'])
        worst = max(worst, float(np.abs(np.array(p) - np.array(c['proba'])).max()))
    assert worst < 1e-9, f'최대 오차 {worst:.3e}'


def test_판정_불가는_정책값을_따른다(eng):
    row = [4, 4, 5, 1, -1, 3, 1]                      # 배포본 기준 판정 성립 사례
    loose = eng.decide(row, tau_conf=0.0, tau_dens=-99.0,
                       decision_weights=[1.1, 1.1, 1, 1, 1], contrib_threshold=0.13)
    assert loose['decided'] is True

    strict = eng.decide(row, tau_conf=0.9, tau_dens=-99.0,
                        decision_weights=[1.1, 1.1, 1, 1, 1], contrib_threshold=0.13)
    assert strict['decided'] is False
    assert strict['undecidableReason'] == 'ambiguous'


def test_희소성만_걸려도_판정_불가다(eng):
    row = [4, 4, 5, 1, -1, 3, 1]
    got = eng.decide(row, tau_conf=0.0, tau_dens=-1.0,
                     decision_weights=[1.1, 1.1, 1, 1, 1], contrib_threshold=0.13)
    assert got['decided'] is False
    assert got['undecidableReason'] == 'sparse'


def test_판정_불가면_기여요인을_내지_않는다(eng):
    row = [4, 4, 5, 1, -1, 3, 1]
    got = eng.decide(row, tau_conf=0.9, tau_dens=-99.0,
                     decision_weights=[1.1, 1.1, 1, 1, 1], contrib_threshold=0.13)
    assert got['contributions'] is None          # FR-011c
    assert got['internalLabel'] is None          # FR-009a
```

- [ ] **Step 2: 실패 확인**

Run: `PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests/test_engine_golden.py -q`
Expected: FAIL — `No module named 'cb_burden.serve'`

- [ ] **Step 3: 구현**

`ml/cb_burden/serve/__init__.py` — 빈 파일

`ml/cb_burden/serve/engine.py`
```python
"""추론 엔진 — 상태 없는 계산기.

파일은 load 할 때 한 번만 읽고, 그 뒤로는 파일도 DB 도 건드리지 않는다.
판정 임계값과 결정 가중치는 **호출자가 준다**(FR-009c — 설정이 소유한다).
"""
import json
from pathlib import Path

import joblib
import numpy as np

EPS = 1e-4


class Engine:
    def __init__(self, bundle, model_json, uncertainty, questions):
        self.b = bundle
        self.model_json = model_json
        self.unc = uncertainty
        self.questions = questions
        self.features = bundle['features']
        self.classes = list(bundle['classes'])
        self.missing = bundle['missing_sentinel']

    @classmethod
    def load(cls, release_dir):
        d = Path(release_dir)
        bundle = joblib.load(d / 'model_v1.joblib')
        rd = lambda n: json.loads((d / n).read_text(encoding='utf-8'))
        return cls(bundle, rd('model_v1.json'), rd('uncertainty_v1.json'),
                   rd('questions_v1.json'))

    def proba(self, row):
        X = self.b['encoder'].transform(np.array([row], dtype=float))
        return self.b['model'].predict_proba(X)[0].tolist()

    def rarity(self, row):
        table = self.unc['freq_table']
        s = 0.0
        for j, f in enumerate(self.features):
            p = table.get(f, {}).get(str(int(row[j])), EPS)
            s += np.log(max(p, EPS))
        return float(s / len(self.features))

    def decide(self, row, tau_conf, tau_dens, decision_weights, contrib_threshold):
        p = self.proba(row)
        rar = self.rarity(row)
        maxp = float(max(p))

        # 두 조건은 OR. 함께 걸리면 sparse 가 우선한다 — 구체적으로 설명할 수 있는 쪽이다.
        reason = None
        if rar < tau_dens:
            reason = 'sparse'
        elif maxp < tau_conf:
            reason = 'ambiguous'

        out = {'proba': p, 'maxProba': maxp, 'rarity': rar,
               'undecidableReason': reason, 'decided': reason is None,
               'internalLabel': None, 'contributions': None,
               'modelVersion': self.model_json['model_version'],
               'questionSetVersion': self.model_json['question_set_version']}
        if reason is not None:
            return out

        w = np.array(decision_weights, dtype=float)
        idx = int(np.argmax(np.array(p) * w))
        out['internalLabel'] = self.classes[idx]
        out['contributions'] = self._contributions(row, idx, contrib_threshold)
        return out

    def _contributions(self, row, cls_idx, threshold):
        """선형 모델의 기여도 분해. sum(contrib) + base = 점수 가 정확히 성립한다."""
        mj = self.model_json
        cats, spans = mj['categories'], mj['spans']
        coef, expect = mj['coef'], mj['expected_contrib']
        out = []
        for j, f in enumerate(self.features):
            start, _ = spans[j]
            try:
                k = [float(v) for v in cats[j]].index(float(row[j]))
                actual = coef[cls_idx][start + k]
            except ValueError:
                actual = 0.0                      # 미지의 값 → 원-핫 전부 0
            v = actual - expect[j][cls_idx]
            out.append({'feature': f, 'value': row[j], 'contrib': round(v, 6),
                        'isMinor': abs(v) < threshold})
        out.sort(key=lambda x: -abs(x['contrib']))
        return out[:3]
```

- [ ] **Step 4: 통과 확인**

Run: `PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests/test_engine_golden.py -q`
Expected: `4 passed`

- [ ] **Step 5: 커밋**

```bash
git add ml/cb_burden/serve ml/tests/test_engine_golden.py
git -c user.name="오현근" commit -m "feat(ml): 추론 엔진 — 정책은 호출자가 주는 상태 없는 계산기"
```

---

## Task B2: FastAPI 서비스

**Files:**
- Create: `ml/cb_burden/serve/schema.py`, `ml/cb_burden/serve/app.py`, `ml/cb_burden/serve/__main__.py`, `ml/tests/test_serve_api.py`

- [ ] **Step 1: 실패하는 API 테스트를 쓴다**

`ml/tests/test_serve_api.py`
```python
"""추론 서비스 계약 — 잘못된 입력을 경계에서 막는다."""
import pytest
from fastapi.testclient import TestClient
from cb_burden.serve.app import create_app

POLICY = {'tauConf': 0.3239, 'tauDens': -2.4343,
          'decisionWeights': [1.1, 1.1, 1.0, 1.0, 1.0],
          'contributionMinThreshold': 0.1325}


@pytest.fixture(scope='module')
def client():
    return TestClient(create_app('models'))


def _answers():
    vals = [4, 4, 5, 1, None, 3, 1]
    return [{'questionNo': i + 1, 'value': v} for i, v in enumerate(vals)]


def test_health_가_버전을_알려준다(client):
    r = client.get('/health')
    assert r.status_code == 200
    b = r.json()
    assert b['status'] == 'ok'
    assert b['modelVersion'] and b['questionSetVersion']
    assert len(b['artifactDecisionWeights']) == 5


def test_정상_요청은_판정을_돌려준다(client):
    r = client.post('/predict', json={'answers': _answers(), 'policy': POLICY})
    assert r.status_code == 200
    b = r.json()
    assert len(b['proba']) == 5
    assert b['decided'] in (True, False)
    assert b['modelVersion']


def test_policy_가_없으면_거절한다(client):
    # 기본값을 두면 조용히 다른 기준으로 판정하게 된다
    r = client.post('/predict', json={'answers': _answers()})
    assert r.status_code == 422


def test_문항_수가_다르면_거절한다(client):
    r = client.post('/predict', json={'answers': _answers()[:3], 'policy': POLICY})
    assert r.status_code == 422


def test_모르는_문항번호는_거절한다(client):
    a = _answers()
    a[0]['questionNo'] = 99
    r = client.post('/predict', json={'answers': a, 'policy': POLICY})
    assert r.status_code == 422
```

- [ ] **Step 2: 실패 확인**

Run: `PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests/test_serve_api.py -q`
Expected: FAIL — `No module named 'cb_burden.serve.app'`

- [ ] **Step 3: 구현**

`ml/cb_burden/serve/schema.py`
```python
from typing import List, Optional
from pydantic import BaseModel, Field


class Answer(BaseModel):
    questionNo: int
    value: Optional[float] = None          # None = "해당사항 없음" → 결측 센티널


class Policy(BaseModel):
    """판정 정책은 설정(cb_config_v1)이 소유한다. 기본값을 두지 않는다(FR-009c)."""
    tauConf: float = Field(gt=0.0, lt=1.0)
    tauDens: float = Field(lt=0.0)
    decisionWeights: List[float] = Field(min_length=5, max_length=5)
    contributionMinThreshold: float = Field(ge=0.0)


class PredictRequest(BaseModel):
    answers: List[Answer]
    policy: Policy


class Contribution(BaseModel):
    feature: str
    value: float
    contrib: float
    isMinor: bool


class PredictResponse(BaseModel):
    modelVersion: str
    questionSetVersion: str
    proba: List[float]
    decided: bool
    internalLabel: Optional[int]
    maxProba: float
    rarity: float
    undecidableReason: Optional[str]
    contributions: Optional[List[Contribution]]
```

`ml/cb_burden/serve/app.py`
```python
"""추론 서비스.

개인정보를 받지 않는다. 문항 응답과 정책 값만 받고, 요청 본문을 로그에 남기지 않는다
(원칙 III).
"""
import os

from fastapi import FastAPI, HTTPException
from cb_burden.serve.engine import Engine
from cb_burden.serve.schema import PredictRequest, PredictResponse


def create_app(release_dir=None):
    release = release_dir or os.getenv('CB_MODELS_DIR', 'models')
    engine = Engine.load(release)              # 로드 실패하면 뜨지 않는다
    qnos = [q['questionNo'] for q in engine.questions['questions']]
    app = FastAPI(title='cb-burden inference', version=engine.model_json['model_version'])

    @app.get('/health')
    def health():
        # decisionWeights 를 함께 낸다 — 설정(cb_config_v1)과 아티팩트가 갈라지면
        # 조용히 다른 기준으로 판정하게 된다. 2026-09-01 임계값 사고와 같은 유형이다.
        return {'status': 'ok', 'release': str(release),
                'modelVersion': engine.model_json['model_version'],
                'questionSetVersion': engine.model_json['question_set_version'],
                'artifactDecisionWeights': engine.model_json['decision_weights']}

    @app.post('/predict', response_model=PredictResponse)
    def predict(req: PredictRequest):
        by_no = {a.questionNo: a.value for a in req.answers}
        if sorted(by_no) != sorted(qnos):
            raise HTTPException(422, f'문항 번호가 모델과 다릅니다. 기대 {qnos}')
        row = [engine.missing if by_no[n] is None else float(by_no[n]) for n in qnos]
        p = req.policy
        return engine.decide(row, p.tauConf, p.tauDens,
                             p.decisionWeights, p.contributionMinThreshold)

    return app
```

`ml/cb_burden/serve/__main__.py`
```python
import argparse
import uvicorn
from cb_burden.serve.app import create_app

ap = argparse.ArgumentParser(prog='cb_burden.serve')
ap.add_argument('--release', default=None)
ap.add_argument('--socket', default=os.getenv('CB_INFERENCE_SOCKET',
                                             str(ROOT / 'run' / 'cb-inference.sock')))
a = ap.parse_args()
sock = Path(a.socket); sock.parent.mkdir(parents=True, exist_ok=True)
if sock.exists():
    sock.unlink()                    # 이전 프로세스가 남긴 소켓 파일을 치운다
uvicorn.run(create_app(a.release), uds=str(sock), access_log=False)
```

- [ ] **Step 4: 통과 확인**

Run: `PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests/test_serve_api.py -q`
Expected: `5 passed`

- [ ] **Step 5: 실제로 띄워 본다**

Run:
```bash
PYTHONPATH=ml/.pylibs:ml python3 -m cb_burden.serve --release models &
curl -s --unix-socket run/cb-inference.sock http://localhost/health
```
Expected: `{"status":"ok","release":"models","modelVersion":"v1.0.0","questionSetVersion":"qs-v1.0.0"}`

- [ ] **Step 6: 커밋**

```bash
git add ml/cb_burden/serve ml/tests/test_serve_api.py
git -c user.name="오현근" commit -m "feat(ml): FastAPI 추론 서비스 — /predict · /health"
```

---

## Task B3: 백엔드 추론 클라이언트

**Files:**
- Create: `backend/src/services/inferenceClient.ts`, `backend/tests/unit/inferenceClient.test.ts`
- Modify: `backend/src/config/env.ts`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/unit/inferenceClient.test.ts`
```typescript
// 추론 서비스 호출 — 실패해도 진단 흐름이 무너지지 않아야 한다.
//   파이썬이 죽어도 기관 안내는 계속 나가야 하므로, 예외를 던지지 않고
//   'unavailable' 을 돌려준다(설계 4.9.4).
import { describe, it, expect, vi, afterEach } from 'vitest';
import { callInference } from '../../src/services/inferenceClient.js';

const REQ = {
  answers: [{ questionNo: 1, value: 4 }],
  policy: { tauConf: 0.3, tauDens: -2.4, decisionWeights: [1.1, 1.1, 1, 1, 1],
            contributionMinThreshold: 0.13 },
};

afterEach(() => vi.unstubAllGlobals());

describe('추론 서비스 호출', () => {
  it('정상 응답을 그대로 돌려준다', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(
      JSON.stringify({ modelVersion: 'v1.0.0', questionSetVersion: 'qs-v1.0.0',
                       proba: [0.1, 0.2, 0.3, 0.3, 0.1], decided: true, internalLabel: 3,
                       maxProba: 0.3, rarity: -1.1, undecidableReason: null,
                       contributions: [] }),
      { status: 200, headers: { 'content-type': 'application/json' } })));
    const r = await callInference(REQ);
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.value.internalLabel).toBe(3);
  });

  it('5xx 면 unavailable 이다', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('boom', { status: 500 })));
    const r = await callInference(REQ);
    expect(r.ok).toBe(false);
  });

  it('연결 실패면 unavailable 이다', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('ECONNREFUSED'); }));
    const r = await callInference(REQ);
    expect(r.ok).toBe(false);
  });

  it('한 번 재시도한다', async () => {
    const f = vi.fn()
      .mockRejectedValueOnce(new Error('ECONNREFUSED'))
      .mockResolvedValueOnce(new Response(
        JSON.stringify({ modelVersion: 'v', questionSetVersion: 'q',
                         proba: [1, 0, 0, 0, 0], decided: true, internalLabel: 1,
                         maxProba: 1, rarity: -1, undecidableReason: null,
                         contributions: [] }),
        { status: 200, headers: { 'content-type': 'application/json' } }));
    vi.stubGlobal('fetch', f);
    const r = await callInference(REQ);
    expect(r.ok).toBe(true);
    expect(f).toHaveBeenCalledTimes(2);
  });
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && npx vitest run tests/unit/inferenceClient.test.ts`
Expected: FAIL — 모듈을 찾을 수 없음

- [ ] **Step 3: 구현**

`backend/src/config/env.ts` 의 `env` 객체에 추가
```typescript
  inferenceSocket: process.env.CB_INFERENCE_SOCKET || path.join(ROOT, 'run', 'cb-inference.sock'),
  inferenceTimeoutMs: Number(process.env.CB_INFERENCE_TIMEOUT_MS || 2000),
```

`backend/src/services/inferenceClient.ts`
```typescript
// 파이썬 추론 서비스 호출 (설계 4.9)
//   ★ 예외를 던지지 않는다. 실패는 값으로 돌려준다 — 파이썬이 죽어도 기관 안내는
//     계속 나가야 하기 때문이다(FR-021j 안전망과 같은 취지).
import { env } from '../config/env.js';

export interface InferenceRequest {
  answers: { questionNo: number; value: number | null }[];
  policy: {
    tauConf: number; tauDens: number;
    decisionWeights: number[]; contributionMinThreshold: number;
  };
}

export interface InferenceResult {
  modelVersion: string;
  questionSetVersion: string;
  proba: number[];
  decided: boolean;
  internalLabel: number | null;
  maxProba: number;
  rarity: number;
  undecidableReason: 'sparse' | 'ambiguous' | null;
  contributions: { feature: string; value: number; contrib: number; isMinor: boolean }[] | null;
}

export type InferenceOutcome =
  | { ok: true; value: InferenceResult }
  | { ok: false; reason: string };

async function once(req: InferenceRequest): Promise<InferenceResult> {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), env.inferenceTimeoutMs);
  try {
    const res = await fetch(`${env.inferenceUrl}/predict`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(req),
      signal: ctl.signal,
    });
    if (!res.ok) throw new Error(`추론 서비스가 ${res.status} 를 냈습니다`);
    return (await res.json()) as InferenceResult;
  } finally {
    clearTimeout(t);
  }
}

/** 실패해도 던지지 않는다. 호출자가 unavailable 화면을 만든다. */
export async function callInference(req: InferenceRequest): Promise<InferenceOutcome> {
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      return { ok: true, value: await once(req) };
    } catch (e: any) {
      if (attempt === 1) {
        console.error('[inference] 호출 실패:', e?.message ?? e);
        return { ok: false, reason: String(e?.message ?? e) };
      }
    }
  }
  return { ok: false, reason: 'unreachable' };
}

export async function inferenceHealth(): Promise<
  { modelVersion: string; questionSetVersion: string;
    artifactDecisionWeights: number[] } | null> {
  try {
    const res = await fetch(`${env.inferenceUrl}/health`);
    if (!res.ok) return null;
    return (await res.json()) as any;
  } catch {
    return null;
  }
}
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && npx vitest run tests/unit/inferenceClient.test.ts`
Expected: `4 passed`

- [ ] **Step 5: 커밋**

```bash
git add backend/src/services/inferenceClient.ts backend/src/config/env.ts \
        backend/tests/unit/inferenceClient.test.ts
git -c user.name="오현근" commit -m "feat(backend): 추론 서비스 클라이언트 — 실패를 값으로 돌려준다"
```

---

## Task B4: diagnosisService 전환

**Files:**
- Modify: `backend/src/services/diagnosisService.ts`
- Create: `backend/tests/unit/diagnosisUnavailable.test.ts`
- Modify: `db/seeds/config.js`

- [ ] **Step 0: 전환 전 TS ↔ 파이썬 3,000건 대조** (설계 6단계 B2)

바꾸기 전에 **두 경로가 정말 같은 답을 내는지** 확인한다. 이걸 건너뛰면 무엇이 달라졌는지
나중에 알 수 없다. 파이썬 서비스를 띄운 상태에서 실행한다.

```bash
cd backend && npx tsx -e "
import fs from 'node:fs';
import { predictProba, decide, contributions } from './src/inference/predictor.js';
import { rarity } from './src/inference/undecidable.js';
const m = JSON.parse(fs.readFileSync('../models/model_v1.json','utf8'));
const u = JSON.parse(fs.readFileSync('../models/uncertainty_v1.json','utf8'));
const q = JSON.parse(fs.readFileSync('../models/questions_v1.json','utf8'));
const f = JSON.parse(fs.readFileSync('../models/parity_v1.json','utf8'));
const pol = { tauConf: u.tau_conf, tauDens: u.tau_dens,
              decisionWeights: m.decision_weights, contributionMinThreshold: 0.1325 };
let worst = 0, mismatch = 0;
for (const c of f.cases) {
  const answers = (q.questions as any[]).map((qq, j) => ({
    questionNo: qq.questionNo,
    value: c.input[j] === m.missing_sentinel ? null : c.input[j] }));
  const res = await send('POST', '/predict', body);   // 유닉스 소켓 전송층
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ answers, policy: pol }) });
  const py = await res.json();
  const ts = predictProba(m, c.input);
  for (let i = 0; i < 5; i++) worst = Math.max(worst, Math.abs(ts[i] - py.proba[i]));
  const tsRar = rarity(m, u, c.input);
  const tsUnd = Math.max(...ts) < u.tau_conf || tsRar < u.tau_dens;
  if (tsUnd === py.decided) mismatch++;
}
console.log('확률 최대 오차', worst.toExponential(3), '· 판정 불일치', mismatch, '건');
"
```
Expected: `확률 최대 오차 < 1e-9 · 판정 불일치 0 건`
**어긋나면 전환하지 않는다.** 원인을 먼저 밝힌다.

- [ ] **Step 1: 설정에 문구를 추가한다**

`db/seeds/config.js` 의 `CONFIG` 에 추가
```javascript
  // 추론 서비스 장애 시 안내 (설계 4.9.4). 판정 불가와 구분되는 문구여야 한다.
  'notice.inferenceUnavailable': {
    text: '지금은 진단 결과를 드릴 수 없습니다. 잠시 후 다시 시도해 주세요. ' +
          '다만 필요한 지원을 놓치지 않도록 가까운 상담·서비스 기관을 안내합니다.',
    note: '판정 불가가 아니라 일시적 장애다. 부담 수준과 무관하다는 점을 밝힌다',
  },
```

`backend/src/config/configStore.ts` 의 `REQUIRED` 에 `'notice.inferenceUnavailable'` 추가.

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`backend/tests/unit/diagnosisUnavailable.test.ts`
```typescript
// 추론 서비스가 죽었을 때 — 진단은 못 하지만 기관 안내는 나가야 한다 (설계 4.9.4)
import { describe, it, expect, vi } from 'vitest';

vi.mock('../../src/services/inferenceClient.js', () => ({
  callInference: async () => ({ ok: false, reason: 'ECONNREFUSED' }),
}));
vi.mock('../../src/inference/modelLoader.js', () => ({
  getArtifacts: () => ({ questions: { questions: [{ questionNo: 1, feature: 'a' }] },
                         model: { question_set_version: 'qs-v1.0.0' } }),
}));
vi.mock('../../src/config/configStore.js', () => ({
  cfg: (k: string) => ({
    'undecidable.thresholds': { tauConf: 0.3, tauDens: -2.4 },
    'burden.labels': {},
    'notice.disclaimer': { text: '고지' },
    'notice.inferenceUnavailable': { text: '지금은 진단 결과를 드릴 수 없습니다.' },
    'contribution.minThreshold': { value: 0.13 },
    'model.decisionWeights': { weights: [1.1, 1.1, 1, 1, 1] },
  } as any)[k],
}));
vi.mock('../../src/repositories/pool.js', () => ({ query: async () => [] }));
vi.mock('../../src/services/referralService.js', () => ({
  buildReferral: async () => ({ facilities: [{ name: '가까운 센터' }] }),
}));

const { diagnose } = await import('../../src/services/diagnosisService.js');

describe('추론 서비스 장애', () => {
  it('진단은 못 하지만 기관 안내는 나간다', async () => {
    const out = await diagnose({
      answers: [{ questionNo: 1, value: 4 }], careTargetAge: 20,
      multipleCareTargets: false, lat: null, lng: null, regionCode: null,
    });
    expect(out.decided).toBe(false);
    expect(out.unavailable).toBe(true);
    expect(out.unavailableNotice).toContain('진단 결과를 드릴 수 없습니다');
    expect(out.immediateReferral).not.toBeNull();
    expect(out.burdenLabel).toBeNull();
    expect(out.contributions).toBeNull();
  });
});
```

- [ ] **Step 3: 실패 확인**

Run: `cd backend && npx vitest run tests/unit/diagnosisUnavailable.test.ts`
Expected: FAIL — `unavailable` 이 없음

- [ ] **Step 4: `diagnosisService.ts` 를 고친다**

- `DiagnosisOutput` 에 `unavailable: boolean` 과 `unavailableNotice: string | null` 추가
- `modelVersion` 의 타입을 `string` → `string | null` 로 바꾼다 (장애 시 알 수 없다)
- `predictProba`·`decide`·`rarity`·`contributions` 직접 호출을 지우고 `callInference` 로 교체
- 정책 값은 설정에서 읽어 요청에 싣는다

```typescript
  // 정책 값은 모두 설정에서 읽는다. B7 이후 백엔드는 모델 아티팩트를 읽지 않으므로
  // getArtifacts().contributionThreshold 를 쓰면 안 된다.
  const tau = cfg<{ tauConf: number; tauDens: number }>('undecidable.thresholds');
  const weights = cfg<{ weights: number[] }>('model.decisionWeights').weights;
  const minThreshold = cfg<{ value: number }>('contribution.minThreshold').value;
  const outcome = await callInference({
    answers: params.answers,
    policy: { tauConf: tau.tauConf, tauDens: tau.tauDens,
              decisionWeights: weights, contributionMinThreshold: minThreshold },
  });

  if (!outcome.ok) {
    const referral = await buildReferral({
      internalLabel: null, undecidable: true,
      careTargetAge: params.careTargetAge,
      lat: params.lat, lng: params.lng, regionCode: params.regionCode,
    });
    return {
      decided: false, unavailable: true,
      unavailableNotice: cfg<any>('notice.inferenceUnavailable').text,
      internalLabel: null, burdenLabel: null, burdenDescription: null, isWarning: false,
      contributions: null, comparison: null, undecidableNotice: null,
      multipleTargetsNotice: null, immediateReferral: referral,
      modelVersion: null, disclaimer: cfg<any>('notice.disclaimer').text,
    };
  }
```

`model.decisionWeights` 설정 키를 `db/seeds/config.js` 에 추가한다 — 지금은 모델 JSON 이
갖고 있으나, 정책이므로 설정으로 옮긴다.

```javascript
  'model.decisionWeights': {
    weights: MODEL.decision_weights,
    note: '고부담(1·2)에 가산점. 놓치지 않는 쪽으로 기울인다 (SC-005)',
  },
```

- [ ] **Step 5: 통과 확인**

Run: `cd backend && npx vitest run`
Expected: 전부 통과

- [ ] **Step 6: 커밋**

```bash
git add backend/src/services/diagnosisService.ts backend/src/config/configStore.ts \
        backend/tests/unit/diagnosisUnavailable.test.ts db/seeds/config.js
git -c user.name="오현근" commit -m "feat(backend): 판정을 추론 서비스에 위임하고 장애를 안내로 처리"
```

---

## Task B5: 기동 시 버전 대조

**Files:**
- Modify: `backend/src/server.ts`

- [ ] **Step 1: `bootstrap()` 에 대조를 넣는다**

```typescript
  // 2026-09-02 오전, 프론트만 새 코드로 넘어가고 백엔드가 안 따라와 화면이 비었다.
  // 프로세스가 하나 늘었으니 같은 종류의 어긋남을 기동 시점에 잡는다 (설계 4.9.5).
  const health = await inferenceHealth();
  if (!health) {
    console.warn('\n  [경고] 추론 서비스에 연결할 수 없습니다. 진단이 불가합니다.\n' +
                 `         ${env.inferenceUrl} · python -m cb_burden.serve 를 먼저 띄우세요\n`);
  } else if (health.questionSetVersion !== model.question_set_version) {
    throw new Error(
      `추론 서비스의 문항 집합이 다릅니다.\n` +
      `  백엔드 ${model.question_set_version}\n  추론   ${health.questionSetVersion}\n` +
      `  → 두 쪽이 같은 릴리스를 보도록 CB_MODELS_DIR 을 맞추세요`);
  } else {
    // 설정의 결정 가중치가 학습 산출물과 갈라지면 조용히 다른 기준으로 판정한다.
    // 막지는 않는다 — 설정으로 조정하는 것이 정당한 경우가 있다(FR-022). 다만 보이게 한다.
    const cfgW = cfg<{ weights: number[] }>('model.decisionWeights').weights;
    const artW = health.artifactDecisionWeights ?? [];
    if (JSON.stringify(cfgW) !== JSON.stringify(artW)) {
      console.warn(`\n  [경고] 결정 가중치가 학습 산출물과 다릅니다 — 판정은 설정값을 따릅니다.` +
                   `\n    설정   ${JSON.stringify(cfgW)}\n    산출물 ${JSON.stringify(artW)}` +
                   `\n    → 의도한 조정이 아니라면 db 폴더에서 'npm run seed:config' 를 실행하세요\n`);
    }
  }
```

기동 로그에 한 줄 추가한다.
```typescript
    console.log(`  추론 서비스 : ${health ? health.modelVersion + ' @ ' + env.inferenceUrl : '연결 안 됨'}`);
```

- [ ] **Step 2: 파이썬 없이 기동해 본다**

Run: `cd backend && CB_BOOTSTRAP=1 npx tsx src/server.ts`
Expected: 경고가 뜨지만 **기동은 된다** (문항 조회·기관 안내는 살아야 한다)

- [ ] **Step 3: 파이썬을 띄우고 다시 기동한다**

Expected: `판정 경로 : 추론 서비스 unix:<루트>/run/cb-inference.sock · v1.0.0`

- [ ] **Step 4: 커밋**

```bash
git add backend/src/server.ts
git -c user.name="오현근" commit -m "feat(backend): 기동 시 추론 서비스 문항 집합 대조"
```

---

## Task B6: 프론트와 계약 문서

**Files:**
- Create: `frontend/src/components/UnavailableNotice.vue`, `frontend/tests/unit/unavailable.test.ts`
- Modify: `frontend/src/pages/ResultPage.vue`, `specs/001-care-burden-map/contracts/openapi.yaml`

기존 프론트 테스트(`result.test.ts`)는 **컴포넌트 단위**로 마운트한다(store 를 세우지 않는다).
같은 방식을 따르기 위해 안내를 컴포넌트로 분리한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/tests/unit/unavailable.test.ts`
```typescript
// 추론 서비스 장애 안내 (설계 4.9.4)
//   판정 불가와 구분되어야 한다 — 부담 수준과 무관한 일시적 장애다.
import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import UnavailableNotice from '../../src/components/UnavailableNotice.vue';

describe('UnavailableNotice', () => {
  it('진단을 드릴 수 없다는 사실을 알린다', () => {
    const w = mount(UnavailableNotice, {
      props: { name: '햇살맘', notice: '지금은 진단 결과를 드릴 수 없습니다. 잠시 후 다시 시도해 주세요.' },
    });
    expect(w.text()).toContain('햇살맘님께 드리는 안내');
    expect(w.text()).toContain('지금은 진단 결과를 드릴 수 없습니다');
  });

  it('부담 구간을 뜻하는 말을 쓰지 않는다', () => {
    // 장애를 판정 결과로 오해하게 만들면 안 된다
    const w = mount(UnavailableNotice, {
      props: { name: '보호자', notice: '지금은 진단 결과를 드릴 수 없습니다.' },
    });
    expect(w.text()).not.toContain('부담군');
    expect(w.text()).not.toContain('판정 불가');
  });
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd frontend && npx vitest run tests/unit/unavailable.test.ts`
Expected: FAIL — `Failed to resolve import ... UnavailableNotice.vue`

- [ ] **Step 3: 컴포넌트를 만든다**

`frontend/src/components/UnavailableNotice.vue`
```html
<script setup lang="ts">
// 추론 서비스에 연결하지 못했을 때. 판정 불가(FR-009a)와 다른 화면이다.
defineProps<{ name: string; notice: string }>();
</script>

<template>
  <section class="undecided" aria-label="진단 안내">
    <p class="undecided__who">{{ name }}님께 드리는 안내</p>
    <p class="undecided__title">지금은 진단 결과를 드릴 수 없습니다</p>
    <p class="undecided__body">{{ notice }}</p>
  </section>
</template>

<style scoped>
.undecided { background: var(--surface); border: 1px solid var(--hairline);
  border-radius: var(--radius); padding: var(--sp-lg); }
.undecided__who { font-size: 14px; color: var(--muted); margin: 0 0 var(--sp-sm); }
.undecided__title { font-size: 22px; font-weight: 700; color: var(--ink);
  margin: 0 0 var(--sp-sm); }
.undecided__body { margin: 0; font-size: 16px; }
</style>
```

- [ ] **Step 4: 통과 확인**

Run: `cd frontend && npx vitest run tests/unit/unavailable.test.ts`
Expected: `2 passed`

- [ ] **Step 5: `ResultPage.vue` 에 분기를 넣는다**

`import UnavailableNotice from '../components/UnavailableNotice.vue';` 를 추가하고,
결과 카드 바로 다음에 둔다. 순서는 **판정됨 → 장애 → 판정 불가** 다.

```html
    <BurdenResultCard v-if="r.decided" … />

    <!-- 추론 서비스 장애 — 판정 불가와 구분한다 -->
    <UnavailableNotice v-else-if="r.unavailable"
                       :name="pre.displayName()" :notice="r.unavailableNotice" />

    <!-- 판정 불가 (FR-009a·FR-021j-1) -->
    <section v-else class="undecided" aria-label="판정 결과 안내"> … </section>
```

- [ ] **Step 6: openapi 에 필드를 추가한다**

`DiagnosisResponse` 의 `properties` 아래에 넣는다.

```yaml
        unavailable:
          type: boolean
          description: |
            추론 서비스에 연결하지 못해 판정을 내지 못한 경우 true.
            판정 불가(FR-009a)와 다르다 — 부담 수준과 무관한 일시적 장애다.
            이 경우 burdenLabel·contributions·comparison 은 모두 null 이고
            immediateReferral 은 제공된다.
        unavailableNotice:
          type: string
          nullable: true
          description: 장애 안내 문구(FR-022 설정 `notice.inferenceUnavailable`). 정상이면 null.
```

`modelVersion` 의 설명에 "추론 서비스 장애 시 null" 을 덧붙이고 `nullable: true` 로 바꾼다.

- [ ] **Step 7: 전체 프론트 테스트**

Run: `cd frontend && npx vitest run`
Expected: 전부 통과

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/components/UnavailableNotice.vue frontend/src/pages/ResultPage.vue \
        frontend/tests/unit/unavailable.test.ts \
        specs/001-care-burden-map/contracts/openapi.yaml
git -c user.name="오현근" commit -m "feat(frontend): 추론 서비스 장애 안내 화면"
```

- [ ] **Step 9: 세 구성요소를 함께 올린다**

**프론트만 올리면 2026-09-02 오전 사고가 반복된다.** 순서를 지킨다.

```bash
cd db && npm run seed:config          # notice.inferenceUnavailable · model.decisionWeights
PYTHONPATH=ml/.pylibs:ml python3 -m cb_burden.serve --release models &
cd backend && npm exec tsx src/server.ts &
# 프론트는 vite dev 가 소스를 즉시 반영하므로 별도 배포 없음
```

배포 뒤 확인:
```bash
curl -s --unix-socket run/cb-inference.sock http://localhost/health
curl -s -X POST http://127.0.0.1:9523/api/v1/diagnoses -H 'content-type: application/json' \
  -d '{"answers":[{"questionNo":1,"value":4},{"questionNo":2,"value":4},{"questionNo":3,"value":5},{"questionNo":4,"value":1},{"questionNo":5,"value":null},{"questionNo":6,"value":3},{"questionNo":7,"value":1}],"careTargetAge":20}'
```
Expected: `decided:true` · `burdenLabel` 이 있음. `consentTraining` 을 주지 않았으므로 DB 에
행이 생기지 않는다(FR-031).

---

## Task B7: TS 추론 제거 — **별도 승인 필요**

> B6 까지는 `CB_INFERENCE_URL` 을 끄고 되돌릴 수 있다. **이 작업부터는 되돌리기 어렵다.**
> 며칠 안정화한 뒤 사용자에게 확인받고 시작한다.

**Files:**
- Delete: `backend/src/inference/predictor.ts`, `backend/src/inference/undecidable.ts`, `backend/tests/parity/`
- Modify: `backend/src/inference/modelLoader.ts`

- [ ] **Step 1: 삭제 전에 확인한다**

Run: `cd backend && grep -rn "predictor\|isUndecidable\|rarity" src/ | grep -v node_modules`
Expected: 참조가 남아 있지 않다

- [ ] **Step 2: 삭제하고 modelLoader 를 줄인다**

`modelLoader.ts` 는 **문항 로드와 DB 문항 집합 대조만** 남긴다. 모델·불확실성·기여도 JSON
로드는 지운다.

- [ ] **Step 3: 전체 테스트**

Run: `cd backend && npx tsc --noEmit && npx vitest run`
Expected: 전부 통과

- [ ] **Step 4: 커밋**

```bash
git rm -r backend/tests/parity backend/src/inference/predictor.ts \
          backend/src/inference/undecidable.ts
git add backend/src/inference/modelLoader.ts
git -c user.name="오현근" commit -m "refactor(backend): TS 추론 이식본 제거 — 추론은 파이썬이 맡는다"
```

---

## Task B8: 문서와 운영 절차

**Files:**
- Modify: `CLAUDE.md`, `ml/README.md`, `docs/작업기록/오현근.md`, `backend/package.json`

`backend/package.json` 의 `test:parity` 스크립트는 B7 에서 대상이 사라지므로 지운다.
릴리스 게이트는 `pytest ml/tests/test_engine_golden.py` 로 옮겨간다.

프로세스가 2개에서 3개로 늘어난다. **어디에도 적히지 않으면 다음 사람이 파이썬을 안 띄운다.**

- [ ] **Step 1: `CLAUDE.md` 의 명령 절을 고친다**

```bash
cd backend && npm run dev      # :9523
cd frontend && npm run dev     # :9503
PYTHONPATH=ml/.pylibs:ml python3 -m cb_burden.serve --release models   # 추론(소켓)
PYTHONPATH=ml/.pylibs:ml python3 -m cb_burden train --snapshot <path> --model-version <ver>
PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests/test_engine_golden.py   # 릴리스 게이트
```

**기동 순서: 추론(소켓) → 백엔드(9523).** 백엔드가 기동 때 추론 서비스의 문항 집합을
대조한다. 순서가 바뀌면 경고가 뜨고 진단만 불가하다.

- [ ] **Step 2: `ml/README.md` 를 고친다**

`train.py` 기준 설명을 `cb_burden` CLI 로 바꾸고, **스냅샷을 먼저 만들어야 한다**는 점과
**test 602건은 `evaluate` 명령에서만 쓴다**는 규칙을 남긴다.

- [ ] **Step 3: 작업기록에 남긴다**

`docs/작업기록/오현근.md` 에 시각 태그와 함께 이관 결과를 이어 붙인다.

- [ ] **Step 4: 커밋**

```bash
git add CLAUDE.md ml/README.md docs/작업기록/오현근.md
git -c user.name="오현근" commit -m "docs: 추론 서비스 도입에 맞춰 명령과 기동 순서를 고친다"
```

---

## 완료 조건

**Phase A**
- `pytest ml/tests` 전부 통과
- 새 파이프라인 산출물이 `models/v1.0.0/` 과 1e-9 이내로 일치
- `verify` 가 현재 릴리스를 통과

**Phase B**
- `pytest ml/tests` · `backend npx vitest run` · `frontend npx vitest run` 전부 통과
- 골든 3,000건 일치
- 파이썬을 끈 상태에서 진단하면 **안내 + 기관 안내**가 나온다
- 문항 집합이 다른 릴리스를 물리면 백엔드가 뜨지 않는다
