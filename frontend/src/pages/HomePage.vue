<script setup lang="ts">
// FR-001 — 두 메뉴를 동등한 비중으로. 사전 절차 없이 곧바로 진입(FR-002).
import { onMounted, ref } from 'vue';
import { useEventStore } from '../stores/events';
import { api } from '../services/apiClient';
const events = useEventStore();

// 문항 수는 FR-004c 로 도출되어 모델 버전마다 달라진다. 값으로 박지 않고 받아 온다.
const questionCount = ref<number | null>(null);

onMounted(async () => {
  events.track('PRESURVEY_ENTER');
  try { questionCount.value = (await api.config()).questionCount ?? null; } catch { /* 숫자 없이 진행 */ }
});
</script>

<template>
  <div class="container stack">
    <h1>어떤 도움이 필요하신가요?</h1>

    <!-- 인사말 -->
    <div class="letter">
      <p>돌봄의 무게는 겉으로 잘 드러나지 않습니다.</p>
      <p class="letter__lead">그래서 몇 가지만 여쭙고,<br />지금 어느 정도인지 함께 읽어 보려 합니다.</p>
      <p class="letter__soft">정답을 가리는 자리가 아니니 편한 대로 답해 주세요.</p>
    </div>

    <!-- 조사 결과. 근거이자 "혼자가 아니다" 라는 말이다.
         출처: 2024 발달장애인 일과 삶 실태조사 3,000가구 (1~2단계 1,629가구) -->
    <section class="stat" aria-label="조사 결과">
      <p class="stat__lead">2024년 전국 <b>3,000가구</b>에 물었습니다.</p>
      <p class="stat__dots" aria-hidden="true">
        <i class="on"></i><i class="on"></i><i class="on"></i><i class="on"></i><i class="on"></i>
        <i></i><i></i><i></i><i></i><i></i>
      </p>
      <p class="stat__body">
        열 가구 가운데 <b>다섯 이상</b>이 높은 돌봄부담을 안고 있었습니다.
        <span class="stat__fig">3,000가구 중 1,629가구 · 54.3%</span>
      </p>
      <p class="stat__note">힘든 것은 당신만의 일이 아닙니다.</p>
    </section>

    <nav class="menu" aria-label="주요 기능">
      <RouterLink class="menu__card" to="/diagnosis/start">
        <span class="menu__icon" aria-hidden="true">
          <svg viewBox="0 0 40 40">
            <rect x="9" y="5" width="22" height="30" rx="4" fill="var(--icon-fill)" />
            <rect x="9" y="5" width="22" height="30" rx="4" fill="none"
                  stroke="currentColor" stroke-width="1.7" />
            <path d="M14 13h12M14 19h8" fill="none" stroke="currentColor"
                  stroke-width="1.7" stroke-linecap="round" />
            <path d="M23.4 24.4c1-1.05 2.7-1.05 3.7 0 1 1.05 1 2.75 0 3.8L23.4 32l-3.7-3.8c-1-1.05-1-2.75 0-3.8 1-1.05 2.7-1.05 3.7 0Z"
                  fill="currentColor" />
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
          <svg viewBox="0 0 40 40">
            <path d="M20 35s11-9 11-17.5A11 11 0 1 0 9 17.5C9 26 20 35 20 35Z" fill="var(--icon-fill)" />
            <path d="M20 35s11-9 11-17.5A11 11 0 1 0 9 17.5C9 26 20 35 20 35Z"
                  fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" />
            <circle cx="20" cy="17" r="4.2" fill="currentColor" />
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
        로그인도 회원가입도 없습니다. 답해 주신 내용은 결과를 계산하는 데에만 쓰고,
        개인을 알아볼 수 있는 형태로 남기지 않습니다.
      </p>
      <p class="sign__from">곁 드림</p>
    </div>
  </div>
</template>

<style scoped>
/* ── 인사말 — 크기와 색으로 세 단을 만든다 ── */
.letter { color: var(--body); }
.letter p { margin: 0 0 var(--sp-sm); word-break: keep-all; }
.letter p:last-child { margin-bottom: 0; }
.letter__lead { font-size: 19px; line-height: 1.9; color: var(--ink); font-weight: 500; }
.letter__soft { font-size: 15px; color: var(--muted); }

