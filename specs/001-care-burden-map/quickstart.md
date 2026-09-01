# Quickstart — 돌봄부담 경량 진단 및 지도 기반 복지서비스 안내

**Branch**: `001-care-burden-map` | **Date**: 2026-09-01

**Docker를 사용하지 않는다**(Constitution 원칙 V, NON-NEGOTIABLE). 모든 구성 요소는 프로젝트
폴더 안의 코드와 선언적 설정으로 전개하며, DB는 애플리케이션 드라이버로 직접 붙는다.

---

## 0. 사전 요구

| 도구 | 버전 | 용도 |
|---|---|---|
| Node.js | 20 LTS | 백엔드·프론트엔드 |
| npm | 10+ | 패키지 관리 |
| Python | 3.11+ | **오프라인 학습 전용** (런타임에는 쓰지 않는다) |

`mysql` 클라이언트 바이너리는 필요 없다. 애플리케이션이 `mysql2` 드라이버로 직접 접속한다.

---

## 1. 자격증명 설정

접속 정보는 **파일에 적지 않고 `.env`로 넘긴다.** 저장소 루트에 `.env.example`이 이미 있다.

```bash
cp .env.example .env
# .env 를 열어 실제 값을 채운다. .env 는 .gitignore 로 제외되어 있다.
```

```bash
DB_HOST=<팀 DB 호스트>
DB_PORT=13306
DB_USER=<사용자>
DB_PASSWORD=<비밀번호>
DB_NAME=ABC8pioneer3
DB_CHARSET=utf8mb4
```

> **주의** — `Intent-Plan.md`와 `notebooks/eda-학습데이터셋_최종.ipynb`에는 접속 정보가 평문
> 기본값으로 남아 있다. 새 코드는 이 값을 복사하지 말고 반드시 `.env`에서 읽는다.
> 저장소를 공개로 전환하기 전에 두 파일을 정리해야 한다.

---

## 2. 폴더 구성

```bash
project2608/
├── backend/      # Node 20 + Express + TypeScript
├── frontend/     # Vue 3 + TypeScript + Vite + Pinia
├── ml/           # Python 오프라인 학습 파이프라인 (배포되지 않음)
├── models/       # 학습 산출 아티팩트 (JSON, 버전 고정)
├── db/           # 스키마 DDL · 적재 스크립트
└── notebooks/    # 기존 EDA
```

---

## 3. 데이터베이스 준비

학습 데이터(`cb_dataset_v1` 등)는 **이미 적재되어 있고 변경하지 않는다.**
신규로 만드는 것은 운영 기준 테이블과 관측 테이블뿐이다(data-model.md 3·4장).

```bash
cd db
npm install
npm run migrate          # cb_region_v1, cb_facility_v1, ... 생성
npm run seed:regions     # 행정표준코드 229개 시군구 적재
npm run seed:facilities  # services_with_coords_std09 → 정규화 테이블 적재
npm run seed:reference   # cb_reference_dist_v1 (셀 30건 미만 자동 제외)
```

**적재 후 확인할 것** — 아래 값이 나와야 한다. 다르면 원천 데이터가 바뀐 것이므로
`research.md` 0장의 실측표를 갱신하고 영향을 다시 판단한다.

| 확인 | 기대값 | 비고 |
|---|---|---|
| `cb_region_v1` 행 수 | 229 | |
| `hasFacilityData = true` | 221 (96.5%) | 미확보 8개 |
| `cb_facility_v1` 행 수 | **875** | 원천 1,283행을 기관 단위로 묶은 결과 |
| `cb_facility_service_v1` 행 수 | **1,277** | 875 + 두 유형 모두 제공 402 |
| `phone IS NULL` | **40** | 기관 단위 기준 |
| 좌표 결측 | 0 | |
| `DAY_ACTIVITY` / `AFTERSCHOOL_YOUTH` | **724 / 553** | 기관 단위 기준 |

**원천 1,283행 → 기관 875건이 되는 이유** — 같은 기관이 두 유형을 모두 제공하는 경우가 402건이라
기관 1행 + 서비스 2행으로 나뉜다(research.md R-8). 여기에 이름·좌표·유형·사업명·전화가 모두 같은
완전 중복 6행이 합쳐져 서비스 행이 1,283 − 6 = 1,277이 된다. spec.md가 말하는 "1,283건"은
**원천 행 수**이고, 위 표는 **정규화 후 기관 수**다. 둘 다 맞는 값이며 세는 단위가 다르다.

---

## 4. 모델 학습 (오프라인 · Python)

**런타임에는 Python이 없다.** 이 단계는 개발자가 손으로 돌려 `models/`에 아티팩트를 만드는
과정이며, 산출물만 배포에 실린다(research.md R-2).

```bash
cd ml
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt      # pandas, scikit-learn, lightgbm, shap, pymysql

python -m ml.train --stage baseline      # 38변수 기준 모델 → B_f1, B_rec 확정
python -m ml.train --stage select        # 후진 제거로 최소 문항 집합 k 도출 (FR-004c)
python -m ml.train --stage calibrate     # 확률 보정 → 판정 불가 임계값 τ 산출 (FR-009b)
python -m ml.train --stage export        # models/*.json 생성
python -m ml.evaluate --use-test         # test 602건 1회 평가 (SC-004·SC-005) ← 마지막에 단 한 번
```

**순서를 지켜야 하는 이유**

- `select`와 `calibrate`는 `cb_dataset_v1.cv_fold`에 고정된 5-fold만 쓴다. test를 섞으면
  SC-004·SC-005가 낙관 편향된다.
