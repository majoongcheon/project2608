# project2608 — 돌봄부담 진단·복지연계 서비스

발달장애인 보호자 대상 돌봄부담 경량 진단 + 지도 기반 복지서비스 신청처 안내.

## 활성 기능

`001-care-burden-map` — `specs/001-care-burden-map/` (spec · plan · research · data-model · contracts · quickstart)

## 기술 스택

| 영역 | 스택 |
|---|---|
| 프론트엔드 | Vue 3.4 + TypeScript 5 + Vite 5 + Pinia 2 + Kakao Maps JS SDK |
| 백엔드 | Node.js 20 LTS + Express 4 + TypeScript 5 + mysql2 3 |
| 데이터베이스 | MariaDB 12.1.2 — `ABC8pioneer3` |
| 오프라인 학습 | Python 3.11 + scikit-learn + LightGBM + SHAP (**배포 대상 아님**) |
| 테스트 | Vitest · Playwright · pytest |

## 반드시 지킬 것

헌법(`.specify/memory/constitution.md` v1.0.0)의 NON-NEGOTIABLE 원칙이다.

1. **Docker 금지** (원칙 V) — 프로젝트 폴더 안 코드·선언적 설정으로만 전개한다.
2. **개인 식별 정보·원본 IP 미보관** (원칙 III) — 저장 금지 항목은 컬럼 자체를 두지 않는다.
   `cb_event_log_v1`과 `cb_training_response_v1`은 **공통 컬럼이 없어야** 한다(FR-032).
3. **근거 기반 판정** (원칙 I) — 문항 수·임계값을 값으로 못박지 않는다. 도출 규칙만 명세하고
   실측으로 확정한다. target(I13)과 동일 블록 6변수는 입력·문항 어디에도 쓰지 않는다.

### 척도 방향 — 가장 실수하기 쉬운 지점

`care_burden`은 **1이 최고부담, 5가 부담 없음**인 역방향 척도다.
숫자가 작을수록 부담이 크므로 임계값 비교는 `<=`다. 내부 라벨은 이용자에게 노출하지 않고
표시 명칭(최고부담군/고부담군/중간부담군/저부담군/부담 없음)으로만 낸다.

| 내부 라벨 | 표시 명칭 | 경고 | 즉시 안내 |
|---|---|---|---|
| 1 | 최고부담군 | O | O (+상담 강조) |
| 2 | 고부담군 | O | O |
| 3~5 | 중간/저/부담 없음 | X | X |
| 판정 불가 | 표시 안 함 | X | **O** (구분 문구 필수) |

## 데이터 실측 (2026-09-01 확인)

- `cb_dataset_v1` 3,000행 — train 2,398 / test 602, `cv_fold` 1~5 사전 배정
- 설명변수 38개 · target 분포 1:464 2:1,165 3:916 4:378 5:77 · 고부담(1~2) 54.3%
- `v_cb_tree_v1`(NULL 유지) / `v_cb_linear_v1`(-1 + isna) 두 뷰 준비됨
- `services_with_coords_std09` 1,283건 · 시군구 221/229 · 좌표 결측 0 · 전화 결측 58

**test 602건은 모든 결정이 끝난 뒤 단 한 번만 사용한다.**

## 명령

```bash
cd backend && npm run dev      # :3000
cd frontend && npm run dev     # :5173
cd ml && python -m ml.train --stage export
cd backend && npm run test:parity   # Python↔TS 추론 일치 (릴리스 게이트)
```

## 자격증명

`.env`에서만 읽는다(`.env.example` 참조). `.env`는 `.gitignore`로 제외되어 있다.
`Intent-Plan.md`와 `notebooks/`에 평문 기본값이 남아 있으니 복사하지 말 것.

<!-- MANUAL ADDITIONS START -->
<!-- 이 마커 사이의 내용은 자동 갱신 시 보존된다. -->
<!-- MANUAL ADDITIONS END -->
