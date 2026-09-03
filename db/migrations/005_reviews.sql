-- 005_reviews.sql — 이용 후기 소통방 (2026-09-03)
--
-- 서비스를 실제로 이용해 본 사람들이 기관에 대해 서로 이야기하는 자리다.
-- 글이 공유되어야 '소통'이 되므로 브라우저가 아니라 서버에 둔다.
--
-- ★ 원칙 III(개인 식별 정보 미보관)를 지키는 방식
--   저장 금지 항목은 **컬럼 자체를 두지 않는다** — 이름·연락처·계정·IP·
--   위경도 컬럼이 여기에 없다. 남는 것은 기관 번호, 스스로 적은 별명,
--   별점, 본문, 시각뿐이다.
--
--   owner_token 은 사람을 가리키는 값이 아니라 **글 하나의 열쇠**다.
--   브라우저가 무작위로 만들어 자기 저장소에 넣어 두고, 자기가 쓴 글을
--   지울 때만 되돌려 준다. 서버는 이 값으로 사람을 찾을 수 없고, 같은
--   사람의 글끼리 묶을 수도 없다(글마다 새로 만든다).
--
-- ★ cb_event_log_v1 · cb_training_response_v1 과 조인할 수 있는 컬럼을
--   만들지 않는다(FR-032 의 취지). session_id 를 여기에 두지 않는 이유다.

CREATE TABLE IF NOT EXISTS cb_facility_review_v1 (
  review_id     BIGINT NOT NULL AUTO_INCREMENT,
  facility_id   BIGINT NOT NULL,
  nickname      VARCHAR(20) NOT NULL,      -- 스스로 적은 별명. 실명 요구 안 함
  rating        TINYINT NOT NULL,          -- 1~5, 클수록 좋았다는 뜻
  body          VARCHAR(600) NOT NULL,
  owner_token   CHAR(36) NOT NULL,         -- 글 하나의 삭제 열쇠 (사람 식별자 아님)
  created_at    DATETIME NOT NULL,
  is_hidden     TINYINT(1) NOT NULL DEFAULT 0,   -- 신고 처리용. 지우지 않고 가린다
  PRIMARY KEY (review_id),
  KEY idx_rv_facility (facility_id, created_at),
  KEY idx_rv_recent (created_at),
  CONSTRAINT chk_rv_rating CHECK (rating BETWEEN 1 AND 5)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
