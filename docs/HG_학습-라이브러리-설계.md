# 학습·추론 라이브러리화 — 설계

**작성** 오현근 세션 · 2026-09-02
**개정** 2026-09-02 — 범위를 추론 서비스까지 확장 (v2)
**상태** 설계 승인됨 · 구현 계획 있음(`docs/HG_학습-라이브러리-구현계획.md`)
**범위** `ml/` 을 파이썬 패키지 `cb_burden` 으로 만들어 **학습부터 추론 서비스 제공까지**
책임지게 하고, 산출물 경로와 서비스 인계 계약을 고정한다.

---

## 1. 목적

지금 파이프라인은 **동작하지만 경로가 보호되어 있지 않다.** 2026-09-01~02 이틀 동안 그
때문에 사고가 세 건 확인됐다. 이 설계는 기능을 늘리지 않는다. **이미 하고 있는 일을
사고가 구조적으로 불가능한 형태로 다시 세운다.**

목표는 넷이다.

1. **과정이 정확할 것** — 어떤 데이터에 어떤 코드로 무엇을 만들었는지 실행마다 남는다
2. **경로가 정확할 것** — 학습이 배포본을 덮을 수 없고, 교체는 검증을 통과한 승격으로만
3. **모델을 바꾸기 쉬울 것** — 학습한 객체를 그대로 서비스가 쓴다. 계열을 바꿔도 이식이 없다
4. **서비스 인계가 명시적일 것** — 계약을 코드로 검증하고, 버전이 어긋나면 뜨지 않는다

---

## 2. 결정 사항

| 항목 | 결정 | 근거 |
|---|---|---|
| 라이브러리 경계 | **학습 + 추론 서비스** | 앞으로 모델 계열을 바꿀 수 있다. 계수만 뽑아 이식하는 방식은 로지스틱·트리까지는 되지만 부스팅·앙상블로 가면 이식 비용이 급격히 커진다 |
| 범용성 | **돌봄부담 전용 정식화.** target 은 `care_burden` 고정 | 발표 일정 안에서 끝낸다. 암묵적 규칙을 명시적 계약으로 바꾸는 것이 목표 |
| 데이터 입력 | **스냅샷 고정 + DB 어댑터** | DB가 바뀌어도 과거 모델을 재현할 수 있고, DB 없이 전 단계를 테스트할 수 있다 |
| 추론 서비스 책임 | **모델 영역 전부** — 확률·구간 결정·기여 요인·희소성·판정 불가 여부 | 모델을 바꿀 때 Node 를 건드리지 않아도 된다 |
| 판정 정책 소유권 | **Node 가 요청에 실어 보낸다** (3.7 참조) | FR-009c(설정으로 조정) 유지. 파이썬은 상태 없는 계산기가 된다 |
| 장애 시 동작 | **안내 + 기관은 계속 제공** | 틀린 판정을 내느니 안 하는 편이 낫다. 판정 불가와 같은 안전망 경로를 재사용한다 |
| 프레임워크 | **FastAPI + uvicorn** | 요청·응답 스키마 검증이 내장되어 계약을 경계에서 강제한다 |

---

## 3. 문제 정의 — 실제로 벌어진 일

추측이 아니라 2026-09-01~02에 확인된 사고다.

### 3.1 산출물이 배포본을 직접 덮는다

`train.py` 는 `models/*.json` 을 직접 쓴다. 버전 보관은 사람이 사후에 폴더로 복사한다.

- 2026-09-01 14:21~15:10 사이 최상위 `models/` 에 14문항 실험 모델이 올라가 있었다.
  그 시간대에 서비스를 본 사람은 다른 모델을 본 것이다
- 15:10에 사람이 수동으로 v1.0.0 을 되돌려 놓았다

### 3.2 부작용이 숨어 있다

`db.py: record_model_version()` 은 `model_version` 을 키로 `ON DUPLICATE KEY UPDATE` 한다.
평가 시 `MODEL_VERSION` 을 주지 않으면 **다른 버전의 성능 기록을 덮어쓴다.**

- `cb_model_version_v1` 의 v1.0.0 행이 14문항 평가 결과로 덮여 있었다
  (판정불가율 0.0415 — 실제 v1.0.0 은 0.0249)
