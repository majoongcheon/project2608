# Phase 1 — Data Model: 돌봄부담 경량 진단 및 지도 기반 복지서비스 안내

**Branch**: `001-care-burden-map` | **Date**: 2026-09-01 | **DB**: `ABC8pioneer3` (MariaDB 12.1.2)

`spec.md`의 Key Entities를 물리 스키마와 런타임 아티팩트로 옮긴 것이다.
**기존 객체는 변경하지 않는다** — 학습 데이터는 읽기 전용으로만 쓰고, 신규 객체는 모두 `cb_` 접두사와
`_v1` 접미사를 붙여 기존과 구분한다.

## 저장소 분리 원칙 (FR-032 · 원칙 III)

이 설계에서 가장 중요한 제약이다. **세 저장소는 서로의 기록을 연결할 수 없어야 한다.**

```text
① 학습 데이터 (읽기 전용)        ② 운영 기준 데이터            ③ 관측·수집 (분리 필수)
   cb_dataset_v1                    cb_region_v1                  ┌─ cb_event_log_v1
   cb_feature_meta_v1               cb_facility_v1                │    세션 식별자 O
   v_cb_tree_v1                     cb_facility_service_v1        │    응답 내용 X
   v_cb_linear_v1                   cb_question_v1                │
   2024_care_burden_std09           cb_config_v1                  └─ cb_training_response_v1
                                    cb_model_version_v1                세션 식별자 X
                                    cb_reference_dist_v1               응답 내용 O
                                    cb_salt_v1                         제출자 해시 O
```

**③의 두 테이블은 개별 기록을 연결할 수 있는 컬럼을 공유하지 않는다.** `cb_event_log_v1`은
`session_id`를 갖고 응답 내용을 갖지 않으며, `cb_training_response_v1`은 응답 내용을 갖고
`session_id`를 갖지 않는다. 조인 키가 존재하지 않아야 FR-032가 구조적으로 성립한다.
시각도 초 단위로 절삭해 저장해, 타임스탬프 대조로 두 기록을 짝지을 수 없게 한다.

**단, `model_version`은 양쪽에 존재한다.** FR-027이 익명 로그에, FR-031이 학습 저장소에 각각
모델 버전 기록을 요구하기 때문이다. 이 값은 수천 건이 공유하는 저카디널리티 속성이라 어느
이벤트가 어느 응답인지 좁히지 못하므로 연결 고리가 되지 않는다. `db/scripts/verify.js`는
이 두 값(`model_version`, `question_set_version`)만 예외로 두고 그 밖의 공통 컬럼을 위반으로 잡는다.

---

## 1. 학습 데이터 (기존 · 읽기 전용)

### 1.1 `cb_dataset_v1` — 정제 데이터셋

3,000행 × 43열. 실측 확인 완료.

| 구분 | 컬럼 | 타입 | 비고 |
|---|---|---|---|
| 메타 | `row_id` | `int` PK | |
| 메타 | `row_key` | `char(32)` UNI | 원자료 대응 해시 |
| 메타 | `split` | `enum('train','test')` | train 2,398 / test 602 |
| 메타 | `cv_fold` | `tinyint` NULL | train만 1~5 (483/481/478/478/478), test는 NULL |
| target | `care_burden` | `tinyint` | **1=최고부담 … 5=부담 없음 (역방향)** |
| 설명변수 | 38개 | `smallint` NULL | 아래 1.2 참조 |

**`cv_fold`가 DB에 고정되어 있다는 점이 중요하다.** R-4의 문항 선별과 R-6의 임계값 보정이 같은
fold를 쓰므로, 두 산출물이 서로 다른 분할에서 나오는 일이 없다(원칙 IV).

**test 602건 사용 규칙** — 문항 선별·하이퍼파라미터 탐색·임계값 보정·모델 계열 선택이 **모두 끝난 뒤
단 한 번** SC-004·SC-005 최종 평가에만 사용한다. 그 전에 어떤 형태로든 참조하면 지표가 낙관 편향된다.

