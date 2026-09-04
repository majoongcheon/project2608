import { Router } from 'express';
import { exec } from '../repositories/pool.js';
import { ApiError, wrap } from '../middleware/errors.js';

/**
 * 정보 소통방 — 안내봇이 답하지 못한 질문만 모은다 (2026-09-04)
 *
 * 왜 남기나 — 규칙을 무엇으로 더 채울지 추측으로 정해 왔다. 실제로 무엇을
 * 물으시는지 모르면 다음 확장도 추측이 된다. 답을 낸 질문은 이미 규칙이
 * 있으니 남길 이유가 없고, **답하지 못한 것만** 남긴다.
 *
 * 무엇을 지키나
 *   · 누가 물었는지 담지 않는다 — session_id·IP·별명 컬럼이 테이블에 없다.
 *   · 연락처 꼴이 섞이면 저장하지 않고 조용히 버린다. 이용자에게는 알리지
 *     않는다 — 이건 이용자의 요청이 아니라 우리 쪽 수집이라, 실패를 오류로
 *     돌려주면 대화가 끊긴다.
 *   · 200자에서 자른다. 긴 사연은 규칙의 근거가 아니다.
 *   · 시각은 날짜까지만 남긴다. 처음엔 DATETIME 이었는데 verify.js 가 잡았다 —
 *     같은 초의 TALK_MESSAGE 이벤트(session_id·시군구·판정 구간이 붙어 있다)와
 *     짝지을 수 있었다. 규칙을 채우는 데 시·분·초는 필요 없다.
 *
 * 화면의 안내 문구도 이 사실에 맞춰 고쳤다(guideBot 의 talk-privacy·privacy).
 * "대화가 통째로 서버에 간다"는 말이 되지 않도록, 답한 것은 보내지 않는다.
 */
export const talkRouter = Router();

const MAX_TEXT = 200;
const CONTACT = /(01[016-9][-\s.]?\d{3,4}[-\s.]?\d{4})|(\b\d{6}[-\s]?[1-4]\d{6}\b)|([\w.+-]+@[\w-]+\.[\w.]+)/;

talkRouter.post('/talk/unanswered', wrap(async (req, res) => {
  const text = String(req.body?.text ?? '').replace(/\s+/g, ' ').trim().slice(0, MAX_TEXT);

  // 너무 짧으면 무엇을 물으신 건지 알 수 없어 규칙의 근거가 못 된다.
  if (text.length < 2) throw new ApiError(400, 'TEXT_TOO_SHORT', '남길 내용이 없습니다.');

  // 연락처가 섞였으면 버린다. 받은 척은 하지 않고 그대로 알린다.
  if (CONTACT.test(text)) {
    res.status(202).json({ stored: false, reason: 'CONTACT_IN_TEXT' });
    return;
  }

  await exec(
    'INSERT INTO cb_talk_unanswered_v1 (text, logged_on) VALUES (?, CURDATE())', [text]);
  res.status(201).json({ stored: true });
}));
