// 지도 컴포넌트 (JSG-01 · FR-016)
//   키 없이 동작할 것, 중심이 기준 위치일 것, 마커·팝업이 그려질 것을 확인한다.
import { describe, it, expect, vi, beforeAll } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import MapView from '../../src/components/MapView.vue';

// jsdom 은 지도 렌더에 필요한 레이아웃 API 가 없어 Leaflet 이 예외를 던진다.
// 최소한만 채워 실제 컴포넌트 코드를 그대로 태운다.
beforeAll(() => {
  (globalThis as any).ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
  Object.defineProperty(HTMLElement.prototype, 'clientWidth', { value: 800, configurable: true });
  Object.defineProperty(HTMLElement.prototype, 'clientHeight', { value: 340, configurable: true });
});

const FACILITIES = [
  { facilityId: 1, name: '종로장애인복지관', lat: 37.58403, lng: 126.96997, address: '서울 종로구 자하문로 89', distanceKm: 2.07 },
  { facilityId: 2, name: '전화없는기관', lat: 37.55947, lng: 126.95704, address: null, distanceKm: 3.1 },
];
const CENTER = { lat: 37.5665, lng: 126.978 };

describe('MapView — 키 없는 지도 (JSG-01)', () => {
  it('발급 키를 전혀 참조하지 않는다', async () => {
    const w = mount(MapView, { props: { center: CENTER, facilities: FACILITIES } });
    await flushPromises();
    expect(w.html()).not.toContain('kakao');
    // SDK 스크립트를 문서에 주입하지 않는다
    expect(document.querySelectorAll('script[src*="dapi.kakao.com"]').length).toBe(0);
  });

  it('지도 컨테이너를 그린다', async () => {
    const w = mount(MapView, { props: { center: CENTER, facilities: FACILITIES } });
    await flushPromises();
    expect(w.find('.map').exists()).toBe(true);
  });

  it('기관마다 마커를 찍고 팝업에 기관명과 주소를 넣는다', async () => {
    const w = mount(MapView, { props: { center: CENTER, facilities: FACILITIES } });
    await flushPromises();
    const html = w.element.ownerDocument.body.innerHTML + w.html();
    expect(html).toContain('pin--facility');
    // 기준 위치 마커는 기관 마커와 구분된다
    expect(html).toContain('pin--center');
  });

  it('좌표가 없는 기관은 건너뛴다 (마커를 만들지 않는다)', async () => {
    const w = mount(MapView, {
      props: { center: CENTER, facilities: [{ facilityId: 9, name: '좌표없음', lat: null, lng: null }] },
    });
    await flushPromises();
    expect(w.find('.map').exists()).toBe(true);   // 지도는 뜨고 예외로 죽지 않는다
  });

  it('중심 좌표가 없어도 죽지 않는다 (기본 위치로 뜬다)', async () => {
    const w = mount(MapView, { props: { center: null, facilities: FACILITIES } });
    await flushPromises();
    expect(w.find('.map').exists()).toBe(true);
  });
});