- **2026-09-02 11:37 정정 완료** — `MODEL_VERSION=v1.0.0` 으로 `evaluate` 를 다시 돌려
  0.3416 / 0.7730 / 0.0249 로 복구했다. 그 과정에서 14문항 평가 기록은 사라졌다

### 3.3 입력이 고정돼 있지 않다

`db.py` 가 `v_cb_tree_v1` 을 매번 새로 읽는다. 뷰나 원본이 바뀌면 **과거 모델을 다시 만들
수 없다.** 지금은 행 수·변수 수 단언으로만 막고 있는데, 이는 "달라졌다"를 잡을 뿐
"무엇이었는지"를 남기지 못한다.

### 3.4 단계 경계가 없다

`train.py` 한 파일(23.7 KB)에 baseline·select·calibrate·export·evaluate 가 모두 있다.
한 단계만 다시 돌리거나 한 단계만 테스트하기 어렵다.

### 3.5 테스트가 없다

`ml/tests/` 는 비어 있다. 회귀를 잡는 장치는 backend 의 parity 테스트뿐인데, 그것은
**추론 이식이 맞는지**를 보지 학습 파이프라인이 맞는지를 보지 않는다.

### 3.6 인계 계약이 암묵적이다

백엔드는 기동할 때 세 가지 정합을 검사하지만, 학습 쪽에는 같은 검사가 없다.

- `models/v1.1.0`·`v1.2.0` 에는 `parity_v1.json` 이 **없다.** 릴리스 게이트를 통과한 적이
  없는 실험 모델인데, 폴더 이름만 보면 배포 후보로 보인다
- 환경변수 이름도 갈라져 있다 — 학습은 `MODELS_DIR`, 백엔드는 `CB_MODELS_DIR`

### 3.7 모델을 바꾸려면 두 번 구현해야 한다

지금은 파이썬이 학습한 계수를 JSON 으로 뽑고 **TypeScript 가 추론을 다시 구현**한다.
선형 모델이라 계수가 곧 모델 전부여서 성립하는 구조다(오늘 확인: 복원 오차 3.3e-16).

문제는 **모델 계열을 바꿀 때**다. 트리까지는 노드 배열로 펴서 내보내고 있으나, 부스팅이나
앙상블로 가면 이식 비용이 급격히 커진다. `predictor.ts` 를 계열마다 새로 써야 한다.

### 3.8 구성요소 버전이 어긋난 채 조용히 돈다

2026-09-02 오전, 프론트만 새 코드로 넘어가고 백엔드는 전날 프로세스로 남아 응답 필드
이름이 어긋났다. **판정 불가 화면이 통째로 사라졌는데 아무 오류도 나지 않았다.**

프론트는 `vite dev` 라 소스를 고치면 즉시 반영되고, 백엔드는 수동 재기동이 필요하다.
이 비대칭이 원인이다. **추론 서비스를 추가하면 이 위험이 하나 더 늘어난다 — 설계로 막아야 한다.**

---

## 4. 설계

### 4.1 패키지 구조

```
ml/
  pyproject.toml
  requirements.txt              sklearn·numpy 버전 고정 (pickle 로드 안정성)
  cb_burden/
    __init__.py
    config.py                   도메인 상수 (4.2)
    data/
      source_db.py              DB 어댑터 — 스냅샷 생성에만 쓴다
      snapshot.py               스냅샷 읽기·쓰기·해시
      integrity.py              무결성 검증
      record.py                 성능 기록 (model_version 필수·중복 거부)
    stages/
      baseline.py               계열 비교 (logit·rf·et)
      select.py                 후진 제거
      calibrate.py              판정 불가 임계값 보정
      export.py                 아티팩트 생성 (JSON 6종 + joblib)
      evaluate.py               test 1회 평가
    artifacts/
      validate.py               스키마·정합·척도 방향 검증
      manifest.py               run manifest 생성·기록
      golden.py                 골든 케이스 생성
      release.py                승격 규칙과 current.json
    explain/
      saabas.py                 기여도 계산
    serve/                      ★ 추론 서비스
      engine.py                 joblib 로드 + 판정 (상태 없는 계산)
      schema.py                 요청·응답 스키마 (pydantic)
      app.py                    FastAPI 앱 — /predict · /health
      __main__.py               python -m cb_burden.serve
    questions.py                변수 → 자연어 문항 변환
    cli.py                      python -m cb_burden <명령>
  tests/
    fixtures/mini_snapshot.csv.gz      합성 300행
    fixtures/make_fixture.py           픽스처 생성기
    test_config.py                     도메인 상수
    test_snapshot.py                   쓰기·읽기·해시 대조
    test_integrity.py                  행수·변수·fold·배제변수
    test_artifacts_validate.py         스키마·정합·**척도 방향**
    test_manifest.py                   run.json
    test_promote_rules.py              승격 거부 규칙
    test_record_guard.py               DB 기록 가드
    test_stages_smoke.py               단계 전체 스모크
    test_golden_build.py               골든 생성
    test_engine_golden.py              3,000건 골든 대조
    test_serve_api.py                  요청·응답 계약
```

