"""제출용 최종 노트북을 생성한다 (deliverables/최종-전체과정.ipynb).

노트북을 손으로 고치지 않고 이 스크립트로 만든다 — 셀 순서·문구를 바꿀 때
diff 가 읽히고, 다시 만들면 항상 같은 결과가 나온다.

노트북이 지키는 규칙
    · 구 ml/train.py 를 쓰지 않는다. cb_burden 만 쓴다 (train.py 는 models/ 최상위를 덮어쓴다)
    · 학습 결과는 models/runs/<run_id>/ 에만 쓴다. 배포본을 바꾸지 않는다
    · test 602건을 쓰지 않는다. 배포 결정 때 1회 소진했다
    · DB 가 없어도 끝까지 돈다 (스냅샷 폴백)
    · 의존은 ml/requirements.txt 그대로 — pandas·matplotlib 를 쓰지 않는다
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'deliverables' / '최종-전체과정.ipynb'


_n = [0]


def _id():
    _n[0] += 1
    return f'cell{_n[0]:02d}'


def md(text):
    return {'cell_type': 'markdown', 'id': _id(), 'metadata': {},
            'source': [l + '\n' for l in text.strip('\n').split('\n')]}


def code(text):
    return {'cell_type': 'code', 'id': _id(), 'execution_count': None, 'metadata': {},
            'outputs': [], 'source': [l + '\n' for l in text.strip('\n').split('\n')]}


cells = []

# ─────────────────────────────────────────────────────────── 표지
cells.append(md('''
# 곁 — 돌봄부담 진단 전체 과정

**데이터 연결 → 데이터 준비 → 모델 학습 → 서비스** 를 처음부터 끝까지 실행한다.

미니프로젝트 3팀 · 모델 `v1.0.0` / 문항 집합 `qs-v1.0.0`

---

## 이 노트북이 지키는 것

| 규칙 | 왜 |
|---|---|
| 배포본(`models/*.json`)을 **바꾸지 않는다** | 운영 중이다. 시작과 끝에서 지문(sha256)을 대조해 증명한다 |
| **`test` 602건을 쓰지 않는다** | 배포 결정 때 단 한 번 썼다. 여기서는 교차검증만 본다 |
| 학습은 `models/runs/<run_id>/` **에만 쓴다** | 배포본을 바꾸는 것은 `promote` 뿐이다 |
| DB 가 없어도 **끝까지 돈다** | 고정된 스냅샷으로 폴백한다 |
| 접속 정보를 노트북에 **적지 않는다** | `.env` 에서만 읽는다 |

> **구 `ml/train.py` 를 부르지 않는다.** 그 모듈은 `models/` 최상위에 직접 쓴다.
> 이 노트북은 `cb_burden` 만 쓴다.

## 준비

```bash
pip install -r ml/requirements.txt        # 또는 ml/.pylibs 사용
```

`pandas` · `matplotlib` 를 쓰지 않는다 — 클린 환경에서 폰트·버전으로 깨질 여지를 없앴다.
'''))

# ─────────────────────────────────────────────────────────── 0. 준비
cells.append(md('''
---
## 0. 준비 — 경로·버전 확인과 배포본 지문

끝(6절)에서 같은 지문을 다시 재서 **아무것도 바뀌지 않았음**을 확인한다.
'''))

cells.append(code('''
import hashlib, json, os, subprocess, sys, time
from pathlib import Path

# 저장소 뿌리를 찾는다 — notebooks/ 에서 열든 뿌리에서 열든 동작한다
ROOT = Path.cwd()
for _ in range(3):
    if (ROOT / 'ml' / 'cb_burden').is_dir():
        break
    ROOT = ROOT.parent
assert (ROOT / 'ml' / 'cb_burden').is_dir(), f'저장소를 찾지 못했습니다 (cwd={Path.cwd()})'

# ml/.pylibs 가 있으면 쓰고, 없으면 실행 환경에 설치된 것을 쓴다
PYLIBS = ROOT / 'ml' / '.pylibs'
if PYLIBS.is_dir():
    sys.path.insert(0, str(PYLIBS))
sys.path.insert(0, str(ROOT / 'ml'))     # cb_burden 패키지용. train.py 는 부르지 않는다

import numpy, sklearn, joblib
print(f'저장소   {ROOT}')
print(f'파이썬   {sys.version.split()[0]}')
print(f'sklearn  {sklearn.__version__}   numpy {numpy.__version__}   joblib {joblib.__version__}')

EXPECT_SKLEARN = '1.6.1'
if sklearn.__version__ != EXPECT_SKLEARN:
    print(f'\\n[주의] 배포본은 sklearn {EXPECT_SKLEARN} 로 만들었습니다. '
          f'joblib 을 읽을 때 결과가 달라질 수 있습니다.')
'''))

cells.append(code('''
# 배포본 지문 — 이 노트북이 무엇도 건드리지 않았음을 끝에서 증명하기 위한 기준값
MODELS = ROOT / 'models'
WATCH = ['model_v1.json', 'model_v1.joblib', 'questions_v1.json',
         'uncertainty_v1.json', 'selection_v1.json', 'contribution_v1.json']

def fingerprint():
    out = {}
    for name in WATCH:
        p = MODELS / name
        out[name] = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
    return out

BEFORE = fingerprint()
print('배포본 지문 (앞 16자)')
for k, v in BEFORE.items():
    print(f'   {k:24s} {v[:16] if v else "(없음)"}')
'''))

# ─────────────────────────────────────────────────────────── 1. 데이터 연결
cells.append(md('''
---
## 1. 데이터 연결

DB 에 붙을 수 있으면 원천 뷰를 확인하고, 붙지 못하면 **고정된 스냅샷**으로 간다.
어느 쪽이든 이 절은 오류 없이 끝나며, **어느 경로를 썼는지 반드시 출력한다.**

### 학습은 왜 DB 가 아니라 스냅샷을 읽나

DB 는 바뀐다. 바뀌면 같은 코드가 다른 모델을 만든다. 그래서 학습 입력을 파일로 얼리고
**지문(sha256)** 을 함께 남긴다. 이 노트북도 같은 규칙을 따른다.
'''))

cells.append(code('''
# ① DB — 있으면 확인만 한다. 새 스냅샷을 만들지 않는다(스냅샷은 덮어쓰기 금지).
DB_OK, DB_INFO = False, '시도하지 않음'
# CB_NO_DB=1 로 오프라인 경로를 강제할 수 있다 — 채점 환경을 여기서 재현해 볼 때 쓴다
if os.getenv('CB_NO_DB') == '1':
    DB_INFO = 'CB_NO_DB=1 — 오프라인 경로를 강제했습니다'
elif (ROOT / '.env').exists():
    try:
        from cb_burden.data import source_db
        con = source_db.connect(); cur = con.cursor()
        cur.execute(f'SELECT COUNT(*) FROM {source_db.SOURCE_VIEW}')
        n_view = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM cb_feature_meta_v1')
        n_feat = cur.fetchone()[0]
        con.close()
        DB_OK = True
        DB_INFO = f'{source_db.SOURCE_VIEW} {n_view:,}행 · 설명변수 {n_feat}개'
    except Exception as e:
        DB_INFO = f'{type(e).__name__}: {str(e)[:70]}'
else:
    DB_INFO = '.env 가 없습니다'

print('① DB 연결 :', '성공' if DB_OK else '건너뜀')
print('           ', DB_INFO)
'''))

cells.append(code('''
# ② 스냅샷 — 학습이 실제로 읽는 것. 없으면 여기서 멈춘다.
SNAPS = sorted((ROOT / 'data' / 'snapshots').glob('*.csv.gz'))
SNAPS = [p for p in SNAPS if (p.parent / (p.name.split('.csv')[0] + '.meta.json')).exists()]
assert SNAPS, ('스냅샷이 없습니다. DB 가 있으면 아래로 만드세요\\n'
               '  python3 -m cb_burden snapshot --out data/snapshots/<날짜>.csv.gz')
SNAP = SNAPS[-1]
META = json.loads((SNAP.parent / (SNAP.name.split('.csv')[0] + '.meta.json')).read_text(encoding='utf-8'))

print(f'② 스냅샷  : {SNAP.relative_to(ROOT)}  ({SNAP.stat().st_size/1024:.0f} KB)')
print(f'            원천 {META["source_view"]} · {META["rows"]:,}행 · 변수 {META["features"]}개')
print(f'            train {META["split"]["train"]:,} / test {META["split"]["test"]:,}')
print(f'            지문 {META["sha256"][:32]}…')
print()
print('학습에 쓰는 것 → 스냅샷' + ('  (DB 는 확인만 했습니다)' if DB_OK else '  (DB 없이 진행합니다)'))
'''))

# ─────────────────────────────────────────────────────────── 2. 데이터 준비
cells.append(md('''
---
## 2. 데이터 준비

스냅샷을 읽으면서 **지문을 다시 계산해 대조**한다. 파일이 한 글자라도 바뀌면 여기서 멈춘다.
'''))

cells.append(code('''
from cb_burden.data import snapshot, integrity

snap = snapshot.read(SNAP)          # 지문이 meta 와 다르면 ValueError
integrity.check(snap)               # train/test/변수/fold + 누수 배제 5검사
print('지문 대조 통과 · 무결성 5검사 통과\\n')

import numpy as np
y, split, fold = snap['y'], snap['split'], snap['cv_fold']
tr = split == 'train'

print(f'{"":10s} {"train":>8s} {"test":>8s}   비율차')
for lv in (1, 2, 3, 4, 5):
    a = (y[tr] == lv).sum() / tr.sum() * 100
    b = (y[~tr] == lv).sum() / (~tr).sum() * 100
    print(f'  {lv}등급   {int((y[tr]==lv).sum()):8d} {int((y[~tr]==lv).sum()):8d}   {a:5.1f}% vs {b:5.1f}%')
print(f'\\n층화 확인 — 최대 비율차 '
      f'{max(abs((y[tr]==l).sum()/tr.sum() - (y[~tr]==l).sum()/(~tr).sum())*100 for l in range(1,6)):.2f}%p')
print('폴드별 건수 :', [int((fold[tr] == k).sum()) for k in (1, 2, 3, 4, 5)])
'''))

cells.append(code('''
# 결측 — 채우지 않는다. 여기서 결측은 "모름"이 아니라 설문 분기다.
X, feats = snap['X'], snap['features']
sentinel = -1
miss = [(int((X[tr, j] == sentinel).sum()), f) for j, f in enumerate(feats)]
have = sorted([m for m in miss if m[0]], reverse=True)

print(f'설명변수 {len(feats)}개 중 결측이 있는 변수 {len(have)}개 · '
      f'전체 칸의 {sum(m[0] for m in miss)/(len(feats)*tr.sum())*100:.1f}%\\n')
for n, f in have[:6]:
    print(f'   {f:32s} {n:5d}건  {n/tr.sum()*100:5.1f}%')
print('\\n최빈값으로 채우지 않는다 — 취업 경험이 없으면 "왜 그만뒀나"를 애초에 묻지 않는다.')
print('결측은 -1 이라는 하나의 범주로 학습된다(원-핫에서 칸 하나).')
'''))

# ─────────────────────────────────────────────────────────── 3. 학습
cells.append(md('''
---
## 3. 모델 학습

`cb_burden train` 을 실제로 실행한다. 네 단계를 거친다.

```
[1/4] baseline    설명변수 38개 전체로 계열 비교 (rf · et · logit)
[2/4] select      후진 제거로 문항 선별
[3/4] calibrate   판정 불가 임계값을 데이터에서 도출
[4/4] export      아티팩트를 models/runs/<run_id>/ 에만 쓴다
```

> **배포본을 건드리지 않는다.** `export` 는 인자로 받은 `run_dir` 에만 쓰고,
> `models/*.json` 을 바꾸는 것은 `promote` 뿐이다. 이 노트북은 `promote` 를 부르지 않는다.
'''))

cells.append(code('''
env = dict(os.environ)
env['PYTHONPATH'] = os.pathsep.join(
    [str(PYLIBS), str(ROOT / 'ml')] if PYLIBS.is_dir() else [str(ROOT / 'ml')])

t0 = time.time()
proc = subprocess.run(
    [sys.executable, '-m', 'cb_burden', 'train',
     '--snapshot', str(SNAP),
     '--model-version', 'nb-run',              # 배포하지 않는 이름
     '--question-set-version', 'qs-v1.0.0'],
    cwd=str(ROOT), env=env, capture_output=True, text=True)
print(proc.stdout)
if proc.returncode != 0:
    print(proc.stderr[-1500:])
    raise SystemExit('학습이 실패했습니다')
print(f'(소요 {time.time()-t0:.1f}초)')
'''))

cells.append(code('''
# 방금 만든 실행 폴더를 찾는다
RUNS = sorted((MODELS / 'runs').glob('*/run.json'), key=lambda p: p.stat().st_mtime)
RUN = RUNS[-1].parent
run = json.loads((RUN / 'run.json').read_text(encoding='utf-8'))
print(f'실행 폴더 {RUN.relative_to(ROOT)}\\n')
for st in run['stages']:
    m = st['metrics']
    if st['name'] == 'baseline':
        for fam, v in m.items():
            print(f'   baseline {fam:6s} macro F1 {v["macro_f1"]:.4f} · '
                  f'고부담 재현율 {v["high_burden_recall"]:.4f}')
    else:
        print(f'   {st["name"]:10s} {json.dumps(m, ensure_ascii=False)}')
'''))

cells.append(md('''
### 재현성 — 방금 학습한 모델이 배포본과 같은가

같은 스냅샷·같은 시드로 학습했으니 배포본과 같은 계수가 나와야 한다.
**이 코드가 저 모델을 만들었다**를 계수 단위로 확인한다.
'''))

cells.append(code('''
new = json.loads((RUN / 'model_v1.json').read_text(encoding='utf-8'))
dep = json.loads((MODELS / 'model_v1.json').read_text(encoding='utf-8'))

same_feats = list(new['features']) == list(dep['features'])
print(f'계열        {new["family"]:6s} vs {dep["family"]}')
print(f'문항        {len(new["features"])}개 vs {len(dep["features"])}개 · '
      f'{"동일" if same_feats else "다름"}')
if not same_feats:
    print('   새로 :', new['features'])
    print('   배포 :', dep['features'])
if same_feats and new['family'] == dep['family'] == 'logit':
    dc = float(np.abs(np.asarray(new['coef']) - np.asarray(dep['coef'])).max())
    di = float(np.abs(np.asarray(new['intercept']) - np.asarray(dep['intercept'])).max())
    print(f'계수 최대차 {dc:.3e}')
    print(f'절편 최대차 {di:.3e}')
    print(f'결정 가중치 {new["decision_weights"]} vs {dep["decision_weights"]}')
    print('\\n→ 재현됩니다' if dc < 1e-9 and di < 1e-9 else '\\n→ 값이 다릅니다. 아래 주석 참고')

nu = json.loads((RUN / 'uncertainty_v1.json').read_text(encoding='utf-8'))
du = json.loads((MODELS / 'uncertainty_v1.json').read_text(encoding='utf-8'))
print(f'\\n판정 불가 임계값')
print(f'   tau_conf  {nu["tau_conf"]:.6f} vs {du["tau_conf"]:.6f}')
print(f'   tau_dens  {nu["tau_dens"]:.6f} vs {du["tau_dens"]:.6f}')
'''))

# ─────────────────────────────────────────────────────────── 4. 평가
cells.append(md('''
---
## 4. 평가 — `test` 602건을 쓰지 않는다

`test` 는 **모든 결정이 끝난 뒤 단 한 번** 쓰기로 한 데이터이고, 배포본 `v1.0.0` 평가에서
이미 소진했다. 이 노트북에서 다시 쓰면 그 규칙이 깨진다.

그래서 여기서는 **교차검증 지표만** 보고, 최종 성능은 **그때 기록된 값을 인용**한다.
'''))

cells.append(code('''
sel = json.loads((RUN / 'selection_v1.json').read_text(encoding='utf-8'))
print('이번 실행 — 교차검증 (train 2,398건 · 5-fold)')
print(f'   채택 계열      {new["family"]}')
print(f'   선별 문항 수   {sel["k"]}개')
print(f'   판정 불가 비율 {nu["rate"]*100:.2f}% (train 기준)')
print(f'   오분류율       판정불가 {nu["err_undecidable"]:.3f} vs 판정 {nu["err_decided"]:.3f}')
print(f'   교차검증       macro F1 {nu["cv"]["macro_f1"]:.4f} · '
      f'고부담 재현율 {nu["cv"]["high_burden_recall"]:.4f}')

# 배포본이 test 로 받은 성적 — 그때 기록된 값을 읽기만 한다
rec = [json.loads(p.read_text(encoding='utf-8')) for p in (MODELS / 'runs').glob('*/run.json')]
rec = [r for r in rec if r.get('evaluation')]
print('\\n배포본 v1.0.0 — test 602건 (2026-09-02 에 1회 사용 · 여기서 다시 쓰지 않음)')
if rec:
    e = rec[0]['evaluation']
    print(f'   macro F1       {e["macro_f1"]:.4f}   (기준 모델 {e["baseline"]["macro_f1"]:.4f})')
    print(f'   고부담 재현율   {e["high_burden_recall"]:.4f}   (기준 모델 {e["baseline"]["high_burden_recall"]:.4f})')
    print(f'   판정 불가       {e["undecidable_rate"]*100:.2f}%')
    for k, v in rec[0]['success_criteria'].items():
        print(f'   {"PASS" if v else "FAIL"}  {k}')
else:
    print('   기록을 찾지 못했습니다 (models/runs/ 에 평가된 실행이 없습니다)')
'''))

# ─────────────────────────────────────────────────────────── 5. 서비스
cells.append(md('''
---
## 5. 서비스 — 실제 판정

판정 경로를 순서대로 시도한다. 서버를 띄우지 않아도 같은 답을 얻는다.

```
① 추론 서비스가 살아 있으면  → 유닉스 소켓으로 요청 (운영과 같은 경로)
② 아니면                    → deliverables/predict.py 를 그 자리에서 호출
```

**판정이 성립하는 응답 1건**과 **판정하지 못하는 응답 1건**을 함께 본다.
판정 불가일 때 구간도 기여 요인도 내지 않는 것이 이 서비스의 핵심 설계다.
'''))

cells.append(code('''
import http.client, socket

SOCK = ROOT / 'run' / 'cb-inference.sock'
POLICY = json.loads((ROOT / 'deliverables' / 'policy.json').read_text(encoding='utf-8')) \\
    if (ROOT / 'deliverables' / 'policy.json').exists() else None

class UnixHTTP(http.client.HTTPConnection):
    def __init__(self, path): super().__init__('localhost'); self._p = path
    def connect(self):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.settimeout(3); s.connect(self._p)
        self.sock = s

def via_service(answers):
    c = UnixHTTP(str(SOCK))
    body = json.dumps({'answers': answers, 'policy': {
        'tauConf': du['tau_conf'], 'tauDens': du['tau_dens'],
        'decisionWeights': dep['decision_weights'],
        'contributionMinThreshold': json.loads(
            (MODELS / 'contribution_v1.json').read_text(encoding='utf-8'))['min_threshold']}})
    c.request('POST', '/predict', body, {'Content-Type': 'application/json'})
    return json.loads(c.getresponse().read())

# CB_NO_SERVICE=1 로 소켓을 건너뛴다 — 서버 없는 채점 환경을 재현해 볼 때 쓴다
ROUTE = None
if SOCK.exists() and os.getenv('CB_NO_SERVICE') != '1':
    try:
        c = UnixHTTP(str(SOCK)); c.request('GET', '/health'); h = json.loads(c.getresponse().read())
        ROUTE = f'추론 서비스 (unix 소켓) · 모델 {h["modelVersion"]}'
    except Exception as e:
        ROUTE = None
if ROUTE is None:
    sys.path.insert(0, str(ROOT / 'deliverables'))
    import predict as P
    ROUTE = '제출 패키지 deliverables/predict.py (서버 없이 그 자리에서 계산)'
print('판정 경로 :', ROUTE)
'''))

cells.append(code('''
NAMES = {1: '최고부담군', 2: '고부담군', 3: '중간부담군', 4: '저부담군', 5: '부담 없음'}
CASES = [('판정이 성립하는 응답', [4, 4, 5, 1, None, 3, 1]),
         ('판정하지 못하는 응답', [4, 1, 5, 5, 5, 6, 2])]

for title, vals in CASES:
    answers = [{'questionNo': i + 1, 'value': v} for i, v in enumerate(vals)]
    if ROUTE.startswith('추론'):
        r = via_service(answers)
    else:
        r = P.predict({'answers': answers})
    print(f'\\n■ {title}   {vals}')
    print(f'   판정 성립      {r["decided"]}')
    if r['decided']:
        lv = r['internalLabel']
        print(f'   구간          {lv} → 표시 명칭 "{NAMES[lv]}"   (1이 최고부담인 역방향 척도)')
        print(f'   최대 확률      {r["maxProba"]:.4f}')
        print(f'   기여 요인      ' + ', '.join(
            f'{c["feature"]}({c["contrib"]:+.3f})' for c in r['contributions']))
    else:
        print(f'   사유          {r["undecidableReason"]}'
              f'  (희소성 {r["rarity"]:.4f} · 최대 확률 {r["maxProba"]:.4f})')
        print(f'   구간          {r["internalLabel"]}  ← 내지 않는다')
        print(f'   기여 요인      {r["contributions"]}  ← 내지 않는다')
        print('   서비스에서는 이 경우에도 기관 안내가 나갑니다 (FR-021j)')
'''))

# ─────────────────────────────────────────────────────────── 6. 마무리
cells.append(md('''
---
## 6. 마무리 — 배포본이 그대로인가

0절에서 찍은 지문을 다시 잰다. 하나라도 다르면 이 노트북이 배포본을 건드린 것이다.
'''))

cells.append(code('''
AFTER = fingerprint()
diff = [k for k in WATCH if BEFORE[k] != AFTER[k]]
for k in WATCH:
    print(f'   {k:24s} {"동일" if BEFORE[k] == AFTER[k] else "★변경됨"}')
print()
if diff:
    raise SystemExit(f'배포본이 바뀌었습니다: {diff}')
print('배포본 무변경 확인 — 이 노트북은 models/runs/ 에만 썼습니다.')
print(f'이번 실행 산출물 : {RUN.relative_to(ROOT)}')
print('\\n실행을 반복하면 models/runs/ 에 폴더가 쌓입니다. 필요 없으면 지워도 됩니다.')
'''))

cells.append(md('''
---

## 요약

| 절 | 한 일 |
|---|---|
| 1 | DB 연결 확인(선택) · 학습 입력은 지문으로 고정된 스냅샷 |
| 2 | 지문 대조 · 무결성 5검사 · 층화 확인 · 결측을 채우지 않는 이유 |
| 3 | `cb_burden` 4단계 학습 → `runs/` · 배포본과 계수 대조 |
| 4 | 교차검증 지표만 확인 · `test` 602건 미사용 |
| 5 | 실제 판정 2건 — 성립 / 판정 불가 |
| 6 | 배포본 지문 재대조 |

**모델의 용도·한계·사용 금지 상황은 `deliverables/model_card.md` 를 본다.**
'''))

nb = {
    'cells': cells,
    'metadata': {
        'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
        'language_info': {'name': 'python', 'version': '3.9.6',
                          'mimetype': 'text/x-python', 'file_extension': '.py',
                          'pygments_lexer': 'ipython3', 'nbconvert_exporter': 'python'},
    },
    'nbformat': 4, 'nbformat_minor': 5,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding='utf-8')
n_code = sum(1 for c in cells if c['cell_type'] == 'code')
print(f'생성 {OUT.relative_to(ROOT)}  셀 {len(cells)}개 (코드 {n_code} · 설명 {len(cells)-n_code})')