### 1.2 `cb_feature_meta_v1` — 변수 메타 (38행)

| 컬럼 | 타입 | 용도 |
|---|---|---|
| `feature` | `varchar(64)` PK | `cb_dataset_v1` 컬럼명 |
| `var_scale` | `enum('continuous','ordinal','binary','nominal')` | continuous 4 · ordinal 12 · binary 13 · nominal 9 |
| `n_levels` | `int` | 범주 수 |
| `n_missing`·`missing_pct` | `int`·`decimal(5,2)` | 결측 규모 |
| `scale_note` | `varchar(255)` | 값 의미 서술 |

`scale_note`는 FR-004a의 자연어 문항 변환과 FR-011의 설명 문장 작성에 **직접 쓰이는 근거**다.
예: `wants_person_employed` = "1 지금 당장, 2 언젠가, 3 원하지 않음. 클수록 취업 희망 약함".
방향이 역전된 변수가 섞여 있으므로, 문항 문구를 만들 때 이 컬럼을 반드시 확인한다.

### 1.3 모델 입력 뷰

| 뷰 | 열 | 결측 처리 | 대상 계열 |
|---|---|---|---|
| `v_cb_tree_v1` | 42 | NULL 원형 유지 | 트리 앙상블 |
| `v_cb_linear_v1` | 44 | NULL→`-1` + `past_job_count_isna`·`age_disability_suspected_isna` | 선형/순서형 |

**`v_cb_linear_v1`이 `-1`을 쓰는 것에 주의한다.** 선형 계열을 채택하면 이 값은 범주로 원-핫
인코딩되어야 하며, 연속형 2개(`past_job_count`, `caregiver_age`)에는 `-1`을 넣지 않고 `*_isna`
플래그로만 처리한다(뷰가 이미 그렇게 되어 있다).

### 1.4 배제 6변수 (FR-004b · 원천 테이블에만 존재)

`cb_dataset_v1`에 **애초에 없으므로 실수로 입력에 섞일 수 없다.** 이것이 배제를 코드 규칙이 아니라
스키마로 보장하는 방식이다.

| 원 문항 | 변수 | MI/H (실측) | 배제 사유 |
|---|---|---|---|
| I14 | `caregiver_life_satisfaction` | **19.06%** | target과 동일 구성개념 |
| I10 | `care_difficulty_top1` | 6.88% | 부담을 전제하고 원인을 물음 |
| I12_1 | `needed_care_service_type` | 4.98% | 부담 판단의 결과 |
| I11_H | `work_care_gap_hours` | 1.08% | target과 동일 I 블록 |
| I11 | `work_care_gap_exp` | 0.62% | target과 동일 I 블록 |
| I12 | `integrated_care_awareness` | 0.36% | target과 동일 I 블록 |

배제 최상위(19.06%)가 잔존 최상위(`help_needed_hours` 8.23%)의 2.3배다.
**배제 비용 10.83%p** — SC-004·SC-005 미달 시에도 이 규칙을 되돌리지 않는다는 결정의 근거다.

---

## 2. 모델 아티팩트 (파일 · 버전 고정)

DB가 아니라 저장소 파일로 관리한다. 배포 단위에 함께 실려야 하고(원칙 V), 내용이 바뀌면
버전이 바뀌어야 하기 때문이다(원칙 IV).

```text
models/
├── model_v1.json          # 트리 구조 또는 계수 행렬 + 클래스 순서 + 확률 보정 파라미터
├── selection_v1.json      # 채택 문항 k개, 탈락 순서, 단계별 CV 지표 (FR-004c 근거)
├── uncertainty_v1.json    # τ_conf, τ_dens, 보정 절차, 검증 결과 (FR-009b 근거)
├── questions_v1.json      # 문항 번호 ↔ 변수 ↔ 자연어 문장 ↔ 선택지 (FR-004a)
└── parity_v1.json         # Python↔TS 패리티 검증 결과 (R-2 릴리스 게이트)
```

