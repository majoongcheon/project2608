<script setup lang="ts">
// 참조 집단 비교 (FR-013a·FR-013b)
//   비교할 항목이 하나도 없으면 부모가 이 컴포넌트를 아예 렌더링하지 않는다.
//   (빈 영역이나 "데이터 없음"을 노출하지 않는다 — spec Edge Cases)
defineProps<{ items: { text: string; userValue: string; referencePct: number }[] }>();
</script>

<template>
  <section class="stack">
    <h2>다른 보호자들과 비교하면</h2>
    <ul class="list">
      <li v-for="(c, i) in items" :key="i" class="item">
        <p class="item__text">{{ c.text }}</p>
        <div class="bar" role="img" :aria-label="`${c.referencePct}퍼센트`">
          <span :style="{ width: Math.min(100, c.referencePct) + '%' }"></span>
        </div>
        <p class="item__meta">내 응답: <strong>{{ c.userValue }}</strong> · 같은 응답 {{ c.referencePct }}%</p>
      </li>
    </ul>
    <p class="muted">
      비교 기준은 2024 발달장애인 일과 삶 실태조사에 참여한 전국 3,000가구입니다.
      응답자가 30명 미만인 항목은 개인이 특정될 수 있어 비교에서 제외했습니다.
    </p>
  </section>
</template>

<style scoped>
.list { list-style: none; padding: 0; margin: 0; display: grid; gap: var(--sp-base); }
.item { border: 1px solid var(--hairline); border-radius: var(--radius-md); padding: var(--sp-md); }
.item__text { margin: 0 0 var(--sp-sm); font-size: 15px; }
.item__meta { margin: var(--sp-xs) 0 0; font-size: 13px; color: var(--muted); }
.bar { height: 10px; background: var(--surface-strong); border-radius: var(--radius-pill); overflow: hidden; }
.bar span { display: block; height: 100%; background: var(--ink); }
</style>
