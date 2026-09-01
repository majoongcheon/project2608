# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]

**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]

**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]

**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]

**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]

**Project Type**: [e.g., library/cli/web-service/mobile-app/compiler/desktop-app or NEEDS CLARIFICATION]

**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]

**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]

**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution v1.0.0 기준. 각 항목에 통과/위반을 표시하고, 위반은 Complexity Tracking에
근거를 기록한다. NON-NEGOTIABLE 항목(I, III, V)은 기록으로도 면제되지 않는다.

| # | 게이트 | 확인 사항 | 결과 |
|---|--------|-----------|------|
| I | 근거 기반 판정 **(NON-NEGOTIABLE)** | 판정에 영향을 주는 값이 모두 실측 근거 또는 도출 규칙을 갖는가? target과 동일 구성개념 변수가 입력에서 배제되었는가? | |
| II | 설명가능성 | 모든 판정에 개별 근거가 동반되는가? 근거를 낼 수 없는 입력에 "판정 불가" 경로가 있는가? 내부 라벨이 이용자에게 노출되지 않는가? | |
| III | 최소 수집과 익명성 **(NON-NEGOTIABLE)** | 개인 식별 정보·원본 IP를 저장하지 않는가? 저장소별 목적·보존 기간·파기가 정의되었는가? 목적 확대에 고지·동의가 있고 거부해도 핵심 기능이 동작하는가? | |
| IV | 재현성과 외부화 | 모델·규칙·문항 집합에 버전이 있고 결과·로그에 기록되는가? 임계값과 문구가 설정으로 외부화되었는가? | |
| V | 컨테이너 없는 전개 **(NON-NEGOTIABLE)** | Docker 이미지·컨테이너를 도입하지 않는가? 모든 구성 요소가 프로젝트 폴더 내 코드·설정으로 전개되는가? | |
| — | 스택 준수 | Vue 3 + TS + Vite + Pinia / Node 20 + Express + TS / MariaDB(mysql2)를 벗어나지 않는가? | |
| — | 척도 방향 | 내부 라벨 1=최고부담, 5=부담 없음 전제가 임계값 비교와 화면 표시에 올바로 반영되었는가? | |
| — | 측정 가능성 | 모든 Success Criteria에 측정 수단이 배정되었는가? | |
| — | 독립 전달 | 각 User Story가 우선순위별로 독립 전달 가능한가? | |

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