### `model_v1.json` 구조 (트리 계열)

```jsonc
{
  "model_version": "v1.0.0",           // FR-012a — 결과·로그에 기록되는 값
  "family": "lightgbm",
  "features": ["help_needed_hours", "..."],   // selection_v1.json 의 k개와 일치해야 함
  "classes": [1, 2, 3, 4, 5],          // 내부 라벨. 1=최고부담
  "trees": [ { "split_feature": 0, "threshold": 2.5, "missing_to_left": true,
               "left": {...}, "right": {...}, "value": [...] } ],
  "base_score": [...],                 // TreeSHAP 기준값 — 기여도 합의 출발점
  "calibration": { "method": "isotonic", "params": [...] }
}
```

**불변 조건** — `features` 배열의 순서가 곧 입력 벡터의 순서다. 이 순서가 어긋나면 조용히 잘못된
판정이 나오므로, 로드 시 `selection_v1.json`과 대조하고 불일치면 **기동을 실패시킨다**(fail fast).

---

## 3. 운영 기준 데이터 (신규)

### 3.1 `cb_region_v1` — 전국 229개 시군구 (FR-016a · FR-016b)

**이 테이블이 없으면 "미확보 지역"을 판별할 수 없다.** 원천 기관 데이터에는 데이터가 있는 221개만
존재하므로, 229개 기준 목록을 별도로 세워야 8개의 공백이 드러난다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `region_code` | `char(5)` PK | 행정표준코드 시군구 |
| `sido_name` | `varchar(20)` | 시도명 |
| `sigungu_name` | `varchar(40)` | 시군구명 |
| `center_lat`·`center_lng` | `double` | 지역 직접 선택 시 기준 좌표(FR-021d) |
| `has_facility_data` | `boolean` | 파생값. 적재 배치가 갱신 |
| `metro_contact_name`·`metro_contact_phone` | `varchar` NULL | 광역 대표 문의처(FR-016b) |

`INDEX (sido_name, sigungu_name)` · `INDEX (has_facility_data)`

**`center_lat/lng`의 용도** — 위치 정보를 거부한 보호자가 지역을 직접 고르면 이 좌표가 기준 위치가
된다. 보호자의 실제 좌표가 아니므로 보관 제약(FR-026)과 무관하다.

### 3.2 `cb_facility_v1` — 기관 (FR-017 · FR-018 · FR-019)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `facility_id` | `int` PK AI | 원천에 없어 신규 부여 |
| `region_code` | `char(5)` FK → `cb_region_v1` | |
| `name` | `varchar(120)` | 제공기관명 |
| `address`·`address_detail` | `varchar(255)` | |
| `phone` | `varchar(30)` NULL | **결측 58건 + 형식 오류 2건은 NULL** |
| `lat`·`lng` | `double` NOT NULL | 결측 0건 확인 |
| `updated_at` | `date` | 최종 갱신일 표기(FR-019) |
| `source_batch` | `varchar(40)` | 재수집 이력 추적(FR-019a) |

`INDEX (lat, lng)` — R-9의 경계 상자 선필터가 타는 인덱스 · `INDEX (region_code)`

**`phone`이 NULL이면 FR-018의 통화 버튼을 숨기고 주소·길찾기만 제공한다**(spec Risks).
빈 문자열이 아니라 NULL이어야 이 분기가 코드에서 명확해진다.

### 3.3 `cb_facility_service_v1` — 기관×서비스 (FR-021a · FR-021h)

기관 하나가 두 유형을 모두 제공할 수 있으므로 분리한다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `facility_id` | `int` PK(복합) FK | |
| `service_type` | `enum('DAY_ACTIVITY','AFTERSCHOOL_YOUTH')` PK(복합) | 주간활동 727 / 방과후 556 |
| `program_name` | `varchar(120)` NULL | 원천 `사업명` |

`INDEX (service_type, facility_id)`

