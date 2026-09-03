<script setup lang="ts">
import { ref, onMounted } from 'vue';

// 편지지 폭 전환. 넓은 화면에서 640px 종이가 답답하다는 요청.
// :root 의 data-width 만 바꾸고 나머지 디자인은 그대로 둔다.
const wide = ref(false);
function applyWidth(v: boolean) {
  document.documentElement.dataset.width = v ? 'wide' : 'narrow';
  try { localStorage.setItem('cb.width', v ? 'wide' : 'narrow'); } catch { /* noop */ }
}
function toggleWidth() { wide.value = !wide.value; applyWidth(wide.value); }
onMounted(() => {
  let saved: string | null = null;
  try { saved = localStorage.getItem('cb.width'); } catch { /* noop */ }
  wide.value = saved ? saved === 'wide' : window.innerWidth >= 1024;
  applyWidth(wide.value);
});

import { RouterView, useRoute, useRouter } from 'vue-router';
import { computed } from 'vue';

const route = useRoute();
const router = useRouter();
const isHome = computed(() => route.name === 'home');
</script>

<template>
  <a class="skip" href="#main">본문으로 건너뛰기</a>
  <header class="top">
    <div class="top__inner container">
      <button v-if="!isHome" class="back" type="button" aria-label="이전 화면으로" @click="router.back()">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor"
             stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M14.5 5 8.2 11.3a1 1 0 0 0 0 1.4L14.5 19" />
        </svg>
      </button>
      <RouterLink to="/" class="brand">
        <!-- 포옹 — 뒤에서 감싸 안은 두 사람. 서비스 이름 "곁"의 그림 풀이다.
             장식이라 aria-hidden 으로 두고, 뜻은 옆 글자가 이미 말한다. -->
        <svg class="brand__hug" viewBox="0 0 36 30" aria-hidden="true">
          <!-- 뒤에 선 사람 — 안아 주는 쪽 -->
          <circle cx="22.2" cy="8" r="5.4" fill="var(--hug-back)" />
          <path d="M12.2 30c0-8.4 4.5-12.8 10-12.8S32.2 21.6 32.2 30Z" fill="var(--hug-back)" />
          <!-- 앞에 안긴 사람 -->
          <circle cx="12.6" cy="12.6" r="4.6" fill="var(--hug-front)" />
          <path d="M4 30c0-6.2 3.9-9.6 8.6-9.6S21.2 23.8 21.2 30Z" fill="var(--hug-front)" />
          <!-- 감싼 팔 — 이 획이 있어야 '나란히 섰다'가 아니라 '안았다'로 읽힌다 -->
          <path d="M25.4 18.6c1.9 3.4-.4 7.1-4.5 7.8-3.6.6-7-.1-9.9-1.7"
                fill="none" stroke="var(--hug-arm)" stroke-width="3.1" stroke-linecap="round" />
        </svg>
        <span class="brand__tx"><span class="brand__mark">곁</span>_돌봄의 무게를 읽다</span>
      </RouterLink>
      <button class="width" type="button" @click="toggleWidth"
              :aria-pressed="wide"
              :title="wide ? '모바일 모드로 보기' : '홈페이지 모드로 보기'">
        <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor"
             stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <template v-if="wide">
            <path d="M9 5v14M15 5v14" /><path d="M4 12h3M17 12h3" />
          </template>
          <template v-else>
            <path d="M4 5v14M20 5v14" /><path d="M8 12h8M8 12l2.5-2.5M8 12l2.5 2.5M16 12l-2.5-2.5M16 12l-2.5 2.5" />
          </template>
        </svg>
        <span class="width__tx">{{ wide ? '모바일 모드' : '홈페이지 모드' }}</span>
      </button>
    </div>
  </header>

  <!-- 에디토리얼 레이아웃(2026-09-03 개편). 15:40 부터 **모든 방**이 이 틀을
       쓴다 — 홈만 지면이고 나머지가 편지지라 방을 옮길 때마다 다른 사이트에
       들어간 것처럼 읽혔다(기획자 지적). theme-editorial.css 가 이 클래스
       아래에서 봉투 플랩·봉랍·여백선을 걷어내고 옛 부품을 지면 언어로 바꾼다. -->
  <main id="main" class="main--editorial">
    <RouterView />
  </main>

  <footer class="foot">
    <div class="container muted">
      <p>이 서비스는 참고 정보를 제공하며 공식 복지 자격 판정이 아닙니다.</p>
      <p>로그인 없이 이용하며 응답은 개인을 식별할 수 있는 형태로 저장하지 않습니다.</p>
    </div>
  </footer>
</template>

<style scoped>
/* FR-039 — 키보드 사용자를 위한 건너뛰기 링크 */
.skip {
  position: absolute; left: -9999px; top: 0; z-index: 100;
  background: var(--ink); color: #fff; padding: var(--sp-md) var(--sp-base); border-radius: 0 0 8px 0;
}
.skip:focus { left: 0; }
.top { border-bottom: 1px solid var(--hairline-soft); background: var(--canvas); position: sticky; top: 0; z-index: 10; }
.top__inner { display: flex; align-items: center; gap: var(--sp-md); padding-block: var(--sp-md); }
.brand {
  display: inline-flex; align-items: center; gap: var(--sp-sm);
  color: var(--ink); text-decoration: none; font-size: 17px; font-weight: 700;
  font-family: var(--font-serif, inherit); letter-spacing: 0; word-break: keep-all;
}
.brand__hug { width: 26px; height: 22px; flex: none; display: block; }
.brand__tx { display: inline-block; }
.brand__mark { color: var(--primary); }
.width {
  display: inline-flex; align-items: center; gap: 6px; margin-left: auto;
  background: none; border: 1px solid var(--hairline); border-radius: var(--radius-pill);
  padding: 6px 12px; min-height: 34px; cursor: pointer; color: var(--muted);
  font: inherit; font-size: 13px; flex: none;
}
.width:hover { background: var(--surface-soft); color: var(--ink); border-color: var(--border-strong); }
/* 좁은 화면에서는 폭을 바꿔도 달라지는 게 없다. 쓸모없는 단추를 두지 않는다. */
@media (max-width: 760px) { .width { display: none; } }
.back {
  display: inline-flex; align-items: center; justify-content: center;
  background: none; border: 1px solid var(--hairline); border-radius: var(--radius-pill);
  width: 40px; min-height: 40px; cursor: pointer; color: var(--ink); flex: none;
}
.back:hover { background: var(--surface-soft); }
main { min-height: 60vh; padding-block: var(--sp-lg); }
.foot { border-top: 1px solid var(--hairline-soft); background: var(--surface-soft); padding-block: var(--sp-lg); margin-top: var(--sp-section); }
.foot p { margin: 0 0 var(--sp-xs); }
</style>
