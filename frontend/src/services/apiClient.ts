const BASE = import.meta.env.VITE_API_BASE ?? '/api/v1';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // init.headers 를 통째로 덮으면 Content-Type 이 사라진다(후기 삭제가
  // x-owner-token 을 함께 보내면서 드러났다). 기본값 위에 얹는다.
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  });
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(body.message ?? '요청에 실패했습니다.'), { body, status: res.status });
  return body as T;
}

export const api = {
  questions: () => request<any>('/questions'),
  config: () => request<any>('/config'),
  model: () => request<any>('/model'),
  regions: () => request<any>('/regions'),
  facilities: (q: Record<string, unknown>) => {
    const p = new URLSearchParams();
    for (const [k, v] of Object.entries(q)) if (v !== null && v !== undefined && v !== '') p.set(k, String(v));
    return request<any>(`/facilities?${p}`);
  },
  facility: (id: number) => request<any>(`/facilities/${id}`),
  report: (id: number, body: unknown) =>
    request<any>(`/facilities/${id}/reports`, { method: 'POST', body: JSON.stringify(body) }),
  diagnose: (body: unknown) => request<any>('/diagnoses', { method: 'POST', body: JSON.stringify(body) }),
  cancel: (token: string) => request<void>(`/diagnoses/${token}`, { method: 'DELETE' }),
  events: (body: unknown) => request<void>('/events', { method: 'POST', body: JSON.stringify(body) }),

  // 이용 후기 소통방 (2026-09-03). 로그인이 없어 "누가 썼는가"는 서버가 모른다 —
  // 글을 쓰면 서버가 ownerToken 을 돌려주고, 그 토큰을 가진 브라우저만 지울 수 있다.
  reviews: (limit = 30) => request<any>(`/reviews?limit=${limit}`),
  facilityReviews: (id: number) => request<any>(`/facilities/${id}/reviews`),
  writeReview: (id: number, body: unknown) =>
    request<any>(`/facilities/${id}/reviews`, { method: 'POST', body: JSON.stringify(body) }),
  deleteReview: (reviewId: number, ownerToken: string) =>
    request<void>(`/reviews/${reviewId}`, { method: 'DELETE', headers: { 'x-owner-token': ownerToken } }),
};
