<script setup lang="ts">
// 지도 기반 기관 안내 (FR-015·FR-016·FR-016b·FR-020)
//   ★ 진단을 거치지 않고도 단독으로 동작한다 (US2 독립 전달).
//   ★ 위치 정보를 거부해도 지역 직접 선택으로 온전히 동작한다(FR-015).
import { ref, computed, onMounted } from 'vue';
import { api } from '../services/apiClient';
import { useEventStore } from '../stores/events';
import FacilityCard from '../components/FacilityCard.vue';
import MapView from '../components/MapView.vue';
import RoomHead from '../components/RoomHead.vue';

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
// 서버가 응답하지 않을 때. 아무 말 없이 멈추면 이용자는 자기 잘못인 줄 안다.
const loadError = ref('');

// 아직 아무것도 고르지 않은 상태. 이때 화면이 비어 있으면 무엇을 해야 하는지 알 수 없다.
const started = computed(() => Boolean(regionCode.value) || Boolean(coords.value));
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
  // 감싸지 않으면 서버가 죽었을 때 여기서 그대로 터지고, 화면은 아무 말 없이
  // 멈춘 채로 남는다(2026-09-03 점검에서 실제로 그랬다).
  try {
    const d = await api.regions();
    regions.value = d.regions;
  } catch {
    loadError.value = '지역 목록을 불러오지 못했습니다. 잠시 후 다시 들어와 주세요.';
  }
});

async function search(q: Record<string, unknown>) {
  loading.value = true;
  loadError.value = '';
  try {
    const d = await api.facilities({ ...q, serviceType: serviceType.value || undefined, limit: 30 });
    facilities.value = d.facilities;
    pending.value = d.regionDataPending;
    metroContact.value = d.metroContact;
    regionCenter.value = d.regionCenter ?? regionCenter.value;
    suggestedRadius.value = d.suggestedRadiusKm;
    radiusKm.value = d.radiusKm;
  } catch {
    facilities.value = [];
    loadError.value = '기관 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.';
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
  <div class="container room stack">
    <RoomHead
      no="02"
      eyebrow="복지서비스 위치 · 연락처"
      title="신청 접수처 찾기"
      lead="주간활동서비스와 청소년 방과후활동서비스의 신청 접수처를 지도와 목록으로 안내합니다."
    />

    <!-- 아직 고르기 전 — 조작부보다 먼저 온다. 설명을 읽고 나서 버튼을 만나야 순서가 맞다 -->
    <div v-if="!started && !loading" class="firststep">
      <p class="firststep__head">두 가지 방법 중 편한 쪽으로 찾으실 수 있습니다.</p>
      <ul class="firststep__list">
        <li><strong>현재 위치에서 찾기</strong> — 가까운 순서로 안내해 드립니다. 위치 권한을 물어봅니다.</li>
        <li><strong>지역 직접 선택</strong> — 위치 권한을 허용하지 않으셔도 됩니다. 시·도와 시·군·구를 고르세요.</li>
      </ul>
      <p class="firststep__note">
        진단을 하지 않으셔도 이 화면만 따로 쓰실 수 있습니다.
        기관 정보가 아직 준비되지 않은 지역은 목록에 <em>(준비 중)</em>으로 표시됩니다.
      </p>
    </div>

    <div class="card stack">
      <button class="btn btn--secondary btn--block" type="button" @click="useMyLocation">
        현재 위치에서 가까운 곳 찾기
      </button>
      <p v-if="locError" class="notice">{{ locError }}</p>
      <p v-if="loadError" class="notice" role="alert">{{ loadError }}</p>

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

    <!-- 기준 위치가 정해졌으면 결과가 0곳이어도 지도는 보여 준다.
         빈 지도가 아니라 "여기를 기준으로 찾았다"는 것이 눈에 보여야 다음 행동을 고를 수 있다. -->
    <MapView v-if="started && center" :center="center" :facilities="facilities"
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

    <nav class="hop" aria-label="다른 방으로">
      <RouterLink class="hop__a" to="/reviews">이용 후기 소통방</RouterLink>
      <RouterLink class="hop__a" to="/me">저장해 둔 기관</RouterLink>
      <RouterLink class="hop__a" to="/talk">정보 소통방</RouterLink>
    </nav>
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
.firststep { background: var(--surface-soft); border: 1px solid var(--hairline);
  border-radius: var(--radius-md); padding: var(--sp-base); }
.firststep__head { margin: 0 0 var(--sp-sm); font-size: 15px; font-weight: 700; color: var(--ink); }
.firststep__list { margin: 0; padding-left: 1.15em; font-size: 15px; }
.firststep__list li + li { margin-top: var(--sp-xs); }
.firststep__note { margin: var(--sp-md) 0 0; font-size: 13px; color: var(--muted); line-height: 1.6; }
.pendingbox { background: #fffaf3; border: 1px solid #f0d9b5; border-radius: var(--radius-md); padding: var(--sp-base); }
.pendingbox p { margin: 0 0 var(--sp-sm); font-size: 15px; }
.linklike { background: none; border: 0; padding: 0; color: var(--link); text-decoration: underline; cursor: pointer; font: inherit; }
</style>