**유형이 2종으로 하드코딩되지 않게 하는 지점** — FR-022a는 유형 수를 코드에 고정하지 말라고 한다.
`service_type`을 enum으로 두면 확장 시 DDL이 필요하므로, **연령–유형 매핑과 이용 대상 범위는
`cb_config_v1`에 두고 코드는 설정을 읽어 동작하게 한다.** enum 자체의 확장은 데이터 추가 작업이다.

### 3.4 `cb_facility_report_v1` — 정보 오류 신고 (FR-019b)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `report_id` | `bigint` PK AI | |
| `facility_id` | `int` FK | |
| `report_type` | `enum('PHONE','ADDRESS','CLOSED','SERVICE','OTHER')` | |
| `detail` | `varchar(500)` NULL | 자유 입력 |
| `status` | `enum('RECEIVED','REVIEWING','RESOLVED','REJECTED')` | 처리 상태 추적 |
| `created_at`·`resolved_at` | `datetime` | |

**개인정보 주의** — 신고자 연락처를 받지 않는다(원칙 III). `detail`은 자유 입력이라 보호자가
식별 정보를 적을 수 있으므로, 입력란에 안내하고 길이를 제한한다(FR-002c와 같은 취지).

### 3.5 `cb_question_v1` — 진단 문항 (FR-003 · FR-004a · FR-005)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `question_set_version` | `varchar(20)` PK(복합) | 문항 집합 버전(원칙 IV) |
| `question_no` | `smallint` PK(복합) | 표시 순서 = 진행률의 분자 |
| `feature` | `varchar(64)` | `cb_feature_meta_v1.feature` 대응 |
| `original_item` | `varchar(20)` | 원 실태조사 문항 코드(G6, F1 …) |
| `question_text` | `varchar(300)` | 자연어 질문 |
| `options_json` | `json` | `[{value, label}]` + "해당사항 없음"(FR-004d) |
| `has_not_applicable` | `boolean` | 조건부 문항 여부 |
| `explain_template` | `varchar(300)` | FR-011 설명 문장 템플릿 |

**`explain_template`을 문항 테이블에 두는 이유** — 기여 요인 문장을 코드에 문자열로 박으면
FR-011의 검수(R-3의 인과 오독 방지)를 매번 배포로 처리해야 한다. 데이터로 두면 복지 도메인
담당자가 검토·수정할 수 있다.

**진행률(FR-005)의 분모** — `question_set_version`에 속한 행 수. 사전 입력 3항목은 포함하지
않는다(FR-002b).

### 3.6 `cb_config_v1` — 외부화 설정 (FR-022 · 원칙 IV)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `config_key` | `varchar(60)` PK(복합) | |
| `version` | `varchar(20)` PK(복합) | |
| `value_json` | `json` | |
| `active_from` | `datetime` | 활성 시점 |
| `reviewed_by`·`reviewed_at` | `varchar(60)`·`datetime` | 복지 도메인 담당자 검증 이력(FR-022) |

FR-022가 열거한 설정 키 전체:

| `config_key` | 기본값 | 근거 FR |
|---|---|---|
| `referral.threshold` | 내부 라벨 ≤ 2 | FR-021 |
| `referral.counseling_threshold` | 내부 라벨 ≤ 1 | FR-021e |
| `referral.facility_count` | 3 | FR-021 |
| `referral.radius_steps_km` | `[10, 20, 50]` | FR-021f, R-9 |
| `age.mapping_boundary` | 18 | FR-021h |
| `age.service_ranges` | 방과후 6~17 / 주간활동 18~64 | FR-021i-1 |
| `age.out_of_range_notice` | 만 6세 미만·만 65세 이상 문구 | FR-021i-3 |
| `undecidable.tau_conf`·`undecidable.tau_dens` | R-6 산출 | FR-009c |
| `undecidable.notice_text` | 판정 불가 안내 문구 | FR-021j-1 |
| `selfreport.notice_text` | 자가보고 문항 안내 문구 | FR-008d |
| `contribution.min_threshold` | R-3 산출 | FR-011-1 |
| `draft.expiry_hours` | 24 | FR-008-2 |
| `submit.rate_limit` | 시간창·횟수 | FR-036c |
| `burden.labels` | 5구간 표시 명칭 | FR-010a |