**모듈 하나가 한 가지만 한다.** 단계 함수는 값만 돌려주고, 파일 쓰기는 `artifacts/` 와
`cli.py` 에만 있다. `serve/engine.py` 는 **파일도 DB도 건드리지 않는다** — 로드된 모델과
입력만으로 계산한다.

### 4.2 도메인 상수 — `config.py`

암묵적으로 흩어져 있던 규칙을 한 곳에 모은다. **여기 있는 값은 헌법·스펙이 정한 것이고
실험으로 바꾸지 않는다.**

```python
CLASSES = [1, 2, 3, 4, 5]          # 1 이 최고부담인 역방향 척도
MISSING_SENTINEL = -1
TARGET = 'care_burden'

# FR-004b — target 과 같은 블록이라 입력에 쓰지 않는다
EXCLUDED_FEATURES = {
    'caregiver_life_satisfaction', 'care_difficulty_top1', 'needed_care_service_type',
    'work_care_gap_hours', 'work_care_gap_exp', 'integrated_care_awareness',
}

SUCCESS_CRITERIA = {              # SC-004 · SC-005 · SC-016
    'max_f1_loss': 0.03, 'max_recall_loss': 0.05,
    'min_recall_abs': 0.70, 'max_undecidable_rate': 0.10,
}
SEED = 42
```

**판정 임계값과 결정 가중치는 여기 없다.** 그것은 설정(`cb_config_v1`)이 소유한다(4.9.2).

### 4.3 데이터 경로 — 스냅샷으로 고정

```
data/snapshots/
  cb_dataset_2026-09-01.csv.gz
  cb_dataset_2026-09-01.meta.json
```

```json
{ "created_at": "2026-09-01T11:40:00+09:00",
  "source_view": "v_cb_tree_v1",
  "rows": 3000, "features": 38,
  "split": { "train": 2398, "test": 602 },
  "sha256": "…",
  "db": { "host": "…", "database": "…" } }
```

**규칙**

- DB 접근은 `snapshot` 명령에만 있다. 학습 단계도 추론 서비스도 DB를 열지 않는다
- 학습 시작 시 스냅샷의 sha256 을 다시 계산해 `meta.json` 과 대조한다. 다르면 중단한다
- 스냅샷은 덮어쓰지 않는다. 새 스냅샷은 새 파일명으로 만든다
- `integrity.py` 가 기존 단언(3,000행 · 38변수 · fold 1~5 · 배제변수 부재)을 수행한다

비밀번호는 스냅샷 메타에 넣지 않는다(원칙 III). 호스트·DB 이름까지만 남긴다.

### 4.4 산출물 경로와 승격 ★

```
models/
  runs/
    2026-09-02T10-30_a1b2c3/        학습은 항상 여기에만 쓴다
      model_v1.json  uncertainty_v1.json  questions_v1.json
      selection_v1.json  contribution_v1.json  golden_v1.json
      model_v1.joblib
      run.json                       manifest
  v1.0.0/                            승격된 릴리스 — 불변
  current.json                       { "release": "v1.0.0", "promoted_at": "…" }
```

**학습은 최상위 `models/*.json` 과 릴리스 폴더를 건드릴 수 없다.** 쓰기 경로가
`models/runs/<run_id>/` 하나뿐이다.

교체는 `promote` 명령만 할 수 있고, 다음을 한 묶음으로 처리한다.

