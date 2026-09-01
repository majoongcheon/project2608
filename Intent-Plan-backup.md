# Intent - Plan

[웹스택] Vue.js + Node.js

# Vue.js + Node.js

현대적인 웹 개발 패턴을 따르는 풀스택 애플리케이션입니다. 프론트엔드와 백엔드가 분리된 구조로, REST API를 통해 데이터를 주고받습니다.

**프론트엔드**
- Vue.js 3 (v3.4+): Composition API 기반 컴포넌트
- TypeScript (v5.x): 정적 타입 지원
- Vite (v5.x): 빠른 개발 서버 및 빌드 도구
- Pinia (v2.x): 상태 관리

**백엔드**
- Node.js (v20 LTS): JavaScript 서버 런타임
- Express.js (v4.x): 웹 프레임워크
- TypeScript (v5.x): 타입 안전성
- mysql2 (v3.x): MariaDB 연결 드라이버

**데이터베이스 기술**
- MariaDB: MySQL 호환 관계형 DB
- mysql2 드라이버: Promise 기반 비동기 쿼리
- SQL 쿼리 기반 데이터 조작

※ 실제 연결 정보는 [데이터베이스 설정]을 참고하세요.

**개발환경/배포** — Docker 미사용 (문서 하단 절대규칙 · Constitution 원칙 V)
- 전개 방식: 프로젝트 폴더 안에서 코드 형식으로 전개 (컨테이너 패키징 없음)
- Nginx: 리버스 프록시, HTTPS
- GitLab CI/CD: 자동화 배포

**빠른 시작**
```bash
# 프론트엔드
cd frontend && npm install && npm run dev

# 백엔드
cd backend && npm install && npm run dev
```

[데이터베이스 설정]

# 팀 데이터베이스 연결 정보

- DB 서버: MariaDB A

**외부 접속 정보** (권장)
- 호스트: mis.iptime.org
- 포트: 13306
- 사용자명: pioneer3
- 데이터베이스: ABC8pioneer3
- 비밀번호: pioneer26

**연결 예시 (Node.js mysql2)**
```javascript
const mysql = require('mysql2/promise');

const connection = await mysql.createConnection({
  host: 'mis.iptime.org',
  port: 13306,
  user: 'pioneer3',
  password: 'pioneer26',
  database: 'ABC8pioneer3'
});
```

**연결 예시 (터미널)**
```bash
mysql -h mis.iptime.org -P 13306 -u pioneer3 -ppioneer26 ABC8pioneer3
```

**내부 접속 정보** (서버 내부용)
- 호스트: 192.168.0.91
- 포트: 3306

**주의: Homebrew mysql 바이너리 사용 금지**
로컬에 설치한 클라이언트 대신 위의 외부 접속 정보(`mis.iptime.org:13306`)로 직접 붙는다.

## 절대규칙 — Docker 미사용

* 서비스 구현을 위해 기술요소를 도입할 때 docker 이미지나 컨테이너 사용을 제한한다.
  프로젝트 폴더 내에서 코드 형식으로 전개하라.

**결정 기록 (2026-09-01)** — 이 문서에는 한때 *"반드시 Docker 컨테이너를 통해 접속하세요"*
라는 지시와 `docker exec` 예시가 위 절대규칙 바로 앞에 함께 있었다. 서로 정면으로 충돌하고
Constitution 원칙 V(컨테이너 없는 전개)와도 어긋나므로 **삭제했다.** DB 서버 호스트에서
MariaDB 가 어떻게 실행되는지는 DB 관리자의 영역이며, 이 프로젝트의 전개 방식과 무관하다.