**`burden.labels`를 설정에 두는 이유** — 내부 라벨 1~5를 표시 명칭으로 바꾸는 매핑은 원칙 II의
핵심이고, 역방향 척도라 실수 시 정반대로 표시된다. 코드가 아니라 한 곳의 데이터로 두면
검증 지점이 하나로 모인다.

### 3.7 `cb_model_version_v1` — 모델 버전 이력 (FR-012a · FR-012b)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `model_version` | `varchar(20)` PK | |
| `family`·`question_set_version` | `varchar` | 계열, 대응 문항 집합 |
| `macro_f1`·`high_burden_recall` | `decimal(5,4)` | test 602건 최종 평가(SC-004·SC-005) |
| `undecidable_rate` | `decimal(5,4)` | SC-016 |
| `activated_at`·`deactivated_at` | `datetime` | FR-012b 공개용 |
| `notes` | `text` | 교체 사유 |

### 3.8 `cb_reference_dist_v1` — 참조 집단 분포 (FR-013a~c-1)

**사전 계산 테이블이다.** 매 요청마다 3,000건을 집계하면 FR-026a에 불리하고, 무엇보다
**셀 크기 30 미만을 실수로 노출할 위험**이 생긴다. 적재 시점에 30 미만을 아예 제외해 넣으면
런타임에서 재식별 위험이 구조적으로 차단된다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `dist_id` | `int` PK AI | |
| `dist_type` | `enum('BURDEN_LEVEL','FEATURE_CATEGORY')` | FR-013c-1의 두 단위 |
| `feature` | `varchar(64)` NULL | `BURDEN_LEVEL`이면 NULL |
| `category_value` | `smallint` | 구간값 또는 응답 범주값 |
| `n` | `int` | **CHECK (n >= 30)** — FR-013c를 스키마로 강제 |
| `pct` | `decimal(5,2)` | |

**교차표를 만들 수 없는 구조** — 컬럼이 `feature` 하나뿐이라 두 변수를 결합한 행을 넣을 수
없다. FR-013c-1의 "교차표 금지"를 주석이 아니라 스키마로 못박은 것이다.

### 3.9 `cb_salt_v1` — 솔트 교체 이력 (FR-037)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `salt_id` | `int` PK AI | |
| `salt_value` | `varbinary(32)` | **애플리케이션 외부에 노출 금지** |
| `active_from`·`active_to` | `datetime` | 분기 1회 교체 |

교체 후 이전 솔트의 해시와 연결 불가 — 이는 별도 조치가 아니라 해시 함수의 성질로 자동 성립한다.

---

## 4. 관측·수집 (분리 저장소)

### 4.1 `cb_event_log_v1` — 익명 집계 로그 (FR-027~FR-030)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `event_id` | `bigint` PK AI | |
| `session_id` | `char(36)` | 1회용 UUIDv4(FR-029) |
| `event_type` | `varchar(40)` | FR-027이 열거한 종류만 |
| `occurred_at` | `datetime` | |
| `duration_ms` | `int` NULL | 진단 처리 소요(SC-018) |
| `model_version` | `varchar(20)` NULL | |
| `region_code` | `char(5)` NULL | **시군구 단위까지만**(FR-028) |
| `burden_level` | `tinyint` NULL | 판정 구간 또는 판정 불가 |
| `consent_training` | `boolean` NULL | 동의율 관측(성공 기준 아님 — spec Risks) |

`INDEX (occurred_at)` · `INDEX (event_type, occurred_at)`

**저장 금지 항목(FR-028)** — 이름·연락처·계정, 별명, IP, 개별 문항 응답, 사전 입력 3항목,
위경도 좌표. 스키마에 해당 컬럼이 아예 없어야 실수로 넣을 수 없다.

