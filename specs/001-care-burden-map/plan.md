# Implementation Plan: 돌봄부담 경량 진단 및 지도 기반 복지서비스 안내

**Branch**: `001-care-burden-map` | **Date**: 2026-09-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-care-burden-map/spec.md`

**참조**: `Intent-Plan.md`(스택·DB) · `.specify/memory/constitution.md` v1.0.0 ·
`notebooks/eda-학습데이터셋_최종.ipynb` · `ABC8pioneer3` 실측 조회(2026-09-01)

---

## Summary

발달장애인 보호자가 계정 없이 **경량 문항에 답해 돌봄부담 구간을 진단받고**(P1),
**지도에서 복지서비스 신청 접수처를 찾고**(P2), **고부담 판정 시 추가 조작 없이 가까운 기관 3곳을
안내받는**(P3) 웹 서비스다.

기술적 접근의 핵심은 **학습과 추론의 분리**다. 2024 발달장애인 일과 삶 실태조사 3,000가구
데이터(`cb_dataset_v1`, 설명변수 38개)로 오프라인 Python 파이프라인에서 모델을 학습·검증하고,
그 결과를 **버전이 부여된 JSON 아티팩트**로 내보낸다. 운영 중 추론은 백엔드가 그 JSON을 읽어
**TypeScript로 직접 계산**한다. 이렇게 하면 Docker 없이(원칙 V) Node·Vue·MariaDB 스택을
벗어나지 않으면서(스택 제약), 동일 입력에 동일 출력을 구조적으로 보장할 수 있다(원칙 IV).

DB 실측 결과 `spec.md`의 모든 수치가 현재 상태와 일치했고, 예상하지 못한 자산 두 가지를 확인했다 —
**`cv_fold`가 train 2,398건에 5-fold로 이미 배정되어 있고**, **결측 처리가 정반대인
`v_cb_tree_v1`·`v_cb_linear_v1` 두 뷰가 준비되어 있다.** 전자는 문항 선별과 임계값 보정이 같은
분할 위에서 재현되게 하고, 후자는 트리 계열과 선형 계열을 같은 조건으로 대조할 수 있게 한다.

---

## Technical Context

**Language/Version**
- 런타임: TypeScript 5.x on Node.js 20 LTS (백엔드) · TypeScript 5.x + Vue 3.4 (프론트엔드)
- 오프라인 전용: Python 3.11+ (학습 파이프라인. **배포 대상 아님**)

**Primary Dependencies**
- 백엔드: Express 4.x, mysql2 3.x
- 프론트엔드: Vite 5.x, Pinia 2.x, Kakao Maps JS SDK
- 오프라인: scikit-learn, LightGBM, SHAP, pandas, pymysql

**Storage**: MariaDB 12.1.2 (`ABC8pioneer3`) — 학습 데이터는 읽기 전용, 운영·관측 테이블은 신규.
모델 아티팩트는 DB가 아닌 저장소 파일(`models/*.json`).

**Testing**: Vitest(백엔드·프론트엔드 단위/계약) · Playwright(E2E) · pytest(오프라인 모델) ·
Python↔TS 패리티 테스트(릴리스 게이트)

**Target Platform**: 모바일 웹 브라우저(스마트폰 우선). 서버는 Linux + Nginx 리버스 프록시.

**Project Type**: Web application (frontend + backend) + 오프라인 ML 파이프라인

**Performance Goals**: 제출→결과 표시 p95 3초 이내(FR-026a, SC-018). 판정과 기여 요인 산출 포함.

**Constraints**
- Docker 사용 금지(원칙 V, NON-NEGOTIABLE)
- 개인 식별 정보·원본 IP 미보관(원칙 III, NON-NEGOTIABLE)
- 내부 라벨(1=최고부담) 이용자 비노출(원칙 II)
- 저장소 간 연결 식별자 공유 금지(FR-032)

**Scale/Scope**
- 학습 데이터 3,000건 × 38 설명변수 · 5구간 분류
- 기관 1,283건 · 전국 229개 시군구(현재 221개 확보)
- 화면 약 8개 · API 엔드포인트 10개

**미결 항목** — 아래는 값이 아니라 **도출 규칙이 확정된 상태**이며, 실측으로만 정할 수 있어
지금 고정하면 원칙 I 위반이다. Phase 1 설계를 막지 않는다(research.md 참조).

| 항목 | 도출 규칙 | 확정 시점 |
|---|---|---|
| 최종 문항 수 k | R-4 후진 제거, SC-004·SC-005 정지 조건 | 모델 학습 |
| 모델 계열 | R-1 두 계열 5-fold 벤치마크 | 모델 학습 |
| τ_conf · τ_dens | R-6 CV 보정, SC-016 검증 | 모델 학습 |
| 기여도 구분 임계값 | R-3 SHAP 분포 하위 분위 | 모델 학습 |

---

## Constitution Check

*GATE: Phase 0 착수 전 1차 · Phase 1 설계 후 2차*

Constitution v1.0.0 기준.

### 1차 (Phase 0 착수 전)

| # | 게이트 | 결과 | 판단 근거 |
|---|--------|------|-----------|
| I | 근거 기반 판정 **(NON-NEGOTIABLE)** | **통과** | 문항 수·임계값·기여도 기준을 값이 아닌 도출 규칙으로 두었다(FR-004c, FR-009b). 배제 6변수는 `cb_dataset_v1`에 **애초에 존재하지 않아** 스키마로 차단된다. MI 순위는 참고 자료로만 쓴다 |
| II | 설명가능성 | **통과** | 개별 SHAP 기여도(FR-011a), 판정 불가 경로(FR-009a), 표시 명칭 변환(FR-010a)이 모두 설계에 반영됨 |
| III | 최소 수집과 익명성 **(NON-NEGOTIABLE)** | **통과** | 저장소 3분할, 금지 항목은 컬럼 자체를 두지 않음, 보존·파기 정의됨. 미동의 시 학습 저장만 생략 |
| IV | 재현성과 외부화 | **통과** | 모델·문항 집합·설정에 버전 부여, FR-022 설정 키 14종을 `cb_config_v1`로 외부화 |
| V | 컨테이너 없는 전개 **(NON-NEGOTIABLE)** | **통과** | 런타임 구성 요소는 Node 프로세스 + Nginx뿐. Python은 오프라인 도구이며 배포되지 않음 |
| — | 스택 준수 | **조건부 통과** | 서비스 스택은 Vue/Node/MariaDB를 벗어나지 않음. **오프라인 Python 도입은 Complexity Tracking에 기록** |
| — | 척도 방향 | **통과** | 1=최고부담 전제를 임계값 비교('이하')와 표시 매핑에 반영. 5구간 전수 회귀 테스트 필수화 |
| — | 측정 가능성 | **통과** | spec.md의 측정 수단 표에 SC 전체가 배정됨 |
| — | 독립 전달 | **통과** | P1은 지도 없이, P2는 진단 없이 각각 동작. P3만 두 스토리에 의존 |

### 2차 (Phase 1 설계 후)

| # | 게이트 | 결과 | 설계로 강화된 점 |
|---|--------|------|-----------------|
| I | 근거 기반 판정 | **통과** | `models/selection_v1.json`·`uncertainty_v1.json`이 도출 근거를 아티팩트로 남긴다. test 602건 1회 사용 규칙을 quickstart에 명문화 |
| II | 설명가능성 | **통과** | `DiagnosisResult`가 내부 라벨을 반환하지 않고 `burdenLabel`만 낸다. 판정 불가 시 `contributions`·`comparison`이 null |
| III | 최소 수집과 익명성 | **통과** | `cb_event_log_v1`과 `cb_training_response_v1`의 **공통 컬럼 집합이 공집합**이라 조인이 불가능하다. `cb_reference_dist_v1`은 `CHECK (n >= 30)`으로 재식별을 스키마로 차단 |
| IV | 재현성과 외부화 | **통과** | 기동 시 모델·문항·설정 정합을 검증하고 불일치면 fail fast. 패리티 테스트를 릴리스 게이트로 둠 |
| V | 컨테이너 없는 전개 | **통과** | 배포 단위가 `frontend/dist` + `backend/dist` + `models/*.json`. 프로세스 관리는 systemd 선언 설정 |
| — | 스택 준수 | **조건부 통과** | 변동 없음. 아래 Complexity Tracking 참조 |
| — | 척도 방향 | **통과** | quickstart.md에 내부 라벨 1~5 + 판정 불가 6행 회귀 테스트 표를 명시 |
| — | 측정 가능성 | **통과** | SC-015(조건 표시 누락 0%)는 `FacilityCard.eligibilityNote`를 필수 필드로 두어 계약 수준에서 보장 |
| — | 독립 전달 | **통과** | 아래 전달 순서 참조 |

**게이트 통과.** NON-NEGOTIABLE 항목(I·III·V) 위반 없음.

---

## Project Structure

### Documentation (this feature)

```text
specs/001-care-burden-map/
├── plan.md              # 이 문서
├── research.md          # Phase 0 — 기술 결정 11건
├── data-model.md        # Phase 1 — 물리 스키마 + 아티팩트
├── quickstart.md        # Phase 1 — 개발·학습·배포 절차
├── contracts/
│   └── openapi.yaml     # Phase 1 — API 계약 10개 엔드포인트
├── checklists/
│   └── requirements.md  # 기존
└── tasks.md             # Phase 2 — /speckit.tasks 가 생성 (이 명령은 만들지 않음)
```

### Source Code (repository root)

```text
backend/                          # Node 20 + Express + TypeScript
├── src/
│   ├── api/                      # 라우터 — openapi.yaml 과 1:1
│   │   ├── questions.ts          # GET /questions
│   │   ├── diagnoses.ts          # POST /diagnoses · DELETE /diagnoses/:token
│   │   ├── facilities.ts         # GET /facilities · /facilities/:id · POST reports
│   │   ├── regions.ts            # GET /regions
│   │   ├── meta.ts               # GET /config · /model
│   │   └── events.ts             # POST /events
│   ├── inference/                # ★ 런타임 추론 (Python 없음)
│   │   ├── modelLoader.ts        # models/*.json 로드 + 정합 검증 (fail fast)
│   │   ├── predictor.ts          # 트리 순회 → 클래스 확률 → 보정
│   │   ├── treeShap.ts           # 개별 기여도 (FR-011a)
│   │   └── undecidable.ts        # τ_conf · τ_dens 판단 (FR-009a)
│   ├── services/
│   │   ├── diagnosisService.ts   # 판정 → 기여요인 → 비교 → 즉시안내 조립
│   │   ├── referralService.ts    # 임계값·연령 매핑·거리 정렬 (FR-021*)
│   │   ├── facilityService.ts    # 경계상자 선필터 + Haversine (R-9)
│   │   ├── consentService.ts     # 학습 저장 분기 (FR-031·FR-033)
│   │   └── eventService.ts       # 익명 로그 기록 (FR-027·FR-028)
│   ├── repositories/             # mysql2 직접 쿼리
│   ├── config/                   # cb_config_v1 로더 + 캐시
│   └── server.ts
└── tests/{unit,contract,parity}/

frontend/                         # Vue 3 + TS + Vite + Pinia
├── src/
│   ├── pages/
│   │   ├── HomePage.vue          # 두 메뉴 동등 제시 (FR-001)
│   │   ├── PreSurveyPage.vue     # 사전 입력 3항목, 전부 건너뛰기 가능 (FR-002a~h)
│   │   ├── SurveyPage.vue        # 진행률·이전이동·해당없음 (FR-004d~007)
│   │   ├── ConsentPage.vue       # 동의 → 자가보고 문항 (FR-033 → FR-008e)
│   │   ├── ResultPage.vue        # 판정·기여요인·비교·즉시안내 (FR-009~021)
│   │   ├── MapPage.vue           # 지도 + 목록 동시 (FR-015~020)
│   │   └── FacilityDetailPage.vue
│   ├── stores/
│   │   ├── surveyStore.ts        # localStorage 24시간 만료 (FR-008-1·2)
│   │   ├── preSurveyStore.ts     # 별명은 sessionStorage, 연령은 메모리
│   │   └── resultStore.ts
│   ├── components/
│   │   ├── BurdenResultCard.vue  # 색상 단독 금지 · 텍스트 병기 (FR-041·042)
│   │   ├── FacilityCard.vue      # eligibilityNote 필수 표시 (SC-015)
│   │   └── MapView.vue           # 지도 실패 시 목록 폴백
│   └── services/apiClient.ts
└── tests/{unit,e2e}/

ml/                               # ★ Python — 오프라인 전용, 배포되지 않음
├── data.py                       # v_cb_tree_v1 / v_cb_linear_v1 적재
├── select.py                     # 후진 제거 문항 선별 (FR-004c)
├── train.py                      # 학습 · 확률 보정 · export
├── calibrate.py                  # 판정 불가 임계값 (FR-009b)
├── evaluate.py                   # test 602건 1회 평가 (SC-004·SC-005)
├── parity.py                     # TS 추론기 대조 기준값 생성
└── tests/

models/                           # 버전 고정 아티팩트 (배포에 포함)
├── model_v1.json  selection_v1.json  uncertainty_v1.json
├── questions_v1.json  parity_v1.json

db/                               # 스키마 · 적재
├── migrations/                   # cb_region_v1, cb_facility_v1, ...
└── seeds/                        # 229개 시군구 · 기관 정규화 · 참조 분포

notebooks/                        # 기존 EDA (변경 없음)
```

**Structure Decision** — `Intent-Plan.md`의 프론트/백엔드 분리 구조를 그대로 따르되
**`ml/`과 `models/`를 추가**했다. 이 둘이 없으면 모델 학습 산출물이 노트북 안에 갇혀
버전 관리와 재현이 불가능해진다(원칙 IV). `ml/`은 배포 대상이 아니고 `models/`만 실린다.

`backend/src/inference/`를 `services/`와 분리한 이유는, 이 폴더가 **패리티 테스트로 Python
구현과 동등성이 보증되어야 하는 유일한 영역**이기 때문이다. 경계를 명확히 두면 검증 범위가 좁아진다.

---

## 데이터 및 모델 구성 계획

`notebooks/eda-학습데이터셋_최종.ipynb`의 검토 결과를 구현 계획으로 옮긴 것이다.

### 1. 데이터 파이프라인

```text
2024_care_burden_std09 (원천 3,000건 · 507문항)
        │  ※ 배제 6변수는 여기까지만 존재 (FR-004b)
        ▼
cb_dataset_v1  3,000 × 43  (메타 4 + target 1 + 설명변수 38)
        │      split: train 2,398 / test 602 (층화 오차 ≤0.16%p)
        │      cv_fold: train에 1~5 배정 (483/481/478/478/478)
        ├──────────────► v_cb_tree_v1   (42열, NULL 원형)  → 트리 계열
        └──────────────► v_cb_linear_v1 (44열, -1 + isna)  → 선형 계열
```

**설계에 반영한 노트북의 관측 4가지**

| 노트북 관측 | 구현 반영 |
|---|---|
| 결측이 88.1% / 30.2% / 69.8%로 **뭉친다** — 분기 문항의 "해당 없음"이다 | 트리 계열을 주 후보로(NULL 네이티브 처리), FR-004d "해당사항 없음" 선택지를 `cb_question_v1.has_not_applicable`로 데이터화 |
| 5단계(부담 없음) train 61건 — macro F1의 병목 | 클래스 가중치 적용, 리샘플링 금지(R-5). 가중치가 확률을 왜곡하므로 **보정 후** 임계값 산출 |
| `secondary_caregiver_type` 역설 — 보조 제공자가 **있는** 쪽 고부담 +3.8%p (역인과) | FR-011 문장을 `explain_template` 컬럼으로 데이터화해 도메인 담당자가 검수. **인과 표현 대신 동반 관찰 표현** |
| 배제 최상위 I14(19.06%)가 잔존 최상위(8.23%)의 2.3배 | 성능 미달 시에도 배제를 되돌리지 않음. `evaluate` 실패는 문항 조합 재선별 또는 SC 재조정으로 대응 |

### 2. 모델 구성

```text
[계열 선택]  트리 앙상블(LightGBM·RF·HistGB)  vs  순서형/다항 로지스틱
             └ 같은 5-fold, 같은 지표로 대조 → SC-004·SC-005로 선택

[문항 선별]  38변수 기준 모델 → 후진 제거(SHAP 전역 중요도 최하위부터)
             정지: ΔmacroF1 ≤ 0.03  AND  Δ고부담재현율 ≤ 0.05  AND  재현율 ≥ 0.70
             → 최소 k 확정 · selection_v1.json

[확률 보정]  클래스 가중 학습 → isotonic/Platt 보정 (임계값의 전제)

[판정 불가]  max p(y|x) < τ_conf  OR  density(x) < τ_dens
             격자 탐색: 판정불가 오분류율 > 판정 오분류율 AND 판정불가 비율 ≤ 10%
             → uncertainty_v1.json

[내보내기]   model_v1.json (트리 구조 + base_score + 보정 파라미터)
             ↓
[런타임 TS]  트리 순회 → 확률 → TreeSHAP 기여도 → 판정 불가 판단
             ↑ 패리티 테스트로 Python과 1e-9 이내 일치 보증
```

**평가는 마지막에 단 한 번** — test 602건은 계열 선택·문항 선별·임계값 보정이 모두 끝난 뒤
`evaluate --use-test`로 1회만 사용한다. 결과가 나쁘다고 앞 단계로 돌아가면 test가 오염되어
SC-004·SC-005의 최종 근거로 쓸 수 없다.

### 3. 기능으로의 연결

| 모델 산출물 | 기능 | FR |
|---|---|---|
| 선택된 k개 문항 | 진단 설문 화면·진행률 | FR-003, FR-005 |
| 클래스 확률 → argmax | 5구간 판정 → 표시 명칭 | FR-009, FR-010a |
| TreeSHAP 기여도 | 기여 요인 최소 3개 + 약한 요인 구분 | FR-011, FR-011-1 |
| τ_conf · τ_dens | 판정 불가 → 안내 + 안전망 즉시 안내 | FR-009a, FR-021j |
| 판정 구간 ≤ 2 | 즉시 안내 발동 | FR-021 |
| 모델 버전 | 결과·로그 기록, 교체 공개 | FR-012a, FR-012b |
| 자가보고 라벨 축적 | 운영 중 실제 정확도 산출 | FR-038 |

---

## 전달 순서 (독립 전달)

| 단계 | 범위 | 선행 조건 | 독립 검증 |
|---|---|---|---|
| **P1** | 사전입력 → 설문 → 동의 → 자가보고 → 판정 → 기여요인 → 비교 | 모델 아티팩트 | 지도 없이 진단만으로 동작 |
| **P2** | 지역 선택/위치 → 지도 + 목록 → 상세 → 통화·길찾기 → 오류 신고 | 기관 정규화 적재 | 진단 없이 지도만으로 동작 |
| **P3** | 결과 화면의 즉시 안내 3곳 · 연령 필터 · 범위 밖 안내 | P1 + P2 | 두 스토리 완료 후 검증 |

P1과 P2는 서로를 전제하지 않는다. `FR-014`(결과→신청처 이동)와 `FR-002e`(연령 입력)가
**P3 범위로 명시**되어 있어, P1 단독 전달 시 해당 UI를 표시하지 않으면 된다.

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **오프라인 Python 파이프라인(`ml/`) 도입** — 헌법 "기술 및 데이터 제약"의 스택 목록(Vue/Node/MariaDB)에 없는 언어다 | 문항 선별(RFE), 확률 보정, SHAP 전역 중요도, 5-fold 교차검증에 필요한 도구가 Python 생태계에만 성숙해 있다. 원칙 I은 이 값들을 **실측으로 도출**할 것을 요구하므로 도구 없이는 원칙 자체를 지킬 수 없다 | **TS로 학습까지 구현**: LightGBM·SHAP·isotonic 보정을 직접 구현해야 하고, 구현 오류가 곧 판정 오류가 되어 원칙 I을 더 크게 위협한다. **노트북에 학습을 남겨둠**: 버전 관리·재현이 불가능해 원칙 IV 위반 |

**위반의 범위를 좁히는 조치**

1. Python은 **런타임에 존재하지 않는다.** 배포 산출물은 `frontend/dist` + `backend/dist` +
   `models/*.json`뿐이며, 서비스 구성 요소는 Node 프로세스 하나다. 원칙 V(NON-NEGOTIABLE)와
   무관하고, 스택 제약의 대상인 **서비스 스택은 위반하지 않는다.**
2. 이미 저장소의 `notebooks/`가 Python이며 같은 지위다. `ml/`은 그 코드를 버전 관리 가능한
   형태로 옮기는 것에 가깝다.
3. 경계를 패리티 테스트로 고정한다 — Python이 만든 아티팩트와 TS 추론기가 3,000건 전량에서
   1e-9 이내로 일치해야 배포된다.

**헌법 개정 필요 여부** — 헌법은 "다른 스택을 도입하려면 개정 절차를 거쳐야 한다"고 한다.
위 3개 조치로 서비스 스택은 무결하지만, **오프라인 도구의 지위를 헌법이 명시하지 않는다**는
공백이 남는다. 다음 개정 시 "분석·학습 도구는 배포 대상이 아닌 한 스택 제약의 대상이 아니다"는
문장을 추가할 것을 제안한다. 그때까지는 이 기록으로 대신한다.

---

## Phase 산출물

| Phase | 산출물 | 상태 |
|---|---|---|
| 0 | `research.md` — 기술 결정 11건, 미결 6건의 도출 규칙 | 완료 |
| 1 | `data-model.md` — 학습 데이터 3 + 운영 9 + 관측 2 + 클라이언트 3 | 완료 |
| 1 | `contracts/openapi.yaml` — 엔드포인트 10개 | 완료 |
| 1 | `quickstart.md` — 개발·학습·테스트·배포 | 완료 |
| 2 | `tasks.md` | **미생성** — `/speckit.tasks`로 생성한다 |

## 다음 단계에서 확인할 위험

| 위험 | 조기 확인 방법 |
|---|---|
| TreeSHAP TS 이식 난도 | 학습 착수와 동시에 스파이크. 어려우면 Saabas 폴백(기여도 크기 미표기) |
| 문항 수 k가 30을 넘음 | `select` 단계 직후 판단. "경량 진단" 성격 재검토(spec Risks) |
| 미확보 8개 시군구 문의처 미확보 | `seed:regions` 시점에 공백 목록 확정 → 도메인 담당자 전달 |
| Nginx·Express 로그의 IP 잔존 | 배포 설정 리뷰를 별도 작업으로 분리(quickstart 8장) |
