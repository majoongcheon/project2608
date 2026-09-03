# 곁 — 돌봄부담 진단·복지연계 서비스

발달장애인 보호자를 위한 **경량 돌봄부담 자가 진단**과, 그 결과에 따른
**지도 기반 복지서비스 신청처 안내**.

> 부담이 큰 보호자를 놓치지 않고 지원으로 잇는 것이 목적이다.
> 정확한 등급을 매기는 것이 목적이 아니다.

---

## 1. 문제 정의

발달장애인 보호자는 돌봄 부담을 혼자 안고 가기 쉽고, **이용할 수 있는 지원이 있다는
사실조차 모르는 경우**가 많다. 기존 부담 척도는 문항이 30개 이상이라 진입 장벽이 높다.

이 서비스는 두 가지를 한다.

```
① 7문항으로 부담 수준을 가늠한다        30문항 척도 → 후진 제거로 7문항
② 결과에 따라 신청처를 바로 안내한다     전국 875개 기관 · 시군구 221곳
```

### 설계에서 양보하지 않은 것

| 원칙 | 구현 |
|---|---|
| **모를 때는 모른다고 한다** | 확신이 낮거나 응답이 드물면 등급을 내지 않는다. **대신 기관 안내는 계속 나간다** |
| **놓치는 쪽이 더 비싸다** | 고부담 확률에 가중치를 둬 재현율을 우선한다 (77.3%) |
| **개인 식별 정보를 보관하지 않는다** | 저장 금지 항목은 **컬럼 자체를 두지 않는다.** 관측 로그와 동의 응답은 공통 컬럼이 없어 구조적으로 결합할 수 없다 |
| **근거 없는 값을 못박지 않는다** | 문항 수·임계값을 스펙에 적지 않고 **학습 데이터에서 도출**한다 |

자세한 것은 [`deliverables/model_card.md`](deliverables/model_card.md).

---

## 2. 구조

```
┌─ 오프라인 학습 (배포 대상 아님) ─────────────────────────────────────────┐
│  실태조사 3,000행 ─→ 스냅샷(.csv.gz + sha256) ─→ 학습 4단계 ─→ 평가 ─→ 승격 │
│                     DB 를 읽는 유일한 지점        runs/ 에만 씀   test 1회  │
└──────────────────────────────────────────────┬─────────────────────────┘
                                               ▼
                              models/  model_v1.json(배포 계약) · joblib · 문항 · 임계값
                                   ┌───────────┴───────────┐
                                   ▼                       ▼
┌─ 서비스 ─────────────────────────────────────────────────────────────────┐
│  파이썬 추론 서비스  ◀─ 유닉스 소켓 ─▶  백엔드 :9523  ◀─▶  프론트 :9503      │
│  (판정 계산 전담)                      (조립·연계)         (화면)          │
│                                          │                              │
│                                          ▼                              │
│                          MariaDB   설정 · 문항 · 기관 · 지역              │
│                                    관측 로그 · 동의 응답                  │
└─────────────────────────────────────────────────────────────────────────┘
```

**셋이 도는 속도가 다르다** — 학습은 사람이 명령할 때만, 서비스는 요청마다,
설정은 백엔드가 기동할 때 한 번.

### 판정 요청 한 건

```
7문항 응답
  → 문항 집합 버전 대조 (어긋나면 409)
  → 미응답 검사 (있으면 422 + 문항 번호)
  → "해당 없음"(null) → -1 치환
  → 추론 서비스: 확률 · 희소성 · 판정 불가 · 기여 요인
  → 결과 조립: 표시 명칭 · 기여 요인 · 참조 비교
  → 즉시 연계: 부담=발동 · 연령=필터 · 거리=정렬  ← 판정 불가여도 발동
  → 내부 라벨 제거 후 응답
```

### 기술 스택

| 영역 | 스택 |
|---|---|
| 프론트엔드 | Vue 3.4 · TypeScript 5 · Vite 5 · Pinia 2 · Leaflet(OpenStreetMap) |
| 백엔드 | Node.js 20 · Express 4 · TypeScript 5 · mysql2 3 |
| 데이터베이스 | MariaDB 12.1.2 |
| 오프라인 학습 | Python 3.9~3.11 · scikit-learn 1.6.1 (**배포 대상 아님**) |
| 테스트 | Vitest · Playwright · pytest |

Docker 를 쓰지 않는다. 프로젝트 폴더 안의 코드와 선언적 설정으로만 전개한다.

### 폴더

```
frontend/          Vue 앱
backend/           Express API
ml/                학습·추론 라이브러리 (cb_burden) 와 실험 스크립트
models/            배포 아티팩트 — models/*.json 이 배포 계약이다
db/                마이그레이션 · 시드
data/snapshots/    학습 입력 스냅샷 (지문 sha256 과 함께 고정)
deliverables/      제출용 산출물 (아래 §5)
docs/              분석·작업 기록
specs/             기능 명세 (spec · plan · tasks)
```

---

## 3. 실행

### 준비

```bash
cp .env.example .env          # DB 접속 정보를 채운다. .env 는 커밋하지 않는다
pip3 install --target ml/.pylibs -r ml/requirements.txt
cd backend && npm install && cd ../frontend && npm install && cd ..
cd db && npm install && npm run migrate && npm run seed && cd ..
```

### 기동 — 순서가 있다