1. 아티팩트 스키마 검증 (`artifacts/validate.py`)
2. `golden_v1.json` 존재 확인 — 없으면 생성
3. 골든 케이스 대조 — 추론 엔진이 기대 확률과 1e-9 이내로 일치하는지
4. 성공 기준 확인 — `run.json` 의 SC-004·SC-005·SC-016 이 모두 통과
5. 릴리스 디렉터리 생성 (이미 있으면 거부)
6. `current.json` 갱신

**하나라도 실패하면 아무것도 바꾸지 않는다.**

> **`parity_v1.json` → `golden_v1.json` 개명** — TS 이식본이 사라지면 "패리티(두 구현
> 대조)"라는 이름이 맞지 않는다. 내용과 형식은 그대로 쓰되 이름만 바꾼다.
> 기존 `parity_v1.json` 은 v1.0.0 릴리스 안에 그대로 남겨 이력을 보존한다.

### 4.5 run manifest — `run.json`

```json
{ "run_id": "2026-09-02T10-30_a1b2c3",
  "started_at": "…", "finished_at": "…",
  "git": { "sha": "aebcbd0", "dirty": false },
  "snapshot": { "path": "data/snapshots/cb_dataset_2026-09-01.csv.gz",
                "sha256": "…", "rows": 3000 },
  "seed": 42,
  "versions": { "python": "3.9.6", "sklearn": "1.6.1", "numpy": "2.0.2", "cb_burden": "0.1.0" },
  "stages": [ { "name": "baseline", "duration_s": 12.4, "metrics": { … } } ],
  "artifacts": { "model_v1.json": "sha256:…", "model_v1.joblib": "sha256:…" },
  "success_criteria": { "SC-004": true, "SC-005": true, "SC-016": true },
  "model_version": "v1.0.1", "question_set_version": "qs-v1.0.1" }
```

`git.dirty` 가 참이면 승격을 **경고와 함께** 허용한다. 막지는 않되 릴리스에 사실이 남는다.

### 4.6 부작용 통제

- **학습 단계는 DB에 쓰지 않는다.** 읽지도 않는다(스냅샷만 본다)
- DB 기록은 `record` 명령 하나에만 둔다
- `record` 는 `--model-version` 을 **필수 인자**로 받는다. 생략하면 실행이 거부된다
- `record` 는 대상 행이 이미 있고 `--force` 가 없으면 거부한다

3.2의 덮어쓰기 사고가 재발할 수 없다.

### 4.7 아티팩트 검증 — 누가 무엇을 보는가

TS 추론이 사라지면 백엔드는 모델 파일을 읽지 않는다. **검증 주체가 옮겨간다.**

| 검사 | 전 | 후 |
|---|---|---|
| features 순서 = 선별 결과 | 백엔드 기동 | **파이썬 기동** |
| 문항 순서 = 모델 | 백엔드 기동 | **파이썬 기동** |
| DB 활성 문항 = 모델 | 백엔드 기동 | **백엔드 기동** (유지) |
| 스키마·자료형·범위 | 없음 | **파이썬 기동 + `verify`** |
| 척도 방향(1=최고부담) | 없음 | **파이썬 기동 + `verify`** |
| 임계값 범위 | 없음 | **`verify`** |
| 골든 케이스 일치 | 백엔드 parity 테스트 | **`promote` + pytest** |
| **문항 집합 버전 일치** | 없음 | **백엔드 기동 시 `/health` 대조** ★ |

마지막 줄이 3.8을 막는 장치다. 아래 4.9.5 참조.

### 4.8 CLI

```bash
python -m cb_burden snapshot --out data/snapshots/cb_dataset_2026-09-01.csv.gz
python -m cb_burden train    --snapshot <path> --model-version v1.0.1
python -m cb_burden evaluate models/runs/<run_id>          # test 602건 — 1회만
python -m cb_burden golden   models/runs/<run_id>
python -m cb_burden verify   models/runs/<run_id>
python -m cb_burden promote  models/runs/<run_id> --as v1.0.1
python -m cb_burden record   --release v1.0.1 --model-version v1.0.1
python -m cb_burden.serve    --release models/v1.0.0     # 유닉스 소켓
```

