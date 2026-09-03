import type { Request, Response, NextFunction } from 'express';

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public extra?: any) {
    super(message);
  }
}

export function notFound(_req: Request, res: Response) {
  res.status(404).json({ error: 'NOT_FOUND', message: '요청한 자원을 찾을 수 없습니다.' });
}

export function errorHandler(err: any, _req: Request, res: Response, _next: NextFunction) {
  if (err instanceof ApiError) {
    return res.status(err.status).json({ error: err.code, message: err.message, ...(err.extra ?? {}) });
  }
  // 본문이 깨진 JSON 이거나 너무 크면 **보낸 쪽 잘못**이다. 500 으로 답하면
  // 서버가 고장난 것처럼 보이고, 무엇을 고쳐야 하는지도 알려 주지 못한다
  // (2026-09-03 점검에서 실제로 500 이 나왔다).
  if (err?.type === 'entity.parse.failed' || err instanceof SyntaxError) {
    return res.status(400).json({ error: 'BAD_JSON', message: '요청 본문을 읽을 수 없습니다.' });
  }
  if (err?.type === 'entity.too.large') {
    return res.status(413).json({ error: 'BODY_TOO_LARGE', message: '요청 본문이 너무 큽니다.' });
  }
  // 오류 로그에 요청 IP 를 남기지 않는다 (FR-028, 원칙 III)
  console.error('[error]', err?.message ?? err);
  res.status(500).json({ error: 'INTERNAL', message: '처리 중 문제가 발생했습니다.' });
}

/** async 라우터의 예외를 errorHandler 로 넘긴다. */
export const wrap = (fn: (req: Request, res: Response) => Promise<any>) =>
  (req: Request, res: Response, next: NextFunction) => fn(req, res).catch(next);
