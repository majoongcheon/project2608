<script setup lang="ts">
// 지도 기반 기관 안내 (FR-015·FR-016·FR-016b·FR-020)
//   ★ 진단을 거치지 않고도 단독으로 동작한다 (US2 독립 전달).
//   ★ 위치 정보를 거부해도 지역 직접 선택으로 온전히 동작한다(FR-015).
import { ref, computed, onMounted } from 'vue';
import { api } from '../services/apiClient';
import { useEventStore } from '../stores/events';
import FacilityCard from '../components/FacilityCard.vue';
import MapView from '../components/MapView.vue';

const events = useEventStore();
const regions = ref<any[]>([]);
const sido = ref('');
const regionCode = ref('');
const serviceType = ref('');
const facilities = ref<any[]>([]);
const pending = ref(false);
const metroContact = ref<any>(null);
const regionCenter = ref<any>(null);
const suggestedRadius = ref<number | null>(null);
const radiusKm = ref<number | null>(null);
const coords = ref<{ lat: number; lng: number } | null>(null);
const loading = ref(false);
const locError = ref('');

const sidos = computed(() => [...new Set(regions.value.map((r) => r.sidoName))]);
const inSido = computed(() => regions.value.filter((r) => r.sidoName === sido.value));
const center = computed(() => coords.value ?? regionCenter.value);
const centerLabel = computed(() => {
  if (coords.value) return '현재 위치';
  const r = regions.value.find((x) => x.regionCode === regionCode.value);
  return r ? `${r.sidoName} ${r.sigunguName}` : '기준 위치';
});

onMounted(async () => {
  events.track('MAP_ENTER');
  const d = await api.regions();
  regions.value = d.regions;
});

async function search(q: Record<string, unknown>) {
  loading.value = true;
  try {
    const d = await api.facilities({ ...q, serviceType: serviceType.value || undefined, limit: 30 });
    facilities.value = d.facilities;
    pending.value = d.regionDataPending;
    metroContact.value = d.metroContact;
    regionCenter.value = d.regionCenter ?? regionCenter.value;
    suggestedRadius.value = d.suggestedRadiusKm;
    radiusKm.value = d.radiusKm;
  } finally { loading.value = false; }
}

function byRegion() {
  if (!regionCode.value) return;
  coords.value = null;
  const r = regions.value.find((x) => x.regionCode === regionCode.value);
  regionCenter.value = r?.centerLat ? { lat: r.centerLat, lng: r.centerLng } : null;
  events.track('MAP_ENTER', { regionCode: regionCode.value });
  void search({ regionCode: regionCode.value });
}

function useMyLocation() {
  locError.value = '';
  if (!navigator.geolocation) { locError.value = '이 브라우저에서는 위치를 사용할 수 없습니다. 지역을 직접 선택해 주세요.'; return; }
  navigator.geolocation.getCurrentPosition(
    (p) => {
      coords.value = { lat: p.coords.latitude, lng: p.coords.longitude };
      void search({ lat: coords.value.lat, lng: coords.value.lng, radiusKm: 10 });
    },
    () => { locError.value = '위치를 확인하지 못했습니다. 아래에서 지역을 직접 선택해 주세요.'; },
    { timeout: 6000 });
}

// FR-020 — 범위 확대는 자동이 아니라 선택지로 제공한다
function expand() {
  const c = center.value;
  if (!c) return;
  void search({ lat: c.lat, lng: c.lng, radiusKm: suggestedRadius.value ?? 20 });
}
</script>

<template>
  <div class="container stack">
    <h1>복지서비스 신청처 찾기</h1>
    <p class="muted">주간활동서비스와 청소년 방과후활동서비스의 신청 접수처를 안내합니다.</p>

    <div class="card stack">
      <button class="btn btn--secondary btn--block" type="button" @click="useMyLocation">
        현재 위치에서 가까운 곳 찾기
      </button>
      <p v-if="locError" class="notice">{{ locError }}</p>

      <div class="selects">
        <label class="sel">
          <span>시 · 도</span>
          <select v-model="sido" @change="regionCode = ''">
            <option value="">선택하세요</option>
            <option v-for="s in sidos" :key="s" :value="s">{{ s }}</option>
          </select>
        </label>
        <label class="sel">
          <span>시 · 군 · 구</span>
          <select v-model="regionCode" :disabled="!sido" @change="byRegion">
            <option value="">선택하세요</option>
            <option v-for="r in inSido" :key="r.regionCode" :value="r.regionCode">
              {{ r.sigunguName }}{{ r.hasFacilityData ? '' : ' (준비 중)' }}
            </option>
          </select>
        </label>
        <label class="sel">
          <span>서비스 유형</span>
          <select v-model="serviceType" @change="regionCode ? byRegion() : (coords && search({ lat: coords.lat, lng: coords.lng, radiusKm: 10 }))">
            <option value="">전체</option>
            <option value="DAY_ACTIVITY">주간활동서비스</option>
            <option value="AFTERSCHOOL_YOUTH">청소년 방과후활동서비스</option>
          </select>
        </label>
      </div>
    </div>

    <!-- FR-016b — 빈 지도를 그대로 보여주지 않는다 -->
    <div v-if="pending" class="pendingbox">
      <p><strong>이 지역의 기관 정보는 아직 준비 중입니다.</strong></p>
      <p v-if="metroContact?.name">먼저 <strong>{{ metroContact.name }}</strong>로 문의해 주세요.
        <span v-if="metroContact.phone">({{ metroContact.phone }})</span></p>
      <button v-if="suggestedRadius" class="btn btn--ghost" type="button" @click="expand">
        인근 {{ suggestedRadius }}km 범위로 넓혀 찾기
      </button>
    </div>

    <MapView v-if="facilities.length" :center="center" :facilities="facilities"
             :radius-km="radiusKm" :center-label="centerLabel" />

    <p v-if="loading" class="notice">기관을 찾고 있습니다…</p>

    <div v-else-if="facilities.length" class="stack">
      <h2>{{ facilities.length }}곳 <span v-if="radiusKm" class="muted">· 반경 {{ radiusKm }}km</span></h2>
      <FacilityCard v-for="f in facilities" :key="f.facilityId" :facility="f" :show-distance="!!radiusKm" />
    </div>

    <p v-else-if="(regionCode || coords) && !pending" class="notice">
      선택하신 범위에 등록된 신청 접수처가 없습니다.
      <button v-if="suggestedRadius" class="linklike" type="button" @click="expand">
        인근 {{ suggestedRadius }}km까지 넓혀 찾기
      </button>
    </p>
  </div>
</template>

<style scoped>
.selects { display: grid; gap: var(--sp-md); grid-template-columns: 1fr; }
@media (min-width: 640px) { .selects { grid-template-columns: repeat(3, 1fr); } }
.sel span { display: block; font-size: 14px; color: var(--ink); margin-bottom: var(--sp-xs); font-weight: 600; }
select { width: 100%; padding: 12px var(--sp-md); font: inherit; min-height: 48px;
  border: 1px solid var(--border-strong); border-radius: var(--radius-sm); background: var(--canvas); }
.notice { background: var(--surface-soft); color: var(--muted); font-size: 14px;
  padding: var(--sp-md); border-radius: var(--radius-sm); margin: 0; }
.pendingbox { background: #fffaf3; border: 1px solid #f0d9b5; border-radius: var(--radius-md); padding: var(--sp-base); }
.pendingbox p { margin: 0 0 var(--sp-sm); font-size: 15px; }
.linklike { background: none; border: 0; padding: 0; color: var(--link); text-decoration: underline; cursor: pointer; font: inherit; }
</style>
