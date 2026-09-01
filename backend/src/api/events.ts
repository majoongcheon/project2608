import { Router } from 'express';
import { recordEvents } from '../services/eventService.js';
import { wrap } from '../middleware/errors.js';

export const eventsRouter = Router();

// POST /events — 익명 집계 (FR-027). 열거된 필드 외에는 저장하지 않는다(FR-028).
eventsRouter.post('/events', wrap(async (req, res) => {
  const { sessionId, events } = req.body ?? {};
  if (typeof sessionId !== 'string' || !Array.isArray(events)) {
    return res.status(204).end();      // 잘못된 형태여도 조용히 무시한다 (관측은 부가 기능)
  }
  await recordEvents(sessionId, events);
  res.status(204).end();
}));