`train` 은 baseline → select → calibrate → export 까지만 돌린다. `--stage` 로 하나만
돌릴 수도 있다. **`train` 은 승격하지 않는다.**

**`evaluate` 를 `train` 에서 분리하는 이유** — test 602건은 모든 결정이 끝난 뒤 한 번만
쓴다(`ml/README.md`, SC-004·SC-005 의 최종 근거). `train` 이 매번 test 를 건드리면 실험을
반복할수록 test 가 오염된다. 별도 명령으로 명시적으로만 실행하고, `run.json` 에 이미 평가
기록이 있으면 `--force` 없이는 다시 돌리지 않는다.

---

## 4.9 추론 서비스

### 4.9.1 책임 분담

```
[Vue :9503] ── [Node 백엔드 :9523] ──유닉스 소켓──▶ [파이썬 추론]
                        │                     run/cb-inference.sock · joblib 로드
                        └─ MariaDB                 확률·구간·기여도·희소성
```

**파이썬이 내는 것** — 모델에 종속된 모든 계산

| 항목 | 설명 |
|---|---|
| `proba[5]` | 클래스 확률 |
| `decided` · `internalLabel` | 결정 가중치를 적용한 구간 (판정 불가면 null) |
| `maxProba` · `rarity` | 판정 불가 판단 근거값 |
| `undecidableReason` | `sparse` · `ambiguous` · `null` |
| `contributions` | `[{feature, value, contrib, isMinor}]` — 판정 불가면 null |
| `modelVersion` · `questionSetVersion` | 대조용 |

**Node 가 하는 것** — 설정과 DB가 필요한 모든 것

표시 명칭(`burden.labels`) · 안내 문구 · 기여 요인 문장 조립 · 참조 집단 비교 ·
2인 이상 보정 안내 · 기관 연계 · 이벤트/학습 응답 저장 · **내부 라벨 제거**(FR-010a).

### 4.9.2 판정 정책은 Node 가 소유한다 ★

임계값과 결정 가중치를 파이썬이 갖게 되면 **FR-009c(설정으로 코드 수정 없이 조정)와
충돌한다.** 그래서 Node 가 요청에 실어 보낸다.

```jsonc
POST /predict
{ "answers": [ { "questionNo": 1, "value": 4 }, … ],
  "policy": { "tauConf": 0.3239, "tauDens": -2.4343,
              "decisionWeights": [1.1, 1.1, 1.0, 1.0, 1.0],
              "contributionMinThreshold": 0.1325 } }
```

파이썬은 **상태 없는 계산기**가 된다. 얻는 것이 셋이다.

- 설정 소유권이 `cb_config_v1` 에 남아 FR-009c 가 성립한다
- 설정을 바꿔도 **파이썬을 재기동할 필요가 없다**
- 파이썬에 DB 의존이 생기지 않는다 (4.3의 "추론도 DB를 열지 않는다"와 일관)

`policy` 는 필수 필드다. 빠지면 422 로 거절한다 — 기본값을 두면 조용히 다른 기준으로
판정하게 된다.

**결정 가중치도 설정으로 옮긴다.** 지금은 `model_v1.json` 이 갖고 있으나 그것은 정책이지
학습 산출물이 아니다. `cb_config_v1` 에 `model.decisionWeights` 키를 새로 두고, 학습
산출물의 값과 갈라지면 기동 시 경고한다(4.9.5).

### 4.9.3 응답

```jsonc
200 OK
{ "modelVersion": "v1.0.0", "questionSetVersion": "qs-v1.0.0",
  "proba": [0.019, 0.208, 0.429, 0.288, 0.056],
  "decided": true, "internalLabel": 3,
  "maxProba": 0.429, "rarity": -1.138,
  "undecidableReason": null,
  "contributions": [ { "feature": "help_needed_hours", "value": 5,
                       "contrib": -0.412, "isMinor": false }, … ] }
```

### 4.9.4 장애 처리

Node 가 **타임아웃 2초 + 1회 재시도**. 그래도 실패하면 예외를 삼키지 않고 결과에 표시한다.

```jsonc
{ "decided": false, "unavailable": true,
  "burdenLabel": null, "contributions": null, "comparison": null,
  "undecidableNotice": null,
  "unavailableNotice": "지금은 진단 결과를 드릴 수 없습니다. …",
  "immediateReferral": { … } }          ← 기관 안내는 그대로 제공
```

