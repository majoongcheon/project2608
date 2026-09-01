-- 001_schema.sql — 운영 기준 데이터 + 관측 저장소
-- data-model.md 3·4장. 기존 학습 데이터 객체는 변경하지 않는다.

-- ── 3.1 전국 229개 시군구 (FR-016a·FR-016b) ─────────────────────────
CREATE TABLE IF NOT EXISTS cb_region_v1 (
  region_code          CHAR(5)      NOT NULL,
  sido_name            VARCHAR(20)  NOT NULL,
  sigungu_name         VARCHAR(40)  NOT NULL,
  center_lat           DOUBLE       NULL,
  center_lng           DOUBLE       NULL,
  has_facility_data    TINYINT(1)   NOT NULL DEFAULT 0,
  metro_contact_name   VARCHAR(80)  NULL,
  metro_contact_phone  VARCHAR(30)  NULL,
  PRIMARY KEY (region_code),
  KEY idx_region_name (sido_name, sigungu_name),
  KEY idx_region_hasdata (has_facility_data)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 3.2 기관 (FR-017·FR-018·FR-019) ─────────────────────────────────
CREATE TABLE IF NOT EXISTS cb_facility_v1 (
  facility_id     INT          NOT NULL AUTO_INCREMENT,
  region_code     CHAR(5)      NULL,
  name            VARCHAR(160) NOT NULL,
  address         VARCHAR(255) NULL,
  address_detail  VARCHAR(255) NULL,
  phone           VARCHAR(30)  NULL,          -- 결측·형식오류는 NULL (빈 문자열 금지)
  lat             DOUBLE       NOT NULL,
  lng             DOUBLE       NOT NULL,
  updated_at      DATE         NULL,
  source_batch    VARCHAR(40)  NULL,
  PRIMARY KEY (facility_id),
  KEY idx_fac_coord (lat, lng),
  KEY idx_fac_region (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 3.3 기관 × 서비스 유형 (FR-021a·FR-021h) ────────────────────────
CREATE TABLE IF NOT EXISTS cb_facility_service_v1 (
  facility_id   INT NOT NULL,
  service_type  ENUM('DAY_ACTIVITY','AFTERSCHOOL_YOUTH') NOT NULL,
  program_name  VARCHAR(160) NULL,
  PRIMARY KEY (facility_id, service_type),
  KEY idx_fs_type (service_type, facility_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 3.4 정보 오류 신고 (FR-019b) ────────────────────────────────────
CREATE TABLE IF NOT EXISTS cb_facility_report_v1 (
  report_id    BIGINT NOT NULL AUTO_INCREMENT,
  facility_id  INT NOT NULL,
  report_type  ENUM('PHONE','ADDRESS','CLOSED','SERVICE','OTHER') NOT NULL,
  detail       VARCHAR(500) NULL,
  status       ENUM('RECEIVED','REVIEWING','RESOLVED','REJECTED') NOT NULL DEFAULT 'RECEIVED',
  created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  resolved_at  DATETIME NULL,
  PRIMARY KEY (report_id),
  KEY idx_rep_fac (facility_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 3.5 진단 문항 (FR-003·FR-004a·FR-005) ───────────────────────────
CREATE TABLE IF NOT EXISTS cb_question_v1 (
  question_set_version VARCHAR(20) NOT NULL,
  question_no          SMALLINT    NOT NULL,
  feature              VARCHAR(64) NOT NULL,
  original_item        VARCHAR(20) NULL,
  question_text        VARCHAR(300) NOT NULL,
  options_json         LONGTEXT    NOT NULL,
  has_not_applicable   TINYINT(1)  NOT NULL DEFAULT 0,
  explain_template     VARCHAR(300) NULL,
  is_self_report       TINYINT(1)  NOT NULL DEFAULT 0,
  PRIMARY KEY (question_set_version, question_no),
  KEY idx_q_feature (question_set_version, feature)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 3.6 외부화 설정 (FR-022 · 원칙 IV) ──────────────────────────────
CREATE TABLE IF NOT EXISTS cb_config_v1 (
  config_key   VARCHAR(60) NOT NULL,
  version      VARCHAR(20) NOT NULL DEFAULT 'v1',
  value_json   LONGTEXT    NOT NULL,
  active_from  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  reviewed_by  VARCHAR(60) NULL,
  reviewed_at  DATETIME    NULL,
  PRIMARY KEY (config_key, version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 3.7 모델 버전 (FR-012a·FR-012b) ─────────────────────────────────
CREATE TABLE IF NOT EXISTS cb_model_version_v1 (
  model_version        VARCHAR(20) NOT NULL,
  family               VARCHAR(40) NULL,
  question_set_version VARCHAR(20) NULL,
  macro_f1             DECIMAL(6,4) NULL,
  high_burden_recall   DECIMAL(6,4) NULL,
  undecidable_rate     DECIMAL(6,4) NULL,
  activated_at         DATETIME NULL,
  deactivated_at       DATETIME NULL,
  notes                TEXT NULL,
  PRIMARY KEY (model_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 3.8 참조 집단 분포 (FR-013a~c-1) ────────────────────────────────
--   교차표를 만들 수 없는 구조: feature 컬럼이 하나뿐이다.
CREATE TABLE IF NOT EXISTS cb_reference_dist_v1 (
  dist_id        INT NOT NULL AUTO_INCREMENT,
  dist_type      ENUM('BURDEN_LEVEL','FEATURE_CATEGORY') NOT NULL,
  feature        VARCHAR(64) NULL,
  category_value SMALLINT NOT NULL,
  n              INT NOT NULL,
  pct            DECIMAL(5,2) NOT NULL,
  PRIMARY KEY (dist_id),
  KEY idx_ref (dist_type, feature),
  CONSTRAINT chk_ref_min_cell CHECK (n >= 30)       -- FR-013c 를 스키마로 강제
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 3.9 솔트 교체 이력 (FR-037) ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS cb_salt_v1 (
  salt_id     INT NOT NULL AUTO_INCREMENT,
  salt_value  VARBINARY(64) NOT NULL,
  active_from DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  active_to   DATETIME NULL,
  PRIMARY KEY (salt_id),
  KEY idx_salt_active (active_from, active_to)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
