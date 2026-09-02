# project2608 — 돌봄부담 진단·복지연계 서비스

발달장애인 보호자 대상 돌봄부담 경량 진단 + 지도 기반 복지서비스 신청처 안내.

## 활성 기능

`001-care-burden-map` — `specs/001-care-burden-map/` (spec · plan · research · data-model · contracts · quickstart)

## 기술 스택

| 영역 | 스택 |
|---|---|
| 프론트엔드 | Vue 3.4 + TypeScript 5 + Vite 5 + Pinia 2 + Leaflet(OpenStreetMap · 키 불필요) |
| 백엔드 | Node.js 20 LTS + Express 4 + TypeScript 5 + mysql2 3 |
| 데이터베이스 | MariaDB 12.1.2 — `ABC8pioneer3` |
| 오프라인 학습 | Python 3.11 + scikit-learn + LightGBM + SHAP (**배포 대상 아님**) |
| 테스트 | Vitest · Playwright · pytest |

## 작성자 귀속 — 세션마다 반드시 확인

팀 4명이 **접속 계정 `pioneer3` 와 이 폴더를 공유**한다(계정은 바꿀 수 없다). 그래서
OS 계정·MAC·호스트명·git 작성자·**Claude 기억 저장소까지 전부 동일**하다. 사람을 가르는
단서는 **그 세션에서 본인이 밝힌 이름 하나뿐**이다.

1. **세션 사용자를 추측하지 않는다.** 이전 세션에서 확인된 이름이나 기억을 근거로 단정하지
   말고, 귀속이 필요한 일(작업기록·커밋·산출물 접두어) 전에 **먼저 묻는다.**
2. 이름을 들으면 장부에 넣는다 — `bash scripts/JSG-session-author.sh set <이름>`.
   확인은 `get`. `session_id` 로 칸이 나뉘어 세션끼리 덮어쓰지 않는다.
3. **기억(memory)에 "이 노트북 사용자는 X" 를 적지 않는다.** 저장소가 공유라 다른 세션이
   덮어쓰고, 다음 사람을 오인하게 만든다(2026-09-02 실제 발생).
4. 커밋은 `git -c user.name="<이름>" commit`. **`git config --local` 은 건드리지 않는다**
   — `.git/config` 가 공유되어 남의 커밋까지 그 이름으로 찍힌다.
5. 작업기록은 `docs/작업기록/<이름>.md` 에 `HH:MM`(KST) 시간 태그와 함께 남긴다.
   여러 세션이 같은 폴더를 동시에 고치므로 **파일은 덮어쓰지 말고 이어 붙인다.**

배경과 검증 근거는 `docs/작업기록/기기-대조표.md`.

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