`buildReferral` 은 이미 판정 없이 동작하므로(판정 불가 경로) 새로 만들 것이 거의 없다.
문구는 `cb_config_v1` 의 새 키 `notice.inferenceUnavailable` 로 둔다(FR-022).

> **프론트도 함께 바뀐다.** `ResultPage.vue` 에 `unavailable` 분기가 필요하다.
> 오늘 오전 사고(3.8)가 정확히 이 종류였으므로 **프론트·백엔드를 같은 배포로 올린다.**

### 4.9.5 버전 불일치 차단 ★

```
GET /health → { "status": "ok", "modelVersion": "v1.0.0",
                "questionSetVersion": "qs-v1.0.0", "release": "models/v1.0.0",
                "artifactDecisionWeights": [1.1, 1.1, 1.0, 1.0, 1.0] }
```

**백엔드가 기동할 때 `/health` 를 호출해 자기 `questions_v1.json` 의
`question_set_version` 과 대조한다. 다르면 뜨지 않는다.**

프로세스가 하나 늘어나는 만큼 어긋날 지점도 하나 는다. 3.8 의 사고를 기동 시점에 잡는다.

파이썬이 안 떠 있으면 백엔드는 **경고를 남기고 기동한다** — 진단만 불가하고 문항 조회·
기관 안내는 계속 돌아야 하기 때문이다. 대조는 파이썬이 붙는 첫 요청에서 다시 한다.

`artifactDecisionWeights` 도 함께 낸다. 결정 가중치가 설정으로 옮겨오면 **설정과 학습
산출물이 갈라질 수 있다** — 2026-09-01 임계값 사고와 같은 유형이다. 문항 집합과 달리
이쪽은 **경고만 하고 막지 않는다.** 설정으로 조정하는 것이 정당한 경우가 있기 때문이다(FR-022).

### 4.9.6 운영

| 항목 | 값 |
|---|---|
| **통신 방식** | **유닉스 도메인 소켓** `run/cb-inference.sock` — **포트를 쓰지 않는다** |
| 왜 | 팀에 배정된 포트가 프론트(9503)·백엔드(9523) 둘뿐이다. 소켓은 파일이라 포트를 소비하지 않고, 네트워크에 아예 열리지 않아 외부에서 닿을 수 없다 |
| 기동 순서 | 파이썬 → Node |
| 기동 명령 | `python3 -m cb_burden.serve --release models/v1.0.0` |
| 릴리스 지정 | `CB_MODELS_DIR` 또는 `--release` |
| sklearn 버전 | `requirements.txt` 에 고정. 로드 실패 시 기동 실패(fail fast) |

파이썬 서비스는 **개인정보를 받지 않는다.** 문항 응답과 정책 값만 받는다. 로그에 요청
본문을 남기지 않는다(원칙 III).

---

## 5. 테스트 전략

`ml/tests/` 를 pytest 로 채운다. **모두 DB 없이 돌아간다.**

| 테스트 | 확인하는 것 |
|---|---|
| `test_stages_smoke` | 합성 스냅샷 300행으로 baseline→select→calibrate→export 가 끝까지 돈다 |
| `test_artifacts_validate` | 검증기가 정상 아티팩트를 통과시키고 키 누락·자료형·범위 오류를 잡는다 |
| `test_artifacts_validate` (척도 항목) | 1이 최고부담이라는 방향이 뒤집히면 실패한다 — **가장 실수하기 쉬운 지점** |
| `test_promote_rules` | 골든 없음·성공기준 미달·릴리스 중복이면 승격이 거부되고 아무것도 바뀌지 않는다 |
| `test_snapshot_hash` | 스냅샷이 변조되면 학습이 중단된다 |
| `test_record_guard` | `--model-version` 없이 `record` 하면 거부된다 |
| `test_golden_build` · `test_engine_golden` | 골든 케이스를 만들고, 추론 엔진이 3,000건과 1e-9 이내로 일치한다 |
| `test_serve_api` | `policy` 누락 422 · 문항 수 불일치 422 · 정상 요청 200 · `/health` 필드 |

백엔드 쪽에도 하나 둔다.

