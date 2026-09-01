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
      <span aria-hidden="true">⚠</span> 주의가 필요한 결과입니다
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
.result__flag { font-size: 15px; font-weight: 700; color: var(--error-text); margin: 0 0 var(--sp-sm); }
.result__label { font-size: 30px; font-weight: 700; color: var(--ink); margin: 0 0 var(--sp-sm); line-height: 1.25; }
.result__desc { font-size: 16px; color: var(--body); margin: 0; }
</style>
