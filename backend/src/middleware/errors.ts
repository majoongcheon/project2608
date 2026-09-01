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
  // 오류 로그에 요청 IP 를 남기지 않는다 (FR-028, 원칙 III)
  console.error('[error]', err?.message ?? err);
  res.status(500).json({ error: 'INTERNAL', message: '처리 중 문제가 발생했습니다.' });
}

/** async 라우터의 예외를 errorHandler 로 넘긴다. */
export const wrap = (fn: (req: Request, res: Response) => Promise<any>) =>
  (req: Request, res: Response, next: NextFunction) => fn(req, res).catch(next);
