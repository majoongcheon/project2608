import { Router } from 'express';
import { randomUUID } from 'node:crypto';
import { query, one, exec } from '../repositories/pool.js';
import { ApiError, wrap } from '../middleware/errors.js';

/**
 * 이용 후기 소통방 (2026-09-03)
 *
 * 로그인이 없는 서비스라 "누가 썼는가"를 서버가 알지 못한다. 그래서
 *   · 쓸 때  : 별명만 받는다. 서버가 owner_token 을 만들어 돌려준다.
 *   · 지울 때: 그 토큰을 가진 브라우저만 지울 수 있다.
 * 토큰은 사람이 아니라 **글 하나**를 가리키므로, 이것으로 같은 사람의
 * 글을 묶거나 신원을 찾을 수 없다(원칙 III).
 */
export const reviewsRouter = Router();

const MAX_BODY = 600;
const MAX_NICK = 20;

/** 후기에 개인 연락처가 섞여 들어오는 것을 막는다 — 본인도 남도 위험하다. */
const CONTACT = /(01[016-9][-\s.]?\d{3,4}[-\s.]?\d{4})|(\b\d{6}[-\s]?[1-4]\d{6}\b)|([\w.+-]+@[\w-]+\.[\w.]+)/;

function clean(s: unknown, max: number): string {
  return String(s ?? '').replace(/\s+/g, ' ').trim().slice(0, max);
}

function toCard(r: any) {
  return {
    reviewId: Number(r.review_id),
    facilityId: Number(r.facility_id),
    facilityName: r.facility_name ?? null,
    nickname: r.nickname,
    rating: Number(r.rating),
    body: r.body,
    createdAt: r.created_at instanceof Date ? r.created_at.toISOString() : String(r.created_at),
  };
}

// GET /reviews — 최근 후기 (소통방 첫 화면)
reviewsRouter.get('/reviews', wrap(async (req, res) => {
  const limit = Math.min(Number(req.query.limit ?? 30), 100);
  const rows = await query(
    `SELECT r.review_id, r.facility_id, r.nickname, r.rating, r.body, r.created_at,
            f.name AS facility_name
       FROM cb_facility_review_v1 r
       LEFT JOIN cb_facility_v1 f ON f.facility_id = r.facility_id
      WHERE r.is_hidden = 0
      ORDER BY r.created_at DESC
      LIMIT ?`, [limit]);
  res.json({ reviews: rows.map(toCard) });
}));

// GET /facilities/:id/reviews — 한 기관의 후기와 평균
reviewsRouter.get('/facilities/:id/reviews', wrap(async (req, res) => {
  const facilityId = Number(req.params.id);
  if (!Number.isInteger(facilityId)) throw new ApiError(400, 'BAD_ID', '기관 번호가 올바르지 않습니다.');

  const rows = await query(
    `SELECT review_id, facility_id, nickname, rating, body, created_at
       FROM cb_facility_review_v1
      WHERE facility_id = ? AND is_hidden = 0
      ORDER BY created_at DESC
      LIMIT 100`, [facilityId]);

  // 후기가 적을 때 평균은 오해를 부른다. 개수를 항상 함께 낸다.
  const n = rows.length;
  const avg = n ? Number((rows.reduce((a: number, r: any) => a + Number(r.rating), 0) / n).toFixed(1)) : null;
  res.json({ facilityId, count: n, averageRating: avg, reviews: rows.map(toCard) });
}));

// POST /facilities/:id/reviews — 후기 남기기
reviewsRouter.post('/facilities/:id/reviews', wrap(async (req, res) => {
  const facilityId = Number(req.params.id);
  if (!Number.isInteger(facilityId)) throw new ApiError(400, 'BAD_ID', '기관 번호가 올바르지 않습니다.');

  const exists = await one<any>('SELECT facility_id FROM cb_facility_v1 WHERE facility_id = ?', [facilityId]);
  if (!exists) throw new ApiError(404, 'FACILITY_NOT_FOUND', '기관을 찾을 수 없습니다.');

  const nickname = clean(req.body?.nickname, MAX_NICK) || '이름 없는 보호자';
  const body = clean(req.body?.body, MAX_BODY);
  const rating = Number(req.body?.rating);

  if (body.length < 5) {
    throw new ApiError(400, 'BODY_TOO_SHORT', '후기를 다섯 글자 이상 적어 주세요.');
  }
  if (!Number.isInteger(rating) || rating < 1 || rating > 5) {
    throw new ApiError(400, 'BAD_RATING', '별점을 1에서 5 사이로 골라 주세요.');
  }
  // 연락처가 섞이면 저장하지 않고 되돌려 보낸다 — 지운 뒤 저장하면 본인이
  // 무엇이 지워졌는지 모른다. 무엇이 문제인지 말해 주고 고치게 한다.
  if (CONTACT.test(body) || CONTACT.test(nickname)) {
    throw new ApiError(400, 'CONTACT_IN_TEXT',
      '전화번호·이메일·주민등록번호처럼 개인을 알아볼 수 있는 정보는 담을 수 없습니다. 지우고 다시 올려 주세요.');
  }

  const ownerToken = randomUUID();
  const r = await exec(
    `INSERT INTO cb_facility_review_v1
       (facility_id, nickname, rating, body, owner_token, created_at)
     VALUES (?, ?, ?, ?, ?, NOW())`,
    [facilityId, nickname, rating, body, ownerToken]);

  res.status(201).json({
    reviewId: Number(r.insertId),
    // 이 값을 가진 브라우저만 이 글을 지울 수 있다. 서버는 다시 알려주지 않는다.
    ownerToken,
  });
}));

// DELETE /reviews/:id — 내가 쓴 글 지우기 (토큰을 가진 브라우저만)
reviewsRouter.delete('/reviews/:id', wrap(async (req, res) => {
  const reviewId = Number(req.params.id);
  const token = String(req.header('x-owner-token') ?? '');
  if (!Number.isInteger(reviewId) || !token) {
    throw new ApiError(400, 'BAD_REQUEST', '요청이 올바르지 않습니다.');
  }
  const r = await exec(
    'DELETE FROM cb_facility_review_v1 WHERE review_id = ? AND owner_token = ?', [reviewId, token]);
  if (!r.affectedRows) {
    throw new ApiError(403, 'NOT_OWNER', '이 글은 이 브라우저에서 지울 수 없습니다. 쓴 브라우저에서 지워 주세요.');
  }
  res.status(204).end();
}));
