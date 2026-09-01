<script setup lang="ts">
// 기여 요인 (FR-011·FR-011a·FR-011-1)
//   ★ 임계값 미만인 요인은 "판정에 일부 영향을 준 요인"으로 구분해 표시한다.
//   ★ 기여도 크기를 숫자로 표기하지 않는다 — 산출이 Saabas 폴백이므로 순위와 강·약만 쓴다
//     (research.md R-3 의 폴백 규칙).
defineProps<{ items: { text: string; isMinor: boolean }[] }>();
</script>

<template>
  <section class="stack">
    <h2>이렇게 본 이유</h2>
    <ul class="list">
      <li v-for="(c, i) in items" :key="i" class="item" :class="{ 'item--minor': c.isMinor }">
        <span class="item__tag">{{ c.isMinor ? '일부 영향' : '주요 근거' }}</span>
        <span class="item__text">{{ c.text }}</span>
      </li>
    </ul>
    <p class="muted">
      위 항목은 이번 응답을 바탕으로 계산한 것입니다. 같은 구간이어도 응답이 다르면 다른 이유가 제시됩니다.
      함께 나타나는 경향을 뜻하며 원인을 말하는 것은 아닙니다.
    </p>
  </section>
</template>

<style scoped>
.list { list-style: none; padding: 0; margin: 0; display: grid; gap: var(--sp-sm); }
.item { display: flex; gap: var(--sp-md); align-items: flex-start;
  border: 1px solid var(--hairline); border-radius: var(--radius-md); padding: var(--sp-md); background: var(--canvas); }
.item--minor { background: var(--surface-soft); }
.item__tag { flex: none; font-size: 12px; font-weight: 700; color: var(--ink);
  background: var(--surface-strong); border-radius: var(--radius-pill); padding: 4px 10px; }
.item--minor .item__tag { color: var(--muted); background: var(--canvas); border: 1px solid var(--hairline); }
.item__text { font-size: 15px; }
</style>
