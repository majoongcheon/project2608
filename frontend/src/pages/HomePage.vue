<script setup lang="ts">
// FR-001 — 두 메뉴를 동등한 비중으로. 사전 절차 없이 곧바로 진입(FR-002).
import { onMounted } from 'vue';
import { useEventStore } from '../stores/events';
const events = useEventStore();
onMounted(() => events.track('PRESURVEY_ENTER'));
</script>

<template>
  <div class="container stack">
    <h1>어떤 도움이 필요하신가요?</h1>
    <p class="muted">
      로그인이나 회원가입 없이 두 가지를 모두 이용하실 수 있습니다.
    </p>

    <nav class="menu" aria-label="주요 기능">
      <RouterLink class="menu__card" to="/diagnosis/start">
        <span class="menu__icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"
               stroke-linecap="round" stroke-linejoin="round">
            <rect x="4" y="2.75" width="16" height="18.5" rx="3.2" />
            <path d="M8 7.8h8M8 11.4h5" />
            <path d="M14.75 14.9c.6-.62 1.6-.62 2.2 0 .6.62.6 1.62 0 2.24L14.75 19.5l-2.2-2.36c-.6-.62-.6-1.62 0-2.24.6-.62 1.6-.62 2.2 0Z" />
          </svg>
        </span>
        <span class="menu__title">부담감 진단</span>
        <span class="menu__desc">몇 가지 질문에 답하시면 지금의 돌봄부담 수준과 그렇게 본 이유를 알려 드립니다.</span>
      </RouterLink>

      <RouterLink class="menu__card" to="/map">
        <span class="menu__icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"
               stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 21.2c0 0 6.6-5.4 6.6-10.4a6.6 6.6 0 1 0-13.2 0c0 5 6.6 10.4 6.6 10.4Z" />
            <circle cx="12" cy="10.4" r="2.5" />
          </svg>
        </span>
        <span class="menu__title">복지서비스 위치 · 연락처</span>
        <span class="menu__desc">우리 지역의 주간활동 · 청소년 방과후활동 신청 접수처를 지도와 목록으로 찾아 드립니다.</span>
      </RouterLink>
    </nav>
  </div>
</template>

<style scoped>
.menu { display: grid; gap: var(--sp-base); grid-template-columns: 1fr; }
@media (min-width: 640px) { .menu { grid-template-columns: 1fr 1fr; } }
.menu__card {
  display: flex; flex-direction: column; gap: var(--sp-sm);
  border: 1px solid var(--hairline); border-radius: var(--radius-lg);
  padding: var(--sp-lg); text-decoration: none; color: var(--body);
  background: var(--canvas); box-shadow: var(--shadow-soft);
}
.menu__card:hover { box-shadow: var(--shadow-card); border-color: var(--border-strong); }
.menu__icon { display: block; color: var(--primary); }
.menu__icon svg { width: 34px; height: 34px; display: block; }
.menu__title { font-size: 20px; font-weight: 700; color: var(--ink); }
.menu__desc { font-size: 15px; color: var(--muted); }
</style>
