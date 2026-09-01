-- 003_observability.sql — 관측·수집 (FR-027~FR-037)
--
-- ★ 이 두 테이블은 공통 컬럼을 하나도 갖지 않는다 (FR-032, 원칙 III).
--   cb_event_log_v1        : session_id 있음 · 응답 내용 없음
--   cb_training_response_v1: 응답 내용 있음 · session_id 없음
--   조인 키가 존재하지 않아야 저장소 분리가 구조적으로 성립한다.
--   db/tests/separation.test.ts 가 컬럼 교집합이 공집합인지 검증한다.

-- ── 4.1 익명 집계 로그 (FR-027~FR-030) ──────────────────────────────
--   저장 금지(FR-028): 이름·연락처·계정, 별명, IP, 개별 문항 응답,
--   사전 입력 항목 값, 위경도 좌표 — 해당 컬럼을 아예 두지 않는다.
CREATE TABLE IF NOT EXISTS cb_event_log_v1 (
  event_id         BIGINT NOT NULL AUTO_INCREMENT,
  session_id       CHAR(36) NOT NULL,
  event_type       VARCHAR(40) NOT NULL,
  occurred_at      DATETIME NOT NULL,
  question_no      SMALLINT NULL,
  duration_ms      INT NULL,
  model_version    VARCHAR(20) NULL,
  region_code      CHAR(5) NULL,          -- 시군구 단위까지만
  burden_level     TINYINT NULL,          -- 판정 구간, 판정 불가는 NULL
  is_undecidable   TINYINT(1) NULL,
  consent_training TINYINT(1) NULL,
  PRIMARY KEY (event_id),
  KEY idx_ev_time (occurred_at),
  KEY idx_ev_type (event_type, occurred_at),
  KEY idx_ev_session (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 4.2 학습용 응답 (FR-031~FR-035) ─────────────────────────────────
--   동의한 제출만 들어온다(FR-031). 저장 금지(FR-034): 자유 입력 텍스트,
--   위경도, 사전 입력 항목(별명·연령·돌봄 대상 수) — 컬럼을 두지 않는다.
CREATE TABLE IF NOT EXISTS cb_training_response_v1 (
  response_id          BIGINT NOT NULL AUTO_INCREMENT,
  cancel_token         CHAR(36) NULL,      -- FR-025 취소 창. 창이 닫히면 NULL 로 폐기
  question_set_version VARCHAR(20) NOT NULL,
  answers_json         LONGTEXT NOT NULL,
  self_report_label    TINYINT NULL,
  submitted_at         DATETIME NOT NULL,  -- 초 단위 절삭 저장
  survey_duration_sec  INT NULL,
  predicted_level      TINYINT NULL,       -- 판정 불가는 NULL
  model_version        VARCHAR(20) NOT NULL,
  submitter_hash       BINARY(32) NULL,    -- SHA-256(IP+솔트). 원본 IP 미보관
  salt_id              INT NULL,
  PRIMARY KEY (response_id),
  UNIQUE KEY uk_cancel (cancel_token),
  KEY idx_tr_time (submitted_at),
  KEY idx_tr_hash (submitter_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
