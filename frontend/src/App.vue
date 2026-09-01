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
      <RouterLink to="/" class="brand"><span class="brand__mark">곁</span>_돌봄의 무게를 읽다</RouterLink>
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

  <main id="main">
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
  color: var(--ink); text-decoration: none; font-size: 17px; font-weight: 700;
  font-family: var(--font-serif, inherit); letter-spacing: 0; word-break: keep-all;
}
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
