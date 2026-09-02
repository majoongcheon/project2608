<script setup lang="ts">
// 추론 서비스에 연결하지 못했을 때 (설계 4.9.4).
//   판정 불가(FR-009a)와 다른 화면이다 — 부담 수준과 무관한 일시적 장애다.
//   기관 안내는 이 아래에 그대로 나온다.
defineProps<{ name: string; notice: string }>();
</script>

<template>
  <section class="unavailable" aria-label="진단 안내">
    <p class="unavailable__who">{{ name }}님께 드리는 안내</p>
    <p class="unavailable__title">지금은 진단 결과를 드릴 수 없습니다</p>
    <p class="unavailable__body">{{ notice }}</p>
  </section>
</template>

<style scoped>
.unavailable { background: var(--surface); border: 1px solid var(--hairline);
  border-radius: var(--radius); padding: var(--sp-lg); }
.unavailable__who { font-size: 14px; color: var(--muted); margin: 0 0 var(--sp-sm); }
.unavailable__title { font-size: 22px; font-weight: 700; color: var(--ink);
  margin: 0 0 var(--sp-sm); }
.unavailable__body { margin: 0; font-size: 16px; }
</style>
