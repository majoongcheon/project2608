<script setup lang="ts">
// 지도 표시 (FR-016) — Kakao Maps SDK
//   ★ SDK 키가 없거나 로드에 실패해도 목록 경로는 그대로 동작해야 한다.
//     지도는 표현 계층에만 있고 데이터 경로가 분리되어 있다(research.md R-7).
import { ref, watch, onMounted } from 'vue';

const props = defineProps<{
  center: { lat: number; lng: number } | null;
  facilities: { facilityId: number; name: string; lat?: number; lng?: number }[];
}>();

const el = ref<HTMLDivElement | null>(null);
const failed = ref(false);
const ready = ref(false);
let map: any = null;
let markers: any[] = [];

const KEY = import.meta.env.VITE_KAKAO_MAP_KEY;

function loadSdk(): Promise<any> {
  return new Promise((resolve, reject) => {
    if (!KEY) return reject(new Error('no-key'));
    const w = window as any;
    if (w.kakao?.maps) return w.kakao.maps.load(() => resolve(w.kakao));
    const s = document.createElement('script');
    s.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${KEY}&autoload=false`;
    s.onload = () => w.kakao.maps.load(() => resolve(w.kakao));
    s.onerror = () => reject(new Error('sdk-load-failed'));
    document.head.appendChild(s);
    setTimeout(() => reject(new Error('timeout')), 8000);
  });
}

onMounted(async () => {
  try {
    const kakao = await loadSdk();
    if (!el.value) return;
    map = new kakao.maps.Map(el.value, {
      center: new kakao.maps.LatLng(props.center?.lat ?? 37.5665, props.center?.lng ?? 126.978),
      level: 6,
    });
    ready.value = true;
    render(kakao);
  } catch {
    failed.value = true;                 // 목록으로 폴백. 오류를 사용자에게 떠넘기지 않는다.
  }
});

function render(kakao: any) {
  markers.forEach((m) => m.setMap(null));
  markers = [];
  const bounds = new kakao.maps.LatLngBounds();
  let has = false;
  for (const f of props.facilities) {
    if (f.lat == null || f.lng == null) continue;
    const pos = new kakao.maps.LatLng(f.lat, f.lng);
    const mk = new kakao.maps.Marker({ map, position: pos, title: f.name });
    markers.push(mk); bounds.extend(pos); has = true;
  }
  if (has) map.setBounds(bounds);
  else if (props.center) map.setCenter(new kakao.maps.LatLng(props.center.lat, props.center.lng));
}

watch(() => props.facilities, () => {
  const w = window as any;
  if (ready.value && w.kakao?.maps) render(w.kakao);
}, { deep: true });
</script>

<template>
  <div>
    <div v-show="!failed" ref="el" class="map" role="img" aria-label="기관 위치 지도"></div>
    <p v-if="failed" class="fallback">
      지도를 표시할 수 없어 목록으로 안내해 드립니다. 아래 기관 정보는 그대로 이용하실 수 있습니다.
    </p>
  </div>
</template>

<style scoped>
.map { width: 100%; height: 320px; border-radius: var(--radius-md); border: 1px solid var(--hairline); background: var(--surface-soft); }
.fallback { background: var(--surface-soft); color: var(--muted); font-size: 14px;
  padding: var(--sp-md); border-radius: var(--radius-sm); margin: 0; }
</style>
