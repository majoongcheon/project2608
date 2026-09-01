<script setup lang="ts">
// FR-001 — 두 메뉴를 동등한 비중으로. 사전 절차 없이 곧바로 진입(FR-002).
import { onMounted, ref } from 'vue';
import { useEventStore } from '../stores/events';
import { api } from '../services/apiClient';
const events = useEventStore();

// 문항 수는 FR-004c 로 도출되어 모델 버전마다 달라진다(오늘만 7→14→7 로 바뀌었다).
// 화면에 값으로 박지 않고 /config 에서 받아 온다. 실패하면 숫자 없이 나간다.
const questionCount = ref<number | null>(null);

onMounted(async () => {
  events.track('PRESURVEY_ENTER');
  try { questionCount.value = (await api.config()).questionCount ?? null; } catch { /* 숫자 없이 진행 */ }
});
</script>

<template>
  <div class="container stack">
    <h1>어떤 도움이 필요하신가요?</h1>

    <!-- 인사말 — 편지의 첫 문단 -->
    <div class="letter">
      <p>돌봄의 무게는 겉으로 잘 드러나지 않습니다.</p>
      <p>그래서 몇 가지만 여쭙고, 지금 어느 정도인지 함께 읽어 보려 합니다.</p>
      <p>정답을 가리는 자리가 아니니 편한 대로 답해 주세요.</p>
    </div>

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
        <span class="menu__meta">
          <template v-if="questionCount">질문 {{ questionCount }}개 · </template>약 3분
        </span>
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
        <span class="menu__meta">전국 시군구 · 지도와 목록</span>
      </RouterLink>
    </nav>

    <!-- 이용 흐름. 3번이 곧 지도 메뉴라 두 메뉴가 모두 담긴다(FR-001 동등 비중) -->
    <section class="flow" aria-label="이용 흐름">
      <h2 class="flow__h">진단은 이렇게 진행됩니다</h2>
      <ol class="flow__list">
        <li><b aria-hidden="true">1</b><span>몇 가지 질문에 답합니다.</span></li>
        <li><b aria-hidden="true">2</b><span>지금의 부담 수준과 <strong>그렇게 본 이유</strong>를 알려 드립니다.</span></li>
        <li><b aria-hidden="true">3</b><span>가까운 신청처를 지도로 안내해 드립니다.</span></li>
      </ol>
    </section>

    <!-- 맺음말 -->
    <div class="sign">
      <p class="sign__body">
        답해 주신 내용은 결과를 계산하는 데에만 쓰고, 개인을 알아볼 수 있는 형태로 남기지 않습니다.
      </p>
      <p class="sign__from">곁 드림</p>
      <p class="sign__src">2024년 전국 3,000가구 조사 자료를 바탕으로 만들었습니다.</p>
    </div>
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
/* 두 카드 모두 같은 자리에 같은 모양의 한 줄을 둔다 — FR-001 동등 비중 */
.menu__meta {
  margin-top: auto; padding-top: var(--sp-xs);
  font-size: 13px; color: var(--muted-soft); letter-spacing: .01em;
}

/* 인사말 — 편지의 첫 문단. 명조로 두어 본문과 결을 나눈다 */
.letter { font-family: var(--font-serif, inherit); color: var(--body); }
.letter p { margin: 0 0 var(--sp-xs); font-size: 16.5px; line-height: 1.95; word-break: keep-all; }
.letter p:last-child { margin-bottom: 0; }

/* 이용 흐름 */
.flow { border-top: 1px solid var(--hairline); padding-top: var(--sp-lg); }
.flow__h { font-size: 17px; margin: 0 0 var(--sp-md); }
.flow__list { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--sp-sm); }
.flow__list li { display: grid; grid-template-columns: auto 1fr; gap: var(--sp-md); align-items: baseline; }
.flow__list b {
  font-family: var(--font-serif, inherit); font-size: 14px; font-weight: 700;
  color: var(--primary); min-width: 1.4em;
}
.flow__list span { font-size: 15px; color: var(--body); word-break: keep-all; }

/* 맺음말 */
.sign { border-top: 1px solid var(--hairline); padding-top: var(--sp-lg); }
.sign__body { font-size: 14.5px; color: var(--muted); margin: 0 0 var(--sp-md); word-break: keep-all; }
.sign__from {
  font-family: var(--font-serif, inherit); font-size: 17px; font-weight: 700;
  color: var(--ink); text-align: right; margin: 0 0 var(--sp-sm);
}
.sign__src { font-size: 12.5px; color: var(--muted-soft); margin: 0; }
</style>