| 테스트 | 확인하는 것 |
|---|---|
| `backend/tests/unit/inferenceClient.test.ts` | 타임아웃·5xx·스키마 위반 시 `unavailable` 응답이 되고 기관 안내가 남는지 |

합성 스냅샷은 **실제 데이터가 아니다.** 분포를 흉내 낸 300행을 생성해 커밋한다
(개인정보 없음, 원칙 III).

---

## 6. 이관 계획

두 덩어리를 **따로** 옮긴다. 섞으면 무엇이 깨졌는지 알 수 없다.

### 6단계 A — 학습 라이브러리 (서비스 무영향)

기존 `ml/train.py` 를 지우지 않는다. 새 패키지가 같은 결과를 낸다는 것을 확인한 뒤에 교체한다.

**합격 기준**

1. 같은 스냅샷으로 `cb_burden train` 을 돌린 결과가 현재 `models/v1.0.0/` 과 **의미상
   동일** — `features` 순서 동일, `tau_conf`·`tau_dens` 1e-9 이내, 계수 1e-9 이내
2. `pytest ml/tests` 전부 통과
3. `verify` 가 현재 v1.0.0 릴리스를 통과시킨다

1번이 미세하게 어긋나면(라이브러리 버전 차이 등) **그 차이를 문서로 설명한 뒤에만**
진행한다. 조용히 넘어가지 않는다.

### 6단계 B — 추론 서비스 (서비스 영향 있음)

**롤백 가능한 순서로 간다.**

| 단계 | 내용 | 되돌리기 |
|---|---|---|
| B1 | 파이썬 `serve` 신설 + 골든 테스트 통과. **Node 는 아직 안 바꾼다** | 프로세스만 끄면 됨 |
| B2 | TS 와 파이썬을 3,000건으로 대조 — 완전히 같은 답인지 | — |
| B3 | Node 를 HTTP 호출로 전환. **`CB_INFERENCE=ts\|http` 로 되돌릴 수 있게** | 환경변수 하나 |
| B4 | 프론트 `unavailable` 분기 추가. **B3 와 같은 배포로 올린다** | 함께 되돌림 |
| B5 | 안정화 후 TS 추론·parity 테스트 제거 | **되돌리기 어려움** |

**B5 전에 한 번 더 확인받는다.** B4까지는 환경변수로 즉시 복구할 수 있다.

교체가 끝나면 `train.py` 는 `ml/legacy/` 로 옮기고 한 릴리스 뒤에 지운다.

---

## 7. 범위 밖 (YAGNI)

- MLflow·DVC 등 실험추적 도구
- `care_burden` 이외의 target 지원
- 발표 자료 스크립트(`make_charts.py`·`make_map.py`·`make_pptx.py`) 이관 — 그대로 둔다
- `SJH-model-benchmark.py` 등 팀원 개인 실험 스크립트
- 추론 서비스의 수평 확장·큐·캐시 — 트래픽이 그 수준이 아니다
- 파이썬 서비스의 외부 노출 — 소켓이라 애초에 불가능하다

---

## 8. 위험과 완화

| 위험 | 완화 |
|---|---|
| **운영 프로세스가 3개로 늘어난다** | 4.9.5 `/health` 대조로 버전 불일치를 기동 시점에 차단. 기동 순서를 문서와 스크립트로 고정 |
| **진단 장애점이 새로 생긴다** | 4.9.4 — 실패해도 기관 안내는 계속. 이용자에게 정직하게 알린다 |
| pickle 이 sklearn 버전에 결합된다 | `requirements.txt` 버전 고정 + 기동 시 로드 실패면 뜨지 않음. JSON 아티팩트도 계속 생성해 최후 수단으로 남긴다 |
| 재학습 결과가 지금과 미세하게 달라짐 | 6단계 A 합격 기준 1번. 다르면 원인을 밝히고 문서화 |
| 내부 HTTP 지연 | 로컬 호출 1~5ms. 진단 1회당 한 번뿐이라 무시 가능 |
| 스냅샷 파일이 저장소를 무겁게 함 | gzip csv. 3,000행 × 40열이면 수백 KB |
| 다른 팀원이 같은 폴더에서 동시에 학습 | run 디렉터리가 `run_id` 로 갈려 충돌하지 않는다. 승격만 직렬 |
| 발표 일정 압박 | **6단계 A 만으로도 독립적인 가치가 있다.** B는 발표 뒤로 미룰 수 있다 |

