---
description: "Task list for 돌봄부담 경량 진단 및 지도 기반 복지서비스 안내"
---

# Tasks: 돌봄부담 경량 진단 및 지도 기반 복지서비스 안내

**Input**: `/Users/pioneer3/project2608/specs/001-care-burden-map/`
(spec.md · plan.md · research.md · data-model.md · contracts/openapi.yaml · quickstart.md)

**참조**: `Intent-Tasks.md`(디자인 템플릿) · `.specify/memory/constitution.md` v1.0.0

**Tests**: 포함한다. `research.md` R-11이 테스트 전략을 정의하고, `quickstart.md` 7장이 패리티·척도
방향·개인정보 회귀 테스트를 **릴리스 게이트**로 명시했기 때문이다. 헌법의 품질 게이트도 이를 요구한다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 실행 가능 (서로 다른 파일, 의존 없음)
- **[Story]**: US1(진단·P1) · US2(지도·P2) · US3(즉시 연계·P3)
- 모든 경로는 저장소 루트 `/Users/pioneer3/project2608/` 기준

## Path Conventions

`plan.md`의 구조를 따른다 — `backend/src/`, `frontend/src/`, `ml/`, `models/`, `db/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 프로젝트 초기화와 디자인 템플릿 확정

- [X] **T001** `plan.md` 구조대로 최상위 폴더 생성 — `backend/` `frontend/` `ml/` `models/` `db/`.
      `.gitignore`에 `models/*.pkl`, `ml/.venv/`, `**/node_modules/`, `**/dist/` 추가
- [X] **T002** [P] `backend/` 초기화 — `npm init`, TypeScript 5, Express 4, mysql2 3, tsx,
      `tsconfig.json`(strict), `vitest.config.ts`
- [X] **T003** [P] `frontend/` 초기화 — Vite 5 + Vue 3.4 + TS, Pinia 2, vue-router 4,
      Vitest + @vue/test-utils, Playwright
- [X] **T004** [P] `ml/` 초기화 — `requirements.txt`(pandas, numpy, scikit-learn, lightgbm, shap,
      pymysql, pytest), `pyproject.toml`, `ml/__init__.py`
- [X] **T005** [P] `db/` 초기화 — mysql2 기반 마이그레이션 러너와 `db/package.json` 스크립트
      (`migrate`, `seed:regions`, `seed:facilities`, `seed:reference`)
- [ ] **T006** [P] ESLint + Prettier 공유 설정을 루트에 두고 `backend`·`frontend`에서 상속
- [X] **T007** **디자인 템플릿 적용** — 저장소 루트에서 `npx getdesign@latest add airbnb` 실행.
      생성된 `DESIGN.md`를 커밋하고, 이 문서를 프로젝트 전반의 단일 디자인 기준으로 삼는다
      (`Intent-Tasks.md` 지시 · 헌법 "기술 및 데이터 제약 > 디자인")
- [X] **T008** [P] `DESIGN.md`의 색·타이포·간격·컴포넌트 규칙을 CSS 커스텀 속성으로 옮겨
      `frontend/src/assets/tokens.css` 작성. **부담 구간 색은 여기서 정의하지 않는다** —
      색 단독 전달 금지(FR-041)를 지키려면 명칭 텍스트와 함께 컴포넌트에서 다룬다
- [X] **T009** [P] `.env` 로딩과 스키마 검증 — `backend/src/config/env.ts`와 `ml/config.py`.
      값이 없으면 기동 실패. **접속 정보를 코드에 하드코딩하지 않는다**(quickstart 1장)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 모든 User Story가 공유하는 스키마·서버 골격·관측 경로

**⚠️ CRITICAL**: 이 단계가 끝나기 전에는 어떤 User Story도 시작할 수 없다

### 스키마 (data-model.md 3·4장)

- [X] **T010** [P] `db/migrations/001_region_facility.sql` — `cb_region_v1`,
      `cb_facility_v1`(INDEX `(lat,lng)`, `(region_code)`), `cb_facility_service_v1`,
      `cb_facility_report_v1`
- [X] **T011** [P] `db/migrations/002_operational.sql` — `cb_question_v1`, `cb_config_v1`,
      `cb_model_version_v1`, `cb_reference_dist_v1`(**`CHECK (n >= 30)`**), `cb_salt_v1`
- [X] **T012** [P] `db/migrations/003_observability.sql` — `cb_event_log_v1`,
      `cb_training_response_v1`. **두 테이블은 공통 컬럼을 하나도 두지 않는다**(FR-032).
      `cb_event_log_v1`에 응답·별명·IP·좌표 컬럼을, `cb_training_response_v1`에 `session_id`를
      만들지 않는다
- [X] **T013** `db/tests/separation.test.ts` — 두 관측 테이블의 컬럼 집합 교집합이 공집합인지
      검증. **조인 키가 존재하지 않음을 스키마로 증명하는 테스트**(FR-032, 원칙 III)
- [X] **T014** [P] `db/seeds/regions.ts` — 행정표준코드 기준 **229개 시군구** 적재.
      `center_lat`/`center_lng`(지역 직접 선택 시 기준 좌표) 포함. 적재 후 행 수 229 확인
- [X] **T015** [P] `db/seeds/config.ts` — `cb_config_v1`에 FR-022의 설정 키 14종 기본값 적재.
      이 시점에는 모델이 없으므로 `undecidable.thresholds`·`contribution.minThreshold`는
      **자리표시값**이다. 학습이 끝난 뒤 **T029a에서 반드시 재실행**해 실제 산출값으로 덮는다
      (`referral.*`, `age.*`, `undecidable.*`, `selfreport.*`, `contribution.*`, `draft.*`,
      `submit.*`, `burden.labels`). data-model.md 3.6 표 참조

### 백엔드 골격

- [X] **T016** `backend/src/repositories/pool.ts` — mysql2 커넥션 풀과 쿼리 헬퍼
- [X] **T017** `backend/src/server.ts` — Express 앱, 라우터 마운트, 오류 핸들러.
      **요청 로거에서 IP 필드를 비활성화한다**(FR-028, 원칙 III)
- [X] **T018** `backend/src/config/configStore.ts` — `cb_config_v1` 로더와 캐시.
      기동 시 FR-022 필수 키 존재를 검증하고 없으면 **기동 실패**(fail fast)
- [X] **T019** `backend/src/api/meta.ts` — `GET /config`.
      **판정 임계값·판정 불가 기준은 반환하지 않는다**(응답 역산 방지, openapi.yaml 주석)

### 관측 경로 (모든 스토리가 사용)

- [X] **T020** `backend/src/services/eventService.ts` + `backend/src/api/events.ts` —
      `POST /events`. FR-027이 열거한 이벤트 종류와 필드만 저장하고 나머지는 폐기
- [ ] **T021** `backend/tests/unit/eventService.privacy.test.ts` — 응답 내용·별명·IP·좌표·
      사전 입력값을 넣어도 저장되지 않음을 검증(FR-028)

### 프론트엔드 골격

- [X] **T022** `frontend/src/App.vue` + `router/index.ts` + `main.ts` — 레이아웃 셸에
      `tokens.css` 적용
- [X] **T023** [P] `frontend/src/services/apiClient.ts` — `VITE_API_BASE` 기반 fetch 래퍼,
      오류 정규화
- [X] **T024** [P] `frontend/src/stores/eventStore.ts` — 세션 식별자(1회용 UUIDv4) 발급과
      이벤트 전송 큐(FR-029)

**Checkpoint**: 기반 완료 — US1과 US2를 **병렬로** 시작할 수 있다 (US2는 모델에 의존하지 않는다)

---

## Phase 3: User Story 1 - 경량 돌봄부담 진단 (Priority: P1) 🎯 MVP

**Goal**: 보호자가 계정 없이 사전 입력 → 경량 문항 → 동의·자가보고 → 판정 결과(구간·기여 요인·
참조 집단 비교)까지 완주한다.

**Independent Test**: 지도 기능이 전혀 없는 상태에서 진단을 처음부터 끝까지 수행하고,
5구간 판정과 판정 불가가 모두 정상 동작하는지 확인한다. `FR-014`(신청처 이동)와 연령 입력은
P3 범위이므로 이 단계에서는 표시하지 않는다.

### 3-A. 모델 파이프라인 (오프라인 Python)

> `plan.md` "데이터 및 모델 구성 계획"과 `research.md` R-1·R-4·R-5·R-6을 실행한다.
> **test 602건은 T031에서 단 한 번만 사용한다.**

- [X] **T025** `ml/data.py` — `v_cb_tree_v1`·`v_cb_linear_v1` 적재.
      적재 직후 무결성 검증: 3,000행 / train 2,398·test 602 / `cv_fold` 1~5가 train에만
      483·481·478·478·478로 배정 / 배제 6변수 부재. 하나라도 어긋나면 실패시킨다
- [X] **T026** `ml/train.py --stage baseline` — 38변수 **기준 모델**을 트리 계열
      (LightGBM·RandomForest·HistGB)과 선형 계열(다항·순서형 로지스틱) 양쪽으로 5-fold 학습.
      `class_weight='balanced'` 적용, 리샘플링 금지(R-5). 산출: `B_f1`, `B_rec`, 계열 비교표
- [X] **T027** `ml/select.py` — SHAP 전역 중요도 최하위부터 후진 제거.
      정지 조건 `ΔmacroF1 ≤ 0.03 AND Δ고부담재현율 ≤ 0.05 AND 재현율 ≥ 0.70`(SC-004·SC-005)을
      만족하는 **최소 k**. 동률이면 결측률이 낮은 조합. → `models/selection_v1.json`
      (k, 채택 변수, 탈락 순서, 단계별 지표)
- [X] **T028** `ml/calibrate.py` — 확률 보정(isotonic/Platt) 후 `τ_conf`·`τ_dens` 격자 탐색.
      **판정 불가 집단 오분류율 > 판정 집단 오분류율 AND 판정 불가 비율 ≤ 10%**(SC-016)를
      만족하는 조합 중 판정 불가 비율 최저값 채택 → `models/uncertainty_v1.json`
- [X] **T029** `ml/export.py` — `models/model_v1.json`(트리 구조·`base_score`·보정 파라미터·
      `features` 순서·`classes`) 및 `models/questions_v1.json`(문항 번호 ↔ 변수 ↔ 자연어 문장 ↔
      선택지) 생성. `cb_feature_meta_v1.scale_note`를 문항 문구의 근거로 사용한다
- [ ] **T029a** `db/seeds/config.js` **재실행** — T028·T029 산출값을 `cb_config_v1`에 반영한다.
      `uncertainty_v1.json`의 `tau_conf`·`tau_dens` → `undecidable.thresholds`,
      `contribution_v1.json`의 `min_threshold` → `contribution.minThreshold`.
      **시드가 숫자를 손으로 갖지 않고 `models/*.json`에서 직접 읽어야 한다** — 값을 적어두면
      재학습 후 갱신을 잊어 운영값과 모델값이 갈라진다. 반영 후 백엔드를 재기동해
      `configStore` 캐시를 갱신한다(T018)
      ```bash
      cd db && node seeds/config.js && cd .. && ./check_project.sh restart
      ```
- [X] **T030** `ml/parity.py` — 3,000건 전량을 Python 추론기에 통과시켜 클래스 확률·SHAP
      기여도 기준값을 `models/parity_v1.json`에 기록
- [X] **T031** `ml/evaluate.py --use-test` — **test 602건 1회 평가**. macro F1, 고부담 재현율,
      판정 불가 비율을 `cb_model_version_v1`에 기록. 결과가 나빠도 앞 단계로 돌아가지 않으며,
      **배제 6변수를 되살리지 않는다**(FR-004b, spec Risks)
- [ ] **T032** [P] `ml/tests/test_reproducibility.py` — 같은 시드·같은 fold로 재실행 시
      `selection_v1.json`의 k와 채택 변수가 동일한지 검증(원칙 IV)

### 3-B. 런타임 추론 (TypeScript)

- [X] **T033** `backend/src/inference/modelLoader.ts` — `models/*.json` 로드.
      **`model_v1.json.features` 순서가 `selection_v1.json`과, 활성 문항 집합의 `feature`
      목록과 일치하지 않으면 기동 실패**(data-model.md 2장 불변 조건)
- [X] **T034** `backend/src/inference/predictor.ts` — 트리 순회 → 클래스 확률 → 보정 적용.
      결측(“해당사항 없음”)은 `missing_to_left` 규칙으로 처리(FR-004d)
- [X] **T035** `backend/src/inference/treeShap.ts` — TreeSHAP(path-dependent) 구현.
      기여도 합 + `base_score` = 예측값(local accuracy)을 단위 테스트로 검증
- [X] **T036** `backend/src/inference/undecidable.ts` — `max p < τ_conf OR density < τ_dens`
      판단(FR-009a). τ는 `cb_config_v1`에서 읽는다(FR-009c)
- [X] **T037** **패리티 테스트** `backend/tests/parity/inference.parity.test.ts` —
      `models/parity_v1.json`의 3,000건 기준값과 TS 추론 결과가 **1e-9 이내 일치**.
      실패하면 배포 금지(릴리스 게이트, research.md R-2)

### 3-C. 진단 API

- [X] **T038** `db/seeds/questions.ts` — `models/questions_v1.json` → `cb_question_v1` 적재.
      `explain_template` 문구는 **인과가 아닌 동반 관찰 표현**으로 작성한다
      (예: `secondary_caregiver_type` 역설 — research.md R-3)
- [X] **T039** [P] `db/seeds/reference.ts` — `cb_reference_dist_v1` 적재.
      부담 구간 분포와 **개별 문항의 단일 응답 범주**만 넣고, **셀 30건 미만은 제외**한다.
      두 변수를 결합한 행은 만들지 않는다(FR-013c, FR-013c-1)
- [X] **T040** `backend/src/api/questions.ts` — `GET /questions`.
      `totalCount`는 진행률 분모이며 사전 입력 3항목을 포함하지 않는다(FR-002b, FR-005)
- [X] **T041** `backend/src/services/diagnosisService.ts` — 판정 → 기여 요인 → 참조 비교 조립.
      **내부 라벨을 응답에 넣지 않고 `burdenLabel`만 반환**(FR-010a).
      기여 요인은 최소 3개이며 임계값 미만은 `isMinor: true`(FR-011, FR-011-1).
      판정 불가면 `contributions`·`comparison`을 null로 둔다(FR-011c, FR-013d)
- [X] **T042** `backend/src/services/consentService.ts` — `consentTraining`에 따른 분기.
      **false면 `cb_training_response_v1`에 어떤 행도 만들지 않는다**(FR-031, FR-033).
      true면 저장 후 1회용 `cancelToken` 발급
- [X] **T043** `backend/src/services/submitterHash.ts` — `SHA-256(IP + 솔트)`.
      **원본 IP를 로깅·저장하지 않고 메모리에서만 사용**(FR-036). 활성 솔트는 `cb_salt_v1`에서 읽는다
- [X] **T044** `backend/src/api/diagnoses.ts` — `POST /diagnoses`.
      미응답 문항이 있으면 `422` + `unansweredQuestionNos`(FR-007).
      미동의 시 `selfReportLevel` 생략을 허용한다(FR-008e)
- [X] **T045** `backend/src/api/diagnoses.ts` — `DELETE /diagnoses/{cancelToken}`(FR-025).
      존재 여부를 노출하지 않도록 삭제/미존재 모두 `204`
- [X] **T046** [P] `backend/src/api/meta.ts` — `GET /model`(FR-012a, FR-012b)
- [ ] **T047** [P] `backend/tests/contract/us1.contract.test.ts` —
      `contracts/openapi.yaml`의 `/questions`, `/diagnoses`, `/model` 요청·응답 스키마 검증
- [X] **T048** **척도 방향 회귀 테스트** `backend/tests/unit/burdenScale.test.ts` —
      quickstart 7장의 6행 표를 그대로 검증한다. 내부 라벨 1~5와 판정 불가 각각에 대해
      표시 명칭 · 경고 표시 · 즉시 안내 발동 · 상담 강조를 확인.
      **1=최고부담 역방향 척도라 임계값 비교는 `<=`다**(헌법 "척도 방향")
- [ ] **T049** [P] `backend/tests/integration/consent.test.ts` —
      `consentTraining=false` 제출 후 `cb_training_response_v1` 행 수 불변 확인

### 3-D. 진단 화면

- [X] **T050** [P] `frontend/src/pages/HomePage.vue` — 두 메뉴를 **동등한 비중**으로 제시.
      사전 절차 없이 진입(FR-001, FR-002)
- [X] **T051** [P] `frontend/src/stores/preSurveyStore.ts` — 별명은 `sessionStorage`,
      돌봄 대상 수는 메모리. **연령은 P3에서 추가하며 지금은 두지 않는다**(FR-002e는 P3 범위)
- [X] **T052** `frontend/src/stores/surveyStore.ts` — 진행 응답과 위치를 `localStorage`에 저장.
      로드 시 **24시간 경과·제출 완료·"새로 시작"이면 폐기**(FR-008-1, FR-008-2).
      서버로 전송하지 않는다
- [X] **T053** `frontend/src/pages/PreSurveyPage.vue` — 별명(20자, 식별 정보 입력 금지 안내)과
      돌봄 대상 수 구분. **모두 선택 입력이며 건너뛰기 제공**(FR-002a~d, FR-002g, FR-002h)
- [X] **T054** `frontend/src/pages/SurveyPage.vue` — 진행률 표시(FR-005), 이전 문항 이동(FR-006),
      조건부 문항의 **"해당사항 없음" 선택지**(FR-004d). 중간 결과를 표시하지 않는다(FR-011b)
- [X] **T055** `frontend/src/pages/ConsentPage.vue` — 학습 이용 고지·동의(FR-033) →
      **동의한 경우에만** 자가보고 부담 문항 제시(FR-008e).
      문항에 목적 안내 문구를 함께 표시(FR-008d)
- [X] **T056** [P] `frontend/src/components/BurdenResultCard.vue` — 구간 명칭 텍스트를 항상 표시하고
      **색상만으로 구분하지 않는다**(FR-041). 경고는 텍스트를 병기한다(FR-010b, FR-042)
- [X] **T057** [P] `frontend/src/components/ContributionList.vue` — 기여 요인 목록.
      `isMinor`인 항목은 "판정에 일부 영향을 준 요인"으로 구분 표시(FR-011-1)
- [X] **T058** [P] `frontend/src/components/ReferenceComparison.vue` — 참조 집단 비교.
      `comparison`이 null이면 **영역 자체를 표시하지 않는다**(빈 영역·"데이터 없음" 금지)
- [X] **T059** `frontend/src/pages/ResultPage.vue` — 별명 호칭(FR-010c), 구간 설명(FR-010),
      판정 불가 안내(FR-009a·FR-021j-1), 2인 이상 과소 추정 안내(FR-010d, 판정 불가면 미표시
      FR-010f), 참고 정보 고지(FR-013), 저장 취소 경로(FR-025)
- [ ] **T060** `frontend/tests/e2e/us1.spec.ts` — 사전 입력 → 설문 → 동의 → 자가보고 → 결과
      전 흐름. 미응답 제출 거부, 새로고침 후 이어하기, 별명 미복구(의도된 동작) 확인

**Checkpoint**: US1이 독립적으로 완결된다 — 지도 없이 진단만으로 배포·시연 가능 (**MVP**)

---

## Phase 4: User Story 2 - 지도 기반 복지서비스 신청처·연락처 안내 (Priority: P2)

**Goal**: 보호자가 진단을 거치지 않고 지도 메뉴로 바로 들어가 기준 지역의 신청 접수처를
지도와 목록으로 확인하고 연락처·길찾기에 도달한다.

**Independent Test**: 진단 기능을 전혀 쓰지 않고 첫 화면 → 지도 메뉴 → 지역 선택 → 기관 상세 →
통화·길찾기까지 완주한다. **모델 아티팩트가 없어도 동작해야 한다.**

- [X] **T061** `db/seeds/facilities.ts` — `services_with_coords_std09` → `cb_facility_v1` +
      `cb_facility_service_v1` 정규화 적재. 한글 컬럼을 영문 스키마로 매핑,
      사업유형을 `DAY_ACTIVITY`/`AFTERSCHOOL_YOUTH`로 코드화,
      **전화번호 결측·형식 오류는 빈 문자열이 아니라 NULL**(research.md R-8)
- [X] **T062** `db/tests/facilitySeed.test.ts` — 적재 후 quickstart 3장 기대값 검증:
      기관 1,283 / `has_facility_data=true` 221 / `phone IS NULL` 60 / 좌표 결측 0 /
      유형별 727·556. 다르면 원천이 바뀐 것이므로 실패시킨다
- [X] **T063** `backend/src/services/facilityService.ts` — **경계 상자 선필터 후 Haversine 정렬**
      2단계(research.md R-9). 직선거리를 정렬과 표시에 동일하게 사용(FR-021-1)
- [X] **T064** [P] `backend/src/api/regions.ts` — `GET /regions`.
      **229개 전체**를 반환하고 `hasFacilityData`로 확보 여부를 알린다(FR-016a)
- [X] **T065** `backend/src/api/facilities.ts` — `GET /facilities`.
      `lat`/`lng` 또는 `regionCode` 필수, 좌표 우선. 0건이면 `suggestedRadiusKm` 반환(FR-020).
      미확보 지역은 `regionDataPending: true` + `metroContact`(FR-016b)
- [X] **T066** [P] `backend/src/api/facilities.ts` — `GET /facilities/{facilityId}`(FR-017, FR-019)
- [X] **T067** [P] `backend/src/api/facilities.ts` — `POST /facilities/{facilityId}/reports`
      (FR-019b). **신고자 연락처를 받지 않는다**(원칙 III)
- [ ] **T068** [P] `backend/tests/contract/us2.contract.test.ts` — `/regions`, `/facilities`,
      `/facilities/{id}`, reports 계약 검증
- [X] **T069** [P] `backend/tests/unit/haversine.test.ts` — 알려진 좌표쌍의 거리와 경계 상자가
      실제 반경보다 넓어 후보를 놓치지 않음을 검증
- [X] **T070** [P] `frontend/src/components/FacilityCard.vue` — 기관명·거리·서비스 유형·
      **이용 대상 조건(필수)**·연락처. `phone`이 null이면 **통화 버튼을 숨기고** 주소·길찾기만 제공.
      거리가 직선거리 기준임을 표기(FR-021-2, FR-021b)
- [X] **T071** `frontend/src/components/MapView.vue` — Kakao Maps SDK 지도와 핀.
      **SDK 로드 실패·키 부재 시 목록만으로 정상 동작**해야 한다(research.md R-7)
- [X] **T072** `frontend/src/pages/MapPage.vue` — 현재 위치 사용과 지역 직접 선택 두 경로.
      **위치 거부해도 기능이 온전히 동작**(FR-015). 지도와 목록 동시 제공(FR-016).
      미확보 지역은 빈 지도 대신 "정보 준비 중" + 광역 대표 문의처(FR-016b)
- [X] **T073** `frontend/src/pages/FacilityDetailPage.vue` — 별도 번호 입력 없이
      통화 연결과 길찾기 실행(FR-018). 최종 갱신일과 오류 신고 수단 표시(FR-019)
- [ ] **T074** `frontend/tests/e2e/us2.spec.ts` — 진단을 거치지 않고 지도 메뉴 → 지역 선택 →
      상세 → 연락처 도달. 위치 거부 경로와 지도 실패 시 목록 폴백 확인

**Checkpoint**: US1과 US2가 각각 독립적으로 동작한다

---

## Phase 5: User Story 3 - 고부담 판정 시 가까운 기관 즉시 연결 (Priority: P3)

**Goal**: 고부담군 이상(또는 판정 불가)으로 판정된 보호자가 결과 화면에서 **추가 조작 없이**
연령에 맞는 유형의 가까운 기관 3곳을 안내받는다.

**Independent Test**: US1과 US2 완료 후, 고부담 응답을 넣어 결과 화면에 기관 3곳이 즉시
나타나는지, 중간부담 이하에서는 나타나지 않는지, 판정 불가에서는 **구분 문구와 함께** 나타나는지 확인.

**Depends on**: US1(판정) + US2(기관 조회) — 유일하게 다른 스토리에 의존하는 단계다

- [X] **T075** `backend/src/services/referralService.ts` — 3축 조립:
      **부담 구간 = 발동 임계값**(내부 라벨 ≤ 2), **연령 = 유형 필터**, **거리 = 정렬 기준**.
      임계값·기관 수는 `cb_config_v1`에서 읽는다(FR-021, FR-022)
- [X] **T076** `backend/src/services/referralService.ts` — 연령–유형 매핑.
      만 18세 미만 → `AFTERSCHOOL_YOUTH`, 만 18세 이상 → `DAY_ACTIVITY`(FR-021h).
      **매핑은 자격 판정이 아니다** — 연령을 이유로 목록을 차단하지 않는다(FR-021h-1, FR-021i-2)
- [X] **T077** `backend/src/services/referralService.ts` — 이용 대상 범위 밖 처리(FR-021i-1):
      만 6세 미만·만 65세 이상이면 ① 범위 밖 안내 ② 다른 제도 문의처 ③ **기관 3곳은 그대로 표시**
      + 확인 필요 병기. 연령 미입력이면 전체 유형에서 거리순(FR-021i)
- [X] **T078** `backend/src/services/diagnosisService.ts` — `immediateReferral` 결합.
      임계값 미만이면 null(FR-021c). 최고부담군이면 `emphasizeCounseling: true`(FR-021e).
      **판정 불가도 즉시 안내를 제공**하되 `undecidableNotice`로 고부담 판정과 구분(FR-021j, FR-021j-1)
- [X] **T079** [P] `backend/tests/unit/referral.test.ts` — 연령 경계값(5·6·17·18·64·65세)과
      부담 구간 1~5·판정 불가의 조합을 전수 검증. 연령 미입력 경로 포함
- [ ] **T080** [P] `backend/tests/contract/us3.contract.test.ts` — `DiagnosisResult`의
      `immediateReferral`·`ageOutOfRange` 스키마 검증
- [X] **T081** `frontend/src/stores/preSurveyStore.ts` + `PreSurveyPage.vue` — **연령 입력 항목 추가**.
      문구는 "돌보고 계신 발달장애인 당사자의 **만 나이**"처럼 대상과 기준을 명시하고,
      보호자 본인으로 읽힐 표현을 쓰지 않는다(FR-002e, FR-002e-1, FR-002e-2).
      **모델 입력·보관에 쓰지 않는다**(FR-021g)
- [X] **T082** `frontend/src/components/ImmediateReferral.vue` — 기관 3곳 카드.
      T070의 `FacilityCard`를 재사용해 **이용 대상 조건 표시 누락 0%**를 보장(SC-015)
- [X] **T083** `frontend/src/pages/ResultPage.vue` — 즉시 안내 영역 배치.
      과소 추정 안내(FR-010d)와 **위치를 구분**해 판정 자체와 혼동되지 않게 한다(spec Risks).
      "전체 기관 보기" 경로 제공(FR-023). 임계값 미만이면 지도 메뉴 이동 경로만(FR-021c)
- [X] **T084** `frontend/src/pages/ResultPage.vue` — 위치 정보 없을 때 지역 직접 선택을 요청하고
      같은 즉시 안내를 제공(FR-021d). 인근 0건이면 범위 확대·광역 문의처(FR-021f)
- [ ] **T085** `frontend/tests/e2e/us3.spec.ts` — 고부담 응답 → 추가 조작 없이 기관 3곳 확인
      (SC-013). 중간부담 이하 미표시, 판정 불가 시 구분 문구와 함께 표시, 만 5세·만 70세의
      범위 밖 안내 확인

**Checkpoint**: 세 User Story가 모두 독립적으로 검증 가능하다

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 여러 스토리에 걸치는 기본 사용성·개인정보·운영 항목

### 기본 사용성 (FR-039~FR-042 · 검토 10번 반영분)

- [X] **T086** [P] 전체 흐름을 **키보드만으로** 조작 가능하게 한다 — 포커스 순서, 포커스 표시,
      건너뛰기 링크(FR-039)
- [ ] **T087** [P] 글자 **200% 확대**에서 문항·선택지·구간 명칭·기관 정보가 잘리거나 겹치지
      않는지 확인하고 레이아웃을 수정(FR-040)
- [ ] **T088** [P] `frontend/tests/e2e/usability.spec.ts` — 키보드 전 흐름 완주,
      200% 확대 레이아웃, 색상 단독 전달 부재(FR-041), 경고 텍스트 병기(FR-042) 검증

### 개인정보·운영

- [X] **T089** **배포 설정에서 IP 제거** — Nginx `log_format`의 `$remote_addr` 제거,
      Express 요청 로거 IP 비활성화 확인. **코드만으로는 원칙 III를 지킬 수 없는 지점**
      (quickstart 8장)
- [X] **T090** [P] `backend/src/jobs/retention.ts` — 보존 기간 자동 파기.
      `cb_event_log_v1` 12개월(FR-030), `cb_training_response_v1` 36개월(FR-035).
      node-cron 또는 OS cron으로 두고 **컨테이너를 쓰지 않는다**(원칙 V). 실행 이력 기록
- [X] **T091** [P] `backend/src/jobs/saltRotation.ts` — 분기 1회 솔트 교체(FR-037).
      교체 이력을 `cb_salt_v1`에 남긴다
- [ ] **T092** `backend/src/middleware/rateLimit.ts` — 중복 제출 억제.
      해시 + 세션 + 시간창 3중이며 **자동 차단하지 않고 플래그만 기록**(FR-036a, FR-036c)
- [ ] **T093** [P] `backend/tests/integration/privacy.test.ts` — quickstart 7장 개인정보
      회귀 표 전체: 로그 금지 항목 부재, 두 저장소 컬럼 공집합, 미동의 저장 0건,
      별명 미전송, `SELECT MIN(n) FROM cb_reference_dist_v1 >= 30`

### 품질·문서

- [ ] **T094** `backend/src/api/facilities.ts` 외 — 기관 데이터 정기 재수집·재검증 절차와
      갱신 이력 조회(FR-019a). 운영자가 주기와 최종 수행 이력을 확인할 수 있어야 한다
- [ ] **T095** [P] `backend/src/jobs/accuracyReport.ts` — 축적된 자가보고 라벨로 운영 중 모델
      실제 정확도를 주기 산출하고 운영자가 확인 가능하게 한다(FR-038)
- [ ] **T096** 성능 검증 — 제출→결과 표시 **p95 3초 이내**(FR-026a, SC-018).
      초과 시 대기 상태 표시 확인(FR-026b). 병목이 모델이 아니라 DB 조회인지 측정으로 확인
- [X] **T097** [P] `README.md`·`CLAUDE.md` 갱신, `quickstart.md` 절차를 처음부터 끝까지 실행해
      기술한 대로 동작하는지 검증
- [ ] **T098** **자격증명 정리** — `Intent-Plan.md`와 `notebooks/eda-학습데이터셋_최종.ipynb`의
      평문 접속 정보를 `.env` 참조 방식으로 교체. 저장소를 공개 전환하거나 협업자를 추가하기
      전에 반드시 수행한다(quickstart 1장)

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1 Setup (T001~T009)
   └─► Phase 2 Foundational (T010~T024)   ⚠️ 모든 스토리를 막는다
          ├─► Phase 3 US1 (T025~T060)  ─┐
          ├─► Phase 4 US2 (T061~T074)  ─┤   US1·US2는 서로 독립 — 병렬 가능
          │                              └─► Phase 5 US3 (T075~T085)
          └──────────────────────────────────► Phase 6 Polish (T086~T098)
```

### User Story Dependencies

- **US1 (P1)**: Foundational 이후 시작. 다른 스토리에 의존하지 않는다
- **US2 (P2)**: Foundational 이후 시작. **모델 아티팩트가 없어도 동작한다** — US1과 완전 병렬
- **US3 (P3)**: US1(판정) + US2(기관 조회) 완료 필요. 세 스토리 중 유일한 의존 관계

### Within US1

```text
T025 (데이터 적재·검증)
  └─► T026 (기준 모델) ─► T027 (문항 선별) ─► T028 (임계값 보정) ─► T029 (export)
                                                                        ├─► T030 (패리티 기준값)
                                                                        └─► T031 (test 1회 평가)
T029 ─► T029a (설정 반영 + 백엔드 재기동)
T029 ─► T033 (로더) ─► T034 (예측) ─► T035 (SHAP) ─► T036 (판정불가) ─► T037 (패리티 게이트)
T029 ─► T038 (문항 적재) ─► T040 (GET /questions)
T034~T036 ─► T041 (diagnosisService) ─► T044 (POST /diagnoses)
T041 ─► T059 (ResultPage)
```

**핵심 직렬 구간** — T025→T026→T027→T028→T029는 순서를 바꿀 수 없다. 문항 선별 결과가
임계값 보정의 입력이고, 둘 다 확정되어야 export가 가능하다.

**T029a를 빠뜨리면 모델은 갱신됐는데 운영은 옛 값으로 도는 상태가 된다.** 산출물(`models/*.json`)과
운영 설정(`cb_config_v1`)이 서로 다른 저장소이므로, 둘을 잇는 이 단계가 없으면 조용히 어긋난다.

### Within US2

```text
T061 (적재) ─► T062 (검증) ─► T063 (facilityService) ─► T065 (GET /facilities) ─► T072 (MapPage)
T061 ─► T064 (GET /regions) ─► T072
T070 (FacilityCard) ─► T073 (상세) · T082 (US3 즉시안내에서 재사용)
```

---

## Parallel Opportunities

### Phase 1 — T002·T003·T004·T005·T006이 동시 실행 가능

```bash
Task: "backend/ 초기화 — TypeScript 5, Express 4, mysql2 3"
Task: "frontend/ 초기화 — Vite 5 + Vue 3.4 + TS, Pinia, Playwright"
Task: "ml/ 초기화 — requirements.txt, pyproject.toml"
Task: "db/ 초기화 — 마이그레이션 러너"
```

### Phase 2 — 마이그레이션 3종과 시드 2종

```bash
Task: "db/migrations/001_region_facility.sql"
Task: "db/migrations/002_operational.sql"
Task: "db/migrations/003_observability.sql"
# 마이그레이션 완료 후
Task: "db/seeds/regions.ts — 229개 시군구"
Task: "db/seeds/config.ts — 설정 키 14종"
```

### Phase 3·4 — **가장 큰 병렬 기회**

Foundational 완료 시점부터 **US1과 US2를 완전히 병렬로** 진행할 수 있다.
US2는 모델을 전혀 쓰지 않으므로, 오프라인 학습(T025~T032)이 도는 동안 지도 기능을 끝낼 수 있다.

```bash
# 개발자 A — US1 모델 파이프라인 (직렬, 가장 긴 경로)
Task: "ml/data.py → train → select → calibrate → export"

# 개발자 B — US2 전체 (US1과 무관)
Task: "db/seeds/facilities.ts → facilityService → /facilities → MapPage"

# 개발자 C — US1 화면 (API 계약만 있으면 목 데이터로 선행 가능)
Task: "HomePage · PreSurveyPage · SurveyPage · ConsentPage"
```

### Phase 3-D — 화면 컴포넌트 4종

```bash
Task: "HomePage.vue"          # T050
Task: "BurdenResultCard.vue"  # T056
Task: "ContributionList.vue"  # T057
Task: "ReferenceComparison.vue" # T058
```

### Phase 6 — T086·T087·T088·T090·T091·T093·T095·T097이 동시 실행 가능

---

## Implementation Strategy

### MVP First (US1만)

1. Phase 1 Setup (T001~T009)
2. Phase 2 Foundational (T010~T024) — **모든 스토리를 막으므로 최우선**
3. Phase 3 US1 (T025~T060)
4. **STOP & VALIDATE** — 지도 없이 진단만으로 전 흐름 검증.
   특히 T037 패리티 게이트와 T048 척도 방향 회귀를 통과해야 한다
5. 시연/배포 가능

MVP 범위에서 **제외**되는 것: 지도(US2), 즉시 안내(US3), 연령 입력(FR-002e는 P3 범위),
결과→신청처 이동(FR-014도 P3 범위). spec이 이 둘을 P3로 명시했으므로 US1 단독 전달에 문제가 없다.

### Incremental Delivery

1. Setup + Foundational → 기반 완성
2. **+ US1** → 독립 검증 → 배포 (**MVP**)
3. **+ US2** → 독립 검증 → 배포 (진단·지도 두 기능이 각각 동작)
4. **+ US3** → 독립 검증 → 배포 (두 기능이 결과 화면에서 연결)
5. **+ Polish** → 기본 사용성·보존 배치·성능 검증

### Parallel Team Strategy

Foundational 완료 후:

- **개발자 A**: US1 모델 파이프라인 (T025~T037) — 가장 긴 직렬 경로라 먼저 착수
- **개발자 B**: US2 전체 (T061~T074) — 모델과 무관해 완전 독립
- **개발자 C**: US1 화면 (T050~T059) — `contracts/openapi.yaml`로 목을 만들어 선행

US3(T075~T085)는 A와 B가 만나는 지점이므로 두 스토리 완료 후 착수한다.

---

## Notes

### 되돌릴 수 없는 결정 두 가지

- **T031의 test 602건 평가는 1회뿐이다.** 결과가 나쁘다고 T026~T028로 돌아가 재조정하면
  test가 오염되어 SC-004·SC-005의 최종 근거로 쓸 수 없다. 미달 시 대응은 문항 조합 재선별
  또는 성공 기준 재조정이며, **배제 6변수를 되살리는 방식은 채택하지 않는다**(FR-004b)
- **T007의 디자인 템플릿은 프로젝트 전반의 단일 기준이다.** 화면 작업(T050~T059, T070~T073,
  T082~T084) 전에 확정해야 하며, 나중에 바꾸면 모든 화면을 다시 손봐야 한다

### 실수하기 쉬운 지점

- **역방향 척도** — `care_burden`은 1이 최고부담이다. 임계값 비교는 `<=`이고 내부 라벨은
  이용자에게 노출하지 않는다. T048이 이를 6행 전수로 막는다
- **판정 불가의 이중성** — 부담 구간·기여 요인·비교는 **표시하지 않으면서** 즉시 안내는
  **제공한다**. 그리고 고부담 판정으로 읽히지 않게 문구로 구분해야 한다(T078)
- **저장소 분리** — `cb_event_log_v1`과 `cb_training_response_v1`에 편의상 공통 컬럼을 하나라도
  추가하면 FR-032가 깨진다. T013이 이를 테스트로 고정한다
- **연령의 지위** — 서비스 유형 판단 전용이며 모델 입력도 보관 대상도 아니다(T081)
- **모델 산출값과 운영 설정의 분리** — 백엔드는 `models/*.json`이 아니라 `cb_config_v1`을 읽는다.
  재학습 후 **T029a(설정 반영)를 돌리지 않으면 옛 임계값으로 서비스된다.** 화면에 오류가 뜨지
  않으므로 알아채기 어렵다. 2026-09-01 실제로 발생했다 — `tauConf` 0.34(자리표시) vs
  0.3239(산출값), `tauDens` -9.0으로 희소성 조건이 아예 발동하지 않았고,
  `minThreshold` 0.01로 기여 요인 강약 구분이 무의미했다

### 작업 규칙

- `[P]`는 서로 다른 파일이고 의존이 없다는 뜻이다. 같은 파일을 건드리는 작업은 순차 진행한다
  (예: T075·T076·T077은 모두 `referralService.ts`라 `[P]`가 없다)
- 각 작업 또는 논리적 묶음 단위로 커밋한다
- Checkpoint에서 멈춰 해당 스토리를 독립적으로 검증할 수 있다