- `evaluate --use-test`는 **모든 결정이 끝난 뒤 단 한 번** 실행한다. 결과가 나쁘다고 앞 단계로
  돌아가 재조정하면 test가 오염되어 더 이상 최종 평가로 쓸 수 없다.
- 임계값이 나쁘면 배제 6변수를 되살리는 방식은 쓰지 않는다(FR-004b, spec Risks).

**산출물 검증**

```bash
python -m ml.parity --dataset all        # 3,000건을 Python 추론기에 통과시켜 기준값 생성
cd ../backend && npm run test:parity     # TS 추론기 결과와 1e-9 이내 일치 확인
```

패리티 테스트가 실패하면 **배포하지 않는다.** 학습기와 추론기가 다른 답을 내는 상태이므로,
원칙 IV(재현성)가 성립하지 않는다.

---

## 5. 백엔드 실행

```bash
cd backend
npm install
npm run dev              # http://localhost:3000
```

기동 시 다음을 검증하고 하나라도 어긋나면 **기동을 실패시킨다**(fail fast).

1. `models/model_v1.json`의 `features` 순서가 `selection_v1.json`과 일치하는가
2. 활성 문항 집합(`cb_question_v1`)의 `feature` 목록이 모델 `features`와 일치하는가
3. `cb_config_v1`에 FR-022가 요구하는 설정 키가 모두 존재하는가

조용히 잘못된 판정을 내는 것보다 뜨지 않는 편이 낫다(원칙 II의 같은 취지).

---

## 6. 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev              # http://localhost:5173
```

**지도 발급 키가 필요 없다.** Leaflet + OpenStreetMap 을 쓰므로 별도 설정 없이 지도가 뜬다
(research.md R-7, JSG-01 반영).

```bash
# frontend/.env.local — 기본값으로 충분해 보통 만들지 않아도 된다
VITE_API_BASE=/api/v1
```

타일 서버(OSM)를 못 받는 상황에서도 **목록 경로는 동작해야 한다.** 지도는 표현 계층에만 있고
데이터 경로가 분리되어 있기 때문이다. 이 동작이 곧 "지도 표시 수단을 쓸 수 없는 상황"의
목록 대체 경로다.

---

## 7. 테스트

```bash
cd backend  && npm test              # 단위 + 계약
cd frontend && npm test              # 단위
npm run test:e2e                     # Playwright — 전 흐름 + 키보드 조작(FR-039)
cd ml && pytest                      # 선별 재현성 · 지표 산출
```

### 반드시 통과해야 하는 회귀 테스트

역방향 척도(1=최고부담)는 이 프로젝트에서 가장 실수하기 쉬운 지점이라 헌법이 별도로 못박고 있다.
아래를 **내부 라벨 1~5 전부에 대해** 검증한다.

| 내부 라벨 | 표시 명칭 | 경고 표시 | 즉시 안내 | 상담 강조 |
|---|---|---|---|---|
| 1 | 최고부담군 | O | O | O |
| 2 | 고부담군 | O | O | X |
| 3 | 중간부담군 | X | X | X |
| 4 | 저부담군 | X | X | X |
| 5 | 부담 없음 | X | X | X |
| 판정 불가 | (표시 안 함) | X | **O** | O |

마지막 행이 핵심이다 — 판정 불가는 구간을 표시하지 않으면서 즉시 안내는 제공하고,
문구로 고부담 판정과 구분해야 한다(FR-009a, FR-021j, FR-021j-1).

### 개인정보 회귀 테스트

| 검증 | 방법 |
|---|---|
| 익명 로그에 응답·별명·IP·좌표가 없다 | `cb_event_log_v1` 스키마 + 삽입 경로 단위 테스트 |
| 학습 저장소에 `session_id`가 없다 | 스키마 검증 — 두 테이블의 공통 컬럼 집합이 공집합인지 확인 |
| 미동의 시 학습 저장이 0건이다 | 통합 테스트: `consentTraining=false` 제출 후 행 수 불변 |
| 별명이 서버로 전송되지 않는다 | 프론트 단위 테스트 — 요청 본문에 별명 필드 부재 |
| 참조 비교에 30건 미만 셀이 없다 | `SELECT MIN(n) FROM cb_reference_dist_v1` ≥ 30 |

---

## 8. 배포 (컨테이너 없음)

```bash
cd frontend && npm run build     # → frontend/dist
cd ../backend && npm run build   # → backend/dist
```

- Nginx가 `frontend/dist`를 정적 서빙하고 `/api`를 백엔드로 리버스 프록시한다.
- 백엔드는 Node 프로세스로 직접 기동한다(`node dist/server.js`). 프로세스 관리는
  systemd 유닛 파일 등 선언적 설정으로 두며, 컨테이너를 쓰지 않는다.
- `models/*.json`은 백엔드 빌드 산출물과 함께 배포한다.

### 배포 전 필수 조치 — 접근 로그의 IP 제거

FR-028과 원칙 III는 원본 IP를 어떤 저장소에도 남기지 못하게 한다.
**애플리케이션 코드만으로는 부족하다** — Nginx와 Express의 기본 접근 로그가 IP를 남긴다.

- Nginx `log_format`에서 `$remote_addr`를 제거하거나 익명화한다.
- Express의 요청 로거에서 IP 필드를 비활성화한다.
- 제출자 구분용 해시(FR-036)를 만드는 시점에만 메모리에서 IP를 쓰고 즉시 버린다.

이 조치가 빠지면 코드가 아무리 깨끗해도 원칙 III를 위반한다.
