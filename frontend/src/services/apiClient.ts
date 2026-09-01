const BASE = import.meta.env.VITE_API_BASE ?? '/api/v1';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
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
};
