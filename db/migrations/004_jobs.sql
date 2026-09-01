-- 004_jobs.sql — 운영 배치 실행 이력 (FR-019a·FR-030·FR-035·FR-037)
CREATE TABLE IF NOT EXISTS cb_job_run_v1 (
  job_run_id  BIGINT NOT NULL AUTO_INCREMENT,
  job_name    VARCHAR(60) NOT NULL,
  started_at  DATETIME NOT NULL,
  finished_at DATETIME NULL,
  affected    INT NULL,
  status      ENUM('RUNNING','OK','FAILED') NOT NULL DEFAULT 'RUNNING',
  detail      VARCHAR(500) NULL,
  PRIMARY KEY (job_run_id),
  KEY idx_job (job_name, started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
