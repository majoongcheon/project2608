<script setup lang="ts">
/* 방 머리 — 다섯 방이 모두 이것으로 시작한다 (2026-09-03).
 *
 * 방을 늘리면서 받은 요구는 "방을 이동할 때마다 다른 사이트에 들어간 느낌이
 * 안 나도록" 이었다. 화면마다 제목을 제 나름대로 쓰면 반드시 어긋나므로,
 * 머리는 부품 하나로 고정한다. 홈 히어로와 같은 활자 계단(--display-2 ·
 * --lede)을 쓰므로 크기 감각이 그대로 이어진다.
 *
 * 스타일은 theme-editorial.css 의 .room__* 전역 규칙이다 — 여기에 scoped 로
 * 두면 방마다 조금씩 달라질 여지가 생긴다.
 */
defineProps<{
  /** 제목 위 작은 라벨. 이 방이 무엇에 속하는지 */
  eyebrow?: string;
  /** 방 이름 */
  title: string;
  /** 한 줄 설명 */
  lead?: string;
  /** 홈 메뉴의 번호(01~05)와 맞춘다. 어느 방인지 위치를 알려 준다 */
  no?: string;
}>();
</script>

<template>
  <header class="room__head">
    <p v-if="eyebrow || no" class="room__eyebrow">
      <span v-if="no" class="room__no">{{ no }}</span>{{ eyebrow }}
    </p>
    <h1 class="room__h">{{ title }}</h1>
    <p v-if="lead" class="room__lead">{{ lead }}</p>
  </header>
</template>

<style scoped>
.room__no {
  margin-right: 10px; color: var(--muted-soft);
  font-variant-numeric: tabular-nums; letter-spacing: .12em;
}
</style>
