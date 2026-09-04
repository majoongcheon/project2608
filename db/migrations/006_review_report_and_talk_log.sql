-- 006_review_report_and_talk_log.sql — 후기 신고 · 안내봇 미답변 질문 (2026-09-04)
--
-- 두 가지를 채운다.
--   ① 후기 신고 — 005 에서 is_hidden 컬럼만 만들어 두고 받는 자리를 안 만들었다.
--      누구나 볼 수 있는 글인데 가릴 통로가 없는 상태였다.
--   ② 안내봇이 답하지 못한 질문 — 무엇을 더 적어야 하는지 추측 대신 실측으로
--      정하기 위한 것이다. 답한 질문은 남기지 않는다.
--
-- ★ 저장소 분리(FR-032) — 두 테이블 모두 cb_event_log_v1 · cb_training_response_v1
--   과 조인할 수 있는 컬럼을 두지 않는다. session_id 가 여기에 없는 이유다.
--   db/scripts/verify.js 가 이것을 검사한다.

-- ── 6.1 후기 신고 ────────────────────────────────────────────────────
--   신고자를 식별하지 않는다. 이름·연락처·계정·IP 컬럼이 없다.
--   같은 사람이 반복해 누르는 것은 브라우저 쪽에서 막고(cb.reportedReviews),
--   서버는 누가 눌렀는지 알 필요가 없다 — 셀 수만 있으면 된다.
CREATE TABLE IF NOT EXISTS cb_review_report_v1 (
  report_id    BIGINT NOT NULL AUTO_INCREMENT,
  review_id    BIGINT NOT NULL,
  report_type  ENUM('ABUSE','PRIVACY','ADVERTISING','FALSE','OTHER') NOT NULL,
  detail       VARCHAR(300) NULL,
  created_at   DATETIME NOT NULL,
  PRIMARY KEY (report_id),
  KEY idx_rr_review (review_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 6.2 안내봇이 답하지 못한 질문 ────────────────────────────────────
--   답을 낸 질문은 남기지 않는다. fallback 으로 빠진 것만 글로 남긴다.
--
--   ★ 이 테이블은 이용자가 직접 쓴 글을 담는다. 그래서
--     · 누가 물었는지는 담지 않는다 — session_id·IP·별명 컬럼이 없다.
--     · 연락처 꼴이 섞이면 저장하지 않고 버린다(백엔드에서 거른다).
--     · 200자에서 자른다. 긴 사연은 안내봇에 넣을 규칙의 근거가 아니다.
--     · 화면의 안내 문구도 이 사실에 맞춰 고쳤다(guideBot talk-privacy).
--
--   ★ 시각을 날짜까지만 남기고 컬럼 이름도 다르게 둔다.
--     처음에 `occurred_at DATETIME` 으로 만들었더니 verify.js 가 잡아냈다 —
--     cb_event_log_v1 에 같은 이름의 컬럼이 있어, 같은 초에 찍힌 TALK_MESSAGE
--     이벤트와 이 글을 짝지을 수 있었다. 그 이벤트에는 session_id·시군구·판정
--     구간이 붙어 있으므로 사실상 연결 고리가 된다(FR-032 위반).
--     규칙을 무엇으로 채울지 정하는 데 시·분·초는 필요 없다. 날짜면 충분하다.
CREATE TABLE IF NOT EXISTS cb_talk_unanswered_v1 (
  unanswered_id BIGINT NOT NULL AUTO_INCREMENT,
  text          VARCHAR(200) NOT NULL,
  logged_on     DATE NOT NULL,          -- 날짜까지만. 시각 대조로 짝지을 수 없다
  PRIMARY KEY (unanswered_id),
  KEY idx_tu_day (logged_on)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
