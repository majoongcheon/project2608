# Specification Quality Checklist: 돌봄부담 경량 진단 및 지도 기반 복지서비스 안내

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-31
**Last Verified**: 2026-08-31 (최종본 전 항목 독립 재검증 완료)
**Feature**: [spec.md](../spec.md)
**Constitution**: v1.0.0

## Content Quality

- [x] CHK001 No implementation details (languages, frameworks, APIs)
- [x] CHK002 Focused on user value and business needs
- [x] CHK003 Written for non-technical stakeholders
- [x] CHK004 All mandatory sections completed

## Requirement Completeness

- [x] CHK005 No [NEEDS CLARIFICATION] markers remain
- [x] CHK006 Requirements are testable and unambiguous
- [x] CHK007 Success criteria are measurable
- [x] CHK008 Success criteria are technology-agnostic (no implementation details)
- [x] CHK009 All acceptance scenarios are defined
- [x] CHK010 Edge cases are identified
- [x] CHK011 Scope is clearly bounded
- [x] CHK012 Dependencies and assumptions identified

## Feature Readiness

- [x] CHK013 All functional requirements have clear acceptance criteria
- [x] CHK014 User scenarios cover primary flows
- [x] CHK015 Feature meets measurable outcomes defined in Success Criteria
- [x] CHK016 No implementation details leak into specification

## Internal Consistency

- [x] CHK017 우선순위 간 의존이 없다 (각 User Story가 독립 전달 가능)
- [x] CHK018 척도 방향(내부 라벨 1=최고부담)이 전 문서에서 일관된다
- [x] CHK019 연계 임계값이 전 문서에서 일관된다 (즉시 안내=고부담군 이상, 강조=최고부담군)
- [x] CHK020 구간 명칭 용어가 전 문서에서 일관된다

## Constitution Alignment (v1.0.0)

- [x] CHK021 원칙 I 근거 기반 판정 — 판정 영향 값이 실측 근거 또는 도출 규칙을 가진다
- [x] CHK022 원칙 II 설명가능성 — 개별 근거, 판정 불가 경로, 내부 라벨 비노출
- [x] CHK023 원칙 III 최소 수집과 익명성 — 저장 항목·목적·보존·파기, 동의와 거부 경로
- [x] CHK024 원칙 IV 재현성과 외부화 — 버전 부여·기록·공개, 설정 외부화
- [x] CHK025 원칙 V 컨테이너 없는 전개 — spec 범위에 배포 요소 없음 (plan 단계 검증 대상)
- [x] CHK026 품질 게이트: 모든 Success Criteria에 측정 수단이 배정되었다
- [x] CHK027 품질 게이트: User Story가 우선순위별로 독립 전달 가능하다

## Accessibility

- [ ] CHK028 접근성 요구사항이 정의되어 있다 — **이번 범위 외 (2026-08-31 결정, 실 서비스 운영 계획 없음)**

## Notes

**현재 판정 (2026-08-31)**: 28개 항목 중 **27개 통과, 1개 범위 외**. 변경안 그룹
①②③④⑤⑥⑦을 적용해 10개 항목(CHK003·006·007·009·010·013·015·017·026·027)이
해소되었다.

CHK028(접근성)은 이 프로젝트에 실제 서비스 운영 계획이 없으므로 **이번 범위에서
제외하기로 결정했다**(2026-08-31). 결정 사실과 향후 실 서비스 전환 시 정의해야 할 항목을
`spec.md`의 Assumptions "범위 제외 (확정)"에 기록했다.

**`/speckit.plan` 진입 가능.** 미결 항목 없음.

### 독립 재검증 (2026-08-31)

변경안 적용 과정에서 켠 체크박스를 그대로 신뢰하지 않고, 최종본 `spec.md`를 상대로 전 항목을
기계적으로 다시 확인했다. 앞서 "16개 항목 전부 통과"가 틀렸던 것이 자기 편집을 자기가
승인한 결과였기 때문이다.

