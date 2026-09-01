<script setup lang="ts">
// 기관 카드 (FR-017·FR-018·FR-021b)
//   ★ 이용 대상 조건은 항상 표시된다 — 누락률 0%가 SC-015 의 측정 대상이다.
//   ★ phone 이 null 이면 통화 버튼을 숨기고 주소·길찾기만 제공한다(기관 40건).
import { useEventStore } from '../stores/events';
const props = defineProps<{
  facility: { facilityId: number; name: string; distanceKm: number | null;
              serviceTypes: string[]; eligibilityNote: string; phone: string | null; address?: string };
  showDistance?: boolean;
}>();
const events = useEventStore();
const LABEL: Record<string, string> = {
  DAY_ACTIVITY: '주간활동', AFTERSCHOOL_YOUTH: '청소년 방과후',
};
function call() { events.track('CONTACT_ACTION'); }
function directions() {
  events.track('CONTACT_ACTION');
  const q = encodeURIComponent(props.facility.address || props.facility.name);
  window.open(`https://map.kakao.com/link/search/${q}`, '_blank', 'noopener');
}
</script>

<template>
  <article class="fac">
    <header class="fac__head">
      <RouterLink :to="`/facility/${facility.facilityId}`" class="fac__name">{{ facility.name }}</RouterLink>
      <span v-if="showDistance && facility.distanceKm !== null" class="fac__dist">
        {{ facility.distanceKm }}km
      </span>
    </header>

    <p class="fac__types">
      <span v-for="t in facility.serviceTypes" :key="t" class="chip">{{ LABEL[t] ?? t }}</span>
    </p>

    <!-- FR-021b — 반드시 표시 -->
    <p class="fac__elig">{{ facility.eligibilityNote }}</p>
    <p v-if="facility.address" class="fac__addr">{{ facility.address }}</p>

    <div class="row">
      <a v-if="facility.phone" class="btn btn--secondary" :href="`tel:${facility.phone}`" @click="call">
        전화 {{ facility.phone }}
      </a>
      <p v-else class="fac__nophone">등록된 전화번호가 없습니다. 주소로 방문하거나 길찾기를 이용해 주세요.</p>
      <button class="btn btn--ghost" type="button" @click="directions">길찾기</button>
    </div>
  </article>
</template>

<style scoped>
.fac { border: 1px solid var(--hairline); border-radius: var(--radius-md); padding: var(--sp-base); background: var(--canvas); }
.fac__head { display: flex; justify-content: space-between; gap: var(--sp-sm); align-items: baseline; }
.fac__name { font-size: 17px; font-weight: 700; color: var(--ink); text-decoration: none; }
.fac__name:hover { text-decoration: underline; }
.fac__dist { font-size: 14px; color: var(--muted); flex: none; }
.fac__types { margin: var(--sp-sm) 0; display: flex; gap: var(--sp-xs); flex-wrap: wrap; }
.chip { font-size: 12px; background: var(--surface-strong); border-radius: var(--radius-pill); padding: 4px 10px; color: var(--ink); }
.fac__elig { font-size: 13px; color: var(--muted); margin: 0 0 var(--sp-xs); }
.fac__addr { font-size: 14px; margin: 0 0 var(--sp-md); }
.fac__nophone { font-size: 13px; color: var(--muted); margin: 0; flex: 1; }
.btn { text-decoration: none; font-size: 15px; min-height: 44px; padding: 10px var(--sp-base); }
</style>
