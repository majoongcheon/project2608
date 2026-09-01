<script setup lang="ts">
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
      <button v-if="!isHome" class="back" type="button" aria-label="이전 화면으로" @click="router.back()">←</button>
      <RouterLink to="/" class="brand">돌봄부담 진단 · 복지서비스 안내</RouterLink>
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
.brand { color: var(--ink); text-decoration: none; font-weight: 600; font-size: 15px; }
.back {
  background: none; border: 1px solid var(--hairline); border-radius: var(--radius-pill);
  width: 40px; min-height: 40px; font-size: 18px; cursor: pointer; color: var(--ink); flex: none;
}
.back:hover { background: var(--surface-soft); }
main { min-height: 60vh; padding-block: var(--sp-lg); }
.foot { border-top: 1px solid var(--hairline-soft); background: var(--surface-soft); padding-block: var(--sp-lg); margin-top: var(--sp-section); }
.foot p { margin: 0 0 var(--sp-xs); }
</style>
