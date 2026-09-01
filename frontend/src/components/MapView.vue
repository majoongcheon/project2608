<script setup lang="ts">
// 지도 표시 (FR-016) — Leaflet + OpenStreetMap
//
// JSG-01 반영: 발급 키가 필요 없는 방식으로 교체했다.
//   조성기 님이 참고로 준 folium 예시가 내부적으로 쓰는 것이 바로 Leaflet + OSM 이다.
//   folium 은 Python 라이브러리라 그대로 쓸 수 없어, 같은 지도 엔진을 TS 에서 직접 부른다.
//
// 중심좌표는 **기준 위치(현재 위치 또는 선택 지역 대표 좌표)** 다.
//   예시 코드는 마커 평균(mean)을 중심으로 삼지만, 이 서비스의 지도는 "내 주변에서
//   가까운 곳"을 보여주는 것이 목적이라 기준점이 보호자 위치여야 한다(JSG-01 추가 지시).
//   예시가 중심 확인용 마커를 따로 찍은 것처럼, 기준 위치도 구분되는 마커로 표시한다.
//
// 지도를 못 쓰는 상황(타일 서버 불통·오프라인)에서는 목록으로 폴백한다.
// 데이터 경로가 지도와 분리되어 있어 목록은 그대로 동작한다.
import { ref, watch, onMounted, onBeforeUnmount } from 'vue';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

interface MapFacility {
  facilityId: number;
  name: string;
  lat?: number | null;
  lng?: number | null;
  address?: string | null;
  distanceKm?: number | null;
}

const props = defineProps<{
  center: { lat: number; lng: number } | null;
  facilities: MapFacility[];
  radiusKm?: number | null;
  centerLabel?: string;
}>();

const el = ref<HTMLDivElement | null>(null);
const failed = ref(false);
let map: L.Map | null = null;
let markerLayer: L.LayerGroup | null = null;
let centerMarker: L.Marker | null = null;

const SEOUL: L.LatLngExpression = [37.5665, 126.978];

/** 반경(km)에 맞는 줌 단계. 반경이 클수록 넓게 본다. */
function zoomForRadius(km: number | null | undefined): number {
  if (!km) return 13;
  if (km <= 3) return 14;
  if (km <= 7) return 13;
  if (km <= 12) return 12;
  if (km <= 25) return 11;
  return 10;
}

/**
 * 기본 마커 대신 divIcon 을 쓴다.
 *   Leaflet 기본 아이콘은 이미지 파일 경로를 상대 경로로 잡아 번들러에서 깨진다.
 *   CSS 로만 그리면 그 문제가 없고 외부 이미지 요청도 생기지 않는다.
 */
function pinIcon(kind: 'facility' | 'center'): L.DivIcon {
  return L.divIcon({
    className: '',
    html: `<span class="pin pin--${kind}" aria-hidden="true"></span>`,
    iconSize: kind === 'center' ? [22, 22] : [18, 18],
    iconAnchor: kind === 'center' ? [11, 11] : [9, 9],
    popupAnchor: [0, -10],
  });
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] as string));
}

/** 팝업 = 기관명 + 주소 (JSG-01 원문의 popup_text 구성과 동일) */
function popupHtml(f: MapFacility): string {
  const parts = [`<strong>${escapeHtml(f.name)}</strong>`];
  if (f.address) parts.push(escapeHtml(f.address));
  if (f.distanceKm != null) parts.push(`직선거리 약 ${f.distanceKm}km`);
  return `<div class="mapPopup">${parts.join('<br>')}</div>`;
}

function render() {
  if (!map) return;
  markerLayer?.clearLayers();
  if (!markerLayer) markerLayer = L.layerGroup().addTo(map);

  for (const f of props.facilities) {
    if (f.lat == null || f.lng == null) continue;
    L.marker([Number(f.lat), Number(f.lng)], {
      icon: pinIcon('facility'),
      title: f.name,
      alt: f.name,
      keyboard: true,                       // FR-039 — 키보드로 마커에 접근할 수 있어야 한다
    })
      .bindPopup(popupHtml(f), { maxWidth: 300 })
      .addTo(markerLayer);
  }

  // 기준 위치 마커 — 기관 마커와 구분되는 모양으로 둔다
  centerMarker?.remove();
  centerMarker = null;
  if (props.center) {
    centerMarker = L.marker([props.center.lat, props.center.lng], {
      icon: pinIcon('center'),
      title: props.centerLabel ?? '기준 위치',
      alt: props.centerLabel ?? '기준 위치',
      zIndexOffset: 1000,
    })
      .bindPopup(`<div class="mapPopup"><strong>${escapeHtml(props.centerLabel ?? '기준 위치')}</strong></div>`)
      .addTo(map);
  }

  // 중심은 항상 기준 위치. 마커에 맞춰 중심을 옮기지 않는다(JSG-01).
  const center = props.center ? [props.center.lat, props.center.lng] as L.LatLngExpression : SEOUL;
  map.setView(center, zoomForRadius(props.radiusKm), { animate: false });
}

onMounted(() => {
  if (!el.value) return;
  try {
    map = L.map(el.value, { scrollWheelZoom: false, attributionControl: true });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> 기여자',
    })
      // 타일을 못 받으면 지도를 접고 목록으로 넘긴다
      .on('tileerror', () => { failed.value = true; })
      .addTo(map);
    render();
  } catch {
    failed.value = true;
  }
});

onBeforeUnmount(() => { map?.remove(); map = null; });

watch(() => [props.facilities, props.center, props.radiusKm], () => render(), { deep: true });
</script>

<template>
  <div>
    <div v-show="!failed" ref="el" class="map"></div>
    <p v-if="failed" class="fallback">
      지도를 표시할 수 없어 목록으로 안내해 드립니다. 아래 기관 정보는 그대로 이용하실 수 있습니다.
    </p>
  </div>
</template>

<style>
/* scoped 를 쓰지 않는다 — Leaflet 이 만드는 요소(마커·팝업)에는 scoped 속성이 붙지 않는다 */
.pin {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  box-sizing: border-box;
}
.pin--facility {
  background: var(--primary, #ff385c);
  border: 3px solid #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, .4);
}
.pin--center {
  background: #fff;
  border: 5px solid var(--ink, #222);
  box-shadow: 0 1px 4px rgba(0, 0, 0, .4);
}
.mapPopup {
  font-size: 14px;
  line-height: 1.5;
  color: var(--ink, #222);
}
.leaflet-container {
  font: inherit;
  border-radius: var(--radius-md, 12px);
}
</style>

<style scoped>
.map {
  width: 100%;
  height: 340px;
  border-radius: var(--radius-md, 12px);
  border: 1px solid var(--hairline, #ddd);
  background: var(--surface-soft, #f7f7f7);
  z-index: 0;                       /* 헤더(sticky) 위로 올라오지 않게 */
}
.fallback {
  background: var(--surface-soft, #f7f7f7);
  color: var(--muted, #6a6a6a);
  font-size: 14px;
  padding: var(--sp-md, 12px);
  border-radius: var(--radius-sm, 8px);
  margin: 0;
}
</style>