**보존 12개월(FR-030)** — `occurred_at` 기준 일 배치 삭제. 스케줄러는 Node의 `node-cron` 또는
운영체제 cron으로 두며(원칙 V — 컨테이너 없이), 삭제 실행 이력을 남긴다.

### 4.2 `cb_training_response_v1` — 학습용 응답 (FR-031~FR-035)

**동의한 제출만 들어온다**(FR-031 개정판). 미동의 제출은 이 테이블에 어떤 행도 만들지 않는다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `response_id` | `bigint` PK AI | |
| `question_set_version` | `varchar(20)` | 응답 해석에 필요 |
| `answers_json` | `json` | 선정 문항 응답값 |
| `self_report_label` | `tinyint` | 자가보고 부담(정답 라벨, FR-008a) |
| `submitted_at` | `datetime` | **초 단위 절삭** |
| `survey_duration_sec` | `int` | |
| `predicted_level` | `tinyint` NULL | 판정 결과. 판정 불가는 NULL |
| `model_version` | `varchar(20)` | |
| `submitter_hash` | `binary(32)` | FR-036 · 원본 IP 미보관 |
| `salt_id` | `int` FK → `cb_salt_v1` | 어느 솔트로 만든 해시인지 |

**`session_id`가 없다** — FR-032를 성립시키는 핵심이다. `cb_event_log_v1`과 조인할 키가 존재하지 않는다.

**저장 금지(FR-034)** — 자유 입력 텍스트, 위경도, 사전 입력 3항목. 역시 컬럼을 두지 않는다.

**보존 36개월(FR-035)** — `submitted_at` 기준 배치 파기.

**삭제권(FR-025)** — 결과 화면을 벗어나기 전까지만 취소할 수 있다. 구현은 **제출 시 즉시 저장하지
않고 결과 응답에 1회용 취소 토큰을 실어 보내는 방식**이 아니라, **저장하되 토큰으로 삭제**하는
방식을 쓴다. 전자는 세션 이탈 시 데이터를 잃고, 후자는 취소 창이 닫히면 토큰이 폐기되어
사후 특정이 불가능해진다(spec FR-025의 "익명이라 사후 특정 불가" 전제와 일치).

---

## 5. 클라이언트 상태 (서버 저장 없음)

| 항목 | 저장소 | 수명 | 근거 |
|---|---|---|---|
| 진행 중 응답·진행 위치 | `localStorage` | 24시간 / 제출 / "새로 시작" | FR-008-1, FR-008-2 |
| 별명 | `sessionStorage` | 탭 종료 시 소멸 | FR-002d |
| 대상자 연령·돌봄 대상 수 | 메모리(Pinia) | 결과 표시까지 | FR-002e, FR-021g |

**연령을 `localStorage`에 두지 않는 이유** — FR-002e가 "보관해서는 안 된다"고 명시한다.
진행 상태 복구 대상에서도 제외해, 재접속 시 다시 입력받거나 FR-021i(연령 없음 경로)로 처리한다.

---

## 6. 검증 규칙 요약

| 규칙 | 적용 지점 | 위반 시 |
|---|---|---|
| `care_burden ∈ {1..5}`, 1=최고부담 | 추론기·표시 매핑 | 테스트 실패(R-11 필수 회귀) |
| 모델 `features` 순서 = `selection_vN.json` | 서버 기동 시 | 기동 실패 |
| 미응답 문항 존재 | 제출 API | 400 + 해당 문항 번호 반환(FR-007) |
| 미동의 제출 | 학습 저장 경로 | 저장 스킵(FR-031·FR-033) |
| `cb_reference_dist_v1.n >= 30` | 적재 배치 + CHECK | 적재 거부(FR-013c) |
| 판정 불가 | 기여 요인·비교·과소추정 안내 | 모두 미표시(FR-011c·FR-013d·FR-010f) |
| 판정 불가 | 즉시 안내 | **표시하되 구분 문구 필수**(FR-021j·FR-021j-1) |
| `phone IS NULL` | 기관 카드 | 통화 버튼 숨김 |
