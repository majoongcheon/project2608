<script setup lang="ts">
// 판정 결과 표시 (FR-010·FR-010a·FR-010b·FR-041·FR-042)
//   ★ 구간 명칭 텍스트를 항상 표시한다 — 색상만으로 구분하지 않는다(FR-041).
//   ★ 경고는 색·아이콘만이 아니라 텍스트로도 알린다(FR-042).
//   ★ 내부 라벨 숫자는 애초에 API 응답에 없다(FR-010a).
defineProps<{ label: string | null; description: string | null; isWarning: boolean; name: string }>();
</script>

<template>
  <section class="result" :class="isWarning ? 'result--warn' : 'result--calm'"
           :aria-label="`${name}님의 진단 결과`">
    <p class="result__who">{{ name }}님의 진단 결과입니다</p>

    <!-- 경고 상태를 텍스트로도 알린다 (FR-042) -->
    <p v-if="isWarning" class="result__flag">
      <svg class="flag__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M12 4.3c.5 0 .97.27 1.22.72l6.35 11.2c.5.9-.14 2.01-1.22 2.01H5.65c-1.08 0-1.73-1.11-1.22-2.01l6.35-11.2c.25-.45.72-.72 1.22-.72Z" />
        <path d="M12 9.7v3.5M12 16.1h.01" />
      </svg>
      주의가 필요한 결과입니다
    </p>

    <p class="result__label">{{ label }}</p>
    <p class="result__desc">{{ description }}</p>
  </section>
</template>

<style scoped>
.result { border-radius: var(--radius-lg); padding: var(--sp-lg); border: 2px solid; }
/* 색은 보조 수단이다. 위 템플릿의 명칭·경고 문구가 정보를 전달한다. */
.result--warn { background: #fff4f1; border-color: var(--error-text); }
.result--calm { background: var(--surface-soft); border-color: var(--hairline); }
.result__who { font-size: 14px; color: var(--muted); margin: 0 0 var(--sp-sm); }
.result__flag {
  display: flex; align-items: center; gap: 7px;
  font-size: 15px; font-weight: 700; color: var(--error-text); margin: 0 0 var(--sp-sm);
}
.flag__icon { width: 19px; height: 19px; flex: none; }
.result__label { font-size: 30px; font-weight: 700; color: var(--ink); margin: 0 0 var(--sp-sm); line-height: 1.25; }
.result__desc { font-size: 16px; color: var(--body); margin: 0; }
</style>