**추론 서비스를 먼저 띄운다.** 백엔드가 기동하면서 추론 서비스의 문항 집합을 대조한다.

```bash
# ① 추론 서비스 — 유닉스 소켓을 쓴다. 포트를 점유하지 않는다
PYTHONPATH=ml/.pylibs:ml python3 -m cb_burden.serve --release models

# ② 백엔드
cd backend && npm run dev      # :9523

# ③ 프론트
cd frontend && npm run dev     # :9503
```

기동할 때 **정합이 하나라도 어긋나면 뜨지 않는다.** 조용히 잘못된 판정을 내는 것보다
뜨지 않는 편이 낫다는 판단이다.

### 학습

**스냅샷을 먼저 만들고, 학습은 `models/runs/` 에만 쓴다. 배포본은 `promote` 로만 바뀐다.**

```bash
PYTHONPATH=ml/.pylibs:ml python3 -m cb_burden snapshot --out data/snapshots/<날짜>.csv.gz
PYTHONPATH=ml/.pylibs:ml python3 -m cb_burden train --snapshot <path> \
    --model-version <ver> --question-set-version <qs>
PYTHONPATH=ml/.pylibs:ml python3 -m cb_burden evaluate models/runs/<run_id>   # test 1회만
PYTHONPATH=ml/.pylibs:ml python3 -m cb_burden promote models/runs/<run_id> --as <ver>
```

> ⚠️ **`test` 602건은 모든 결정이 끝난 뒤 단 한 번만 쓴다.** `v1.0.0` 평가에서 이미 소진했다.
> `evaluate` 는 같은 실행을 두 번 평가하지 못하게 막는다.

### 테스트

```bash
PYTHONPATH=ml/.pylibs:ml python3 -m pytest ml/tests     # 골든 포함 (릴리스 게이트)
cd backend && npm run test
cd frontend && npm run test
```

---

## 4. 데이터

| 항목 | 실측 (2026-09-03) |
|---|---|
| 학습 데이터 | 3,000행 · 설명변수 38개 · train 2,398 / test 602 (층화) |
| 등급 분포 | 1:464 · 2:1,165 · 3:916 · 4:378 · 5:77 → 고부담 54.3% |
| 결측 | 38변수 중 14개 · 전체 칸의 12.8% (**대치하지 않고 `-1` 로 학습**) |
| 기관 | **875개** (수집 원본 1,283건을 같은 기관끼리 합친 수) · 좌표 결측 0 |
| 지역 | 시군구 229곳 중 **221곳**에 기관 데이터 |

**결측을 채우지 않는 이유** — 여기서 결측은 "모름"이 아니라 **설문 분기**다.
취업 경험이 없으면 "왜 그만뒀나"를 묻지 않는다(88.2%). 채우면 없던 사실을 만들게 된다.

---

## 5. 제출 산출물

```
deliverables/
├── model.joblib     Pipeline(OneHotEncoder → LogisticRegression)
├── schema.json      입력 문항 · 타입 · 허용 범위 · 결측 규칙
├── policy.json      결정 가중치 · 판정 불가 임계값 · 빈도표 · 기여도 기준
├── predict.py       predict(payload) -> dict
└── model_card.md    용도 · 성능 · 사용 금지 상황
```

```python
from predict import predict
predict({"answers": [{"questionNo": 1, "value": 4}, ..., {"questionNo": 7, "value": 1}]})
```

> ⚠️ **`model.joblib` 만 단독으로 쓰면 안 된다.** Pipeline 은 전처리와 확률까지만 담당하며,
> **결정 가중치와 판정 불가가 빠져** 서비스와 다른 답을 낸다.
> 운영과 같은 판정을 얻으려면 `predict.py` 의 `predict()` 를 쓴다.

### 생성과 검증

```bash
PYTHONPATH=ml/.pylibs:ml python3 ml/HG_build_deliverables.py   # 재학습하지 않는다
python3 ml/HG_verify_deliverables.py                           # 3,000건 대조
```

같은 계산이 두 벌(`ml/cb_burden/serve/engine.py` · `deliverables/predict.py`)이 되었으므로,
**갈라지지 않았는지 3,000건으로 대조한다.** 확률·희소성·기여도·판정 불가·등급 모두 일치를
확인했다(최대 오차 3.3e-16).

---

## 6. 문서

| 문서 | 내용 |
|---|---|
| [`deliverables/model_card.md`](deliverables/model_card.md) | 용도 · 성능 · 한계 · **사용 금지 상황** |
| [`docs/HG-데이터분석-기록.md`](docs/HG-데이터분석-기록.md) | 성능 해석 · 관계·인과 한계 · 스냅샷과 구조 · 가중치 민감도 |
| [`docs/작업기록/`](docs/작업기록/) | 팀원별 시간순 작업 기록 |
| `specs/001-care-burden-map/` | 기능 명세 (spec · plan · tasks · contracts) |
| `CLAUDE.md` | 개발 규약 — 척도 방향 · 작성자 귀속 · 반드시 지킬 것 |

---

## 7. 자격 증명

`.env` 에서만 읽는다(`.env.example` 참조). `.env` 는 `.gitignore` 로 제외되어 있다.

> ⚠️ `Intent-Plan.md` 와 일부 노트북에 평문 접속 정보가 남아 있다(`tasks.md` T098 미완).
> **복사하거나 그대로 배포하지 말 것.**