| 검증 항목 | 방법 | 결과 |
|---|---|---|
| SC 전수 측정 수단 배정 | SC 정의 목록과 측정 수단 표의 SC 번호 집합 비교 | 18/18 배정, 누락 0 |
| 미해결 마커 | `NEEDS CLARIFICATION`·`TODO`·`TBD` 검색 | 0건 |
| 정량화 없는 형용사 | "충분한/적절한/직관적/가능한 한" 등 FR·SC 범위 검색 | 아래 예외 1건 외 없음 |
| 구현 기술 유출 | 스택·라이브러리·알고리즘 명칭 16종 검색 | 0건 |
| mandatory 섹션 | 헤딩 검색 | 3/3 존재 |
| FR 번호 연속성 | 선언 순서 추출 | FR-001~038, 결번·역순 없음 |
| 척도 방향 일관성 | "1~5단계"·"1이 최고부담" 출현 위치 점검 | 내부 라벨 정의 2곳에만 잔존(의도됨) |
| 임계값 일관성 | "고부담군 이상" 11회 및 임계값 언급 전수 확인 | 불일치 없음 |
| User Story별 시나리오 | 스토리별 Given 개수 집계 | US1 10 / US2 5 / US3 7 = 22건 |
| Edge Case 수 | 목록 항목 집계 | 16건 |

**재검증에서 발견해 수정한 결함 2건 (CHK020)**

- FR-011a — "동일한 판정 **단계**를 받은 보호자라도 … **단계별로** 고정된 안내 문구" →
  "판정 **구간**", "**구간별로**"로 정정. 구간 명칭 도입(FR-010a) 후 남은 잔재였다.
- Assumptions — "부담 **단계** = 즉시 안내 발동 임계값" → "부담 **구간**"으로 정정.

**의도적으로 남긴 표현**

- FR-009a·Edge Case의 "학습 데이터에서 **충분히** 관측되지 않아" — 형용사이나 FR-009b가
  "학습 데이터로 보정해 도출하고 검증 결과를 문서화"라는 도출 규칙을 명시하므로 헌법 원칙 I의
  요건을 충족한다. CHK006 통과로 판정한다.
- Clarifications(23행)와 Assumptions(306행)의 "단계" 표기 — 전자는 과거 결정의 이력 기록,
  후자는 내부 라벨의 정의다. 이용자 노출 문구가 아니므로 정정 대상이 아니다.

### 적용된 변경 (그룹 ①②③④⑤⑥⑦)

- **①** 측정 수단 표에 SC-013(익명 집계 로그), SC-014·SC-015(데이터 표본 점검) 배정 → CHK007·CHK026 해소
- **③** "진단 품질" 그룹에 `macro F1`·`재현율` 평문 해설 삽입 → CHK003 해소
- **⑤** User Story 1에 Acceptance Scenario 6~10 신설(자가보고 문항, 구간 명칭·경고, 판정 불가,
  비교 표시, 학습 미동의) → CHK009·CHK013 해소. 함께 발견된 불일치 2건 정정 —
  시나리오 2와 US1 본문의 "1~5단계" 표기를 "다섯 구간"으로 교체(FR-010a와 충돌하던 부분)
- **⑦** Edge Case 5건 추가(학습 미동의, 자가보고 문항 미응답, 솔트 교체 경계, 비교 항목 전무,
  모델 버전 교체 후 재방문) → CHK010 해소. 스크린리더 항목은 그룹 ⑧과 함께 보류
- **②** FR-013c의 "충분한"을 **최소 셀 크기 30건**으로 정량화 → CHK006 해소.
  FR/SC 전체를 재스캔해 정량화되지 않은 형용사가 남지 않음을 확인했다
- **④** User Story 1의 Independent Test에 FR-014를 P3 범위로 명시해 검증에서 제외하고,
  FR-014 본문에도 P3 소속을 표기 → CHK017·CHK027 해소. FR 번호는 이동하지 않아
  외부 참조가 깨지지 않는다