---

## 9. 확정한 세부 결정

| 항목 | 결정 | 이유 |
|---|---|---|
| 스냅샷 형식 | **`csv.gz`** | parquet 은 `pyarrow` 의존을 더한다. 3,000행 × 40열이면 gzip csv 로 수백 KB, 표준 라이브러리와 numpy 만으로 읽힌다 |
| 배포본 지시 | **`current.json` + `CB_MODELS_DIR`** | 심볼릭 링크는 git 에서 다루기 번거롭다 |
| 설치 방식 | **벤더링 유지 + `pyproject.toml`** | `pip install --target ml/.pylibs` 는 Docker 금지(원칙 V) 아래 이미 쓰는 방식 |
| 환경변수 이름 | **`CB_MODELS_DIR` 로 통일** | 학습(`MODELS_DIR`)과 백엔드(`CB_MODELS_DIR`)가 갈라져 있었다 |
| 프레임워크 | **FastAPI + uvicorn** | 요청·응답 스키마 검증을 경계에서 강제 |
| 통신 | **유닉스 소켓** `run/cb-inference.sock` | 팀 배정 포트가 둘뿐이다. 포트를 소비하지 않고 외부 노출도 불가능하다 |
| 골든 파일 이름 | **`golden_v1.json`** | TS 이식본이 사라지면 "parity"가 뜻을 잃는다 |
| JSON 아티팩트 | **계속 생성한다** | pickle 이 깨졌을 때의 최후 수단이자 사람이 읽을 수 있는 기록 |

---

## 10. 영향 범위

이 설계가 건드리는 것을 빠짐없이 적는다.

| 대상 | 영향 |
|---|---|
| `ml/train.py` | `cb_burden` 으로 이관 후 `ml/legacy/` 로 이동 |
| `ml/db.py` · `saabas.py` · `questions.py` · `parity.py` | 패키지 안으로 이동·분해 |
| `backend/src/inference/*.ts` | **B5에서 제거** (predictor · undecidable · saabas 이식본) |
| `backend/src/inference/modelLoader.ts` | 모델 로드 제거. 문항 로드와 DB 문항 대조는 유지 |
| `backend/src/services/diagnosisService.ts` | 직접 계산 → HTTP 호출. 구조는 유지 |
| `backend/tests/parity/` | **B5에서 제거** — 역할이 `ml/tests/test_engine_golden.py` 로 이동 |
| `backend/src/server.ts` | 기동 시 `/health` 대조 추가 |
| `frontend/src/pages/ResultPage.vue` | `unavailable` 분기 추가 |
| `specs/.../openapi.yaml` | `unavailable` · `unavailableNotice` 필드 추가 |
| `db/seeds/config.js` | `notice.inferenceUnavailable` 키 추가 → **시드 재실행 필요** |
| `deploy/nginx-*.conf` | **변경 없음** (소켓이라 노출 대상 자체가 없다) |
| `CLAUDE.md` | 명령 절에 파이썬 서비스 기동 추가 |
| 운영 절차 | 기동 순서(파이썬 → Node), 재기동 대상 3개 |

---

## 부록 — 이 설계가 막는 사고

| 확인된 사고 | 막는 장치 |
|---|---|
| 배포본이 실험 모델로 바뀜 (09-01 14:21~15:10) | 4.4 — 학습이 릴리스 경로에 쓸 수 없다 |
| v1.0.0 성능 기록이 14문항 결과로 덮임 | 4.6 — `--model-version` 필수, 중복 시 거부 |
| parity 없는 모델이 배포 후보로 보임 | 4.4 — 골든 없으면 승격 거부 |
| DB가 바뀌면 과거 모델 재현 불가 | 4.3 — 스냅샷 해시 고정 |
| 척도 방향 실수 | 5장 — 회귀 테스트 |
| 구성요소 버전이 어긋난 채 조용히 돔 (09-02 오전) | 4.9.5 — `/health` 대조, 다르면 기동 실패 |
| 모델 계열을 바꾸려면 두 번 구현 | 4.9 — 학습한 객체를 서비스가 그대로 쓴다 |
