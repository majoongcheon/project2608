// 익명 집계 이벤트 (FR-027·FR-029)
//   세션 식별자는 이용 1회마다 새로 만드는 난수다. 이용자와 연결 가능한 값을 쓰지 않는다.
import { defineStore } from 'pinia';
import { ref } from 'vue';
import { api } from '../services/apiClient';

export const useEventStore = defineStore('events', () => {
  const sessionId = ref(crypto.randomUUID());
  const queue: any[] = [];
  let timer: number | undefined;

  function track(eventType: string, extra: Record<string, unknown> = {}) {
    queue.push({ eventType, occurredAt: new Date().toISOString(), ...extra });
    if (timer) return;
    timer = window.setTimeout(flush, 1500);
  }

  async function flush() {
    timer = undefined;
    if (!queue.length) return;
    const events = queue.splice(0, queue.length);
    try { await api.events({ sessionId: sessionId.value, events }); } catch { /* 관측 실패는 무시 */ }
  }

  function renew() { sessionId.value = crypto.randomUUID(); }

  return { sessionId, track, flush, renew };
});