- **⑥** Success Criteria 3건 신설 → CHK015 해소
  - SC-016 판정 불가 — 발생 비율 10% 이하이면서, 해당 구간의 오분류율이 판정 구간보다 높음
  - SC-017 참조 집단 비교 유용성 70% 이상
  - SC-018 응답 시간 95 백분위 3초 이내 (FR-026a에서 이관)
  - 세 지표 모두 측정 수단 표에 배정. 학습 이용 동의율은 **의도적으로 SC로 만들지 않았다** —
    합격선을 걸면 동의를 유도하려는 화면 설계 압력이 생겨 "거부해도 불이익 없음"(FR-033)과
    충돌한다. 대신 FR-027 로그의 관측 대상에 동의 여부를 추가하고 Risks에서 추적한다

### 범위 외 항목 (CHK028)

실제 서비스로 운영할 계획이 없어 접근성 준수 요건을 이번 범위에서 제외했다. 준수 기준 선정,
담당 기관 확인, 스크린리더 이용자 평가는 수행하지 않는다.

향후 실 서비스로 전환하는 경우 아래 세 가지를 정하고 FR·SC로 반영해야 한다. 참고용 기록이며
현재 작업 항목이 아니다.

- 준수해야 할 접근성 기준과 등급
- 발달장애인 당사자의 직접 이용 포함 여부 (포함 시 "쉬운 말" 요구 수준이 달라진다)
- 스크린리더 이용자를 포함한 평가 방법

### CHK013의 잔여 사항 (통과 판정이나 기록해 둠)

운영성 요구사항(FR-019a 갱신 주기, FR-030 로그 보존, FR-035 학습 데이터 보존, FR-037 솔트
교체)은 이용자 흐름이 아니어서 Acceptance Scenario가 아닌 문서·설정 점검으로 검증한다.

### 이력

**1회차** — 지도 서비스 제공사 실명(카카오/네이버) 제거, Success Criteria에서 알고리즘·라이브러리
명칭 배제.

**2회차** — 미해결 마커 2건 해소. 문항 선별 모집단 확정, 기관 데이터 범위를 전국 229개 시군구로 확정.

**3회차 (`/speckit.clarify` 1차, 5문)** — Data Leakage 배제 규칙(FR-004b), 지표 측정 수단
이원화(FR-027~030), 완주 시간 목표 제거(구 SC-001), 조건부 문항 "해당사항 없음" 방식(FR-004d),
문항 수 고정 해제(FR-004c), P2 착수/정식 공개 기준 분리.

**4회차 (`/speckit.clarify` 2차, 5문)** — 개별 예측 기여도(FR-011a), 응답 시간 3초(FR-026a),
P3 임계값 재설정, 구간 명칭 표시(FR-010a), 판정 불가(FR-009a), 모델 버전 단위 재현성(FR-012),
자가보고 라벨 문항과 학습용 저장(FR-008a, FR-031~038), IP 솔트 해시(FR-036).

**4회차의 최대 발견** — 돌봄부담 라벨의 척도 방향이 **1=최고부담, 5=부담 없음**으로 확인되었다.
그 이전까지 spec은 정반대를 전제했고, P3 전체가 부담이 적은 이용자에게 즉시 안내를 보내는 구조로
작성되어 있었다. 실데이터 3중 교차검증(당사자 취업률 13.1%→48.1%, 자격증 보유율 4.3%→28.6%,
보호자 평균연령 59.4세→54.9세)으로 확정하고 전 문서를 정정했다.

**직전 판정의 오류** — 2회차 Notes는 "16개 항목 전부 통과"로 기록되어 있었으나, 당시에도
측정 수단이 없는 Success Criteria가 6개 있었고 Assumptions 내부에 모순이 있었다. 통과 판정이
과했다. 이 판정은 폐기한다.

### 계획 단계로 넘길 미결 사항 (스펙 흠결 아님)

- 기관 데이터 정기 갱신의 운영 주체와 주기 (FR-019a)
- 지도 서비스 제공자 선정
- 평가 프로토콜 (홀드아웃 / 교차검증) 확정
- 기여도 산출 방식 선정 (FR-026a의 3초 예산 안에서)