/* ── 조사 결과 ── */
.stat {
  background: var(--surface-soft); border: 1px solid var(--hairline);
  border-left: 3px solid var(--accent); border-radius: var(--radius-sm);
  padding: var(--sp-lg) var(--sp-base);
}
.stat__lead { font-size: 14px; color: var(--muted); margin: 0 0 var(--sp-md); }
.stat__lead b { color: var(--ink); font-weight: 700; }
.stat__dots { display: flex; gap: 6px; margin: 0 0 var(--sp-md); flex-wrap: wrap; }
.stat__dots i {
  width: 15px; height: 15px; border-radius: 50%;
  border: 1.5px solid var(--border-strong); background: transparent;
}
.stat__dots i.on { background: var(--primary); border-color: var(--primary); }
.stat__body { font-size: 17px; line-height: 1.8; color: var(--body); margin: 0 0 var(--sp-sm); word-break: keep-all; }
.stat__body b { color: var(--primary-on-tint); font-weight: 700; font-size: 20px; }
.stat__fig { display: block; font-size: 13px; color: var(--muted-soft); margin-top: var(--sp-xs); }
.stat__note { font-size: 15px; color: var(--ink); font-weight: 600; margin: 0; }

/* ── 메뉴 ── */
.menu { display: grid; gap: var(--sp-base); grid-template-columns: 1fr; }
@media (min-width: 640px) { .menu { grid-template-columns: 1fr 1fr; } }
.menu__card {
  display: flex; flex-direction: column; gap: var(--sp-sm);
  border: 1px solid var(--hairline); border-radius: var(--radius-lg);
  padding: var(--sp-lg); text-decoration: none; color: var(--body);
  background: var(--canvas); box-shadow: var(--shadow-soft);
}
.menu__card:hover { box-shadow: var(--shadow-card); border-color: var(--border-strong); }
/* 아이콘 — 선만 있으면 비어 보인다. 옅은 살구빛 면을 깔고 그 위에 선을 얹은 뒤,
   한 부분(하트·핀 머리)만 꽉 채워 시선이 걸리게 한다. */
.menu__icon {
  --icon-fill: #f6ded1;
  display: inline-flex; align-items: center; justify-content: center;
  width: 54px; height: 54px; border-radius: 14px;
  background: var(--surface-strong); color: var(--primary);
}
.menu__icon svg { width: 34px; height: 34px; display: block; }
.menu__title { font-size: 20px; font-weight: 700; color: var(--ink); }
.menu__desc { font-size: 15px; color: var(--muted); line-height: 1.75; }
.menu__meta {
  margin-top: auto; padding-top: var(--sp-xs);
  font-size: 13px; color: var(--muted-soft);
}

/* ── 이용 흐름 ── */
.flow { border-top: 1px solid var(--hairline); padding-top: var(--sp-lg); }
.flow__h { font-size: 17px; color: var(--muted); font-weight: 600; margin: 0 0 var(--sp-md); }
.flow__list { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--sp-md); }
.flow__list li { display: grid; grid-template-columns: auto 1fr; gap: var(--sp-md); align-items: start; }
.flow__list b {
  display: inline-flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; border-radius: 50%; flex: none;
  background: var(--surface-strong); color: var(--primary-on-tint);
  font-size: 14px; font-weight: 700;
}
.flow__list span { font-size: 16px; color: var(--body); word-break: keep-all; }
.flow__list strong { color: var(--ink); font-weight: 700; }

/* ── 맺음말 ── */
.sign { border-top: 1px solid var(--hairline); padding-top: var(--sp-lg); }
.sign__body { font-size: 14px; color: var(--muted); margin: 0 0 var(--sp-md); word-break: keep-all; line-height: 1.75; }
.sign__from { font-size: 18px; font-weight: 700; color: var(--ink); text-align: right; margin: 0; }
</style>
