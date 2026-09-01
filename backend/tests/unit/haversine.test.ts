// 거리 계산 (FR-021-1 · research.md R-9)
import { describe, it, expect } from 'vitest';
import { haversineKm } from '../../src/services/facilityService.js';

describe('Haversine 직선거리', () => {
  it('같은 지점은 0km', () => {
    expect(haversineKm(37.5665, 126.978, 37.5665, 126.978)).toBeCloseTo(0, 6);
  });

  it('서울시청 ↔ 부산시청 ≈ 325km', () => {
    const d = haversineKm(37.5665, 126.9780, 35.1796, 129.0756);
    expect(d).toBeGreaterThan(315);
    expect(d).toBeLessThan(335);
  });

  it('위도 1도 ≈ 111km', () => {
    expect(haversineKm(37, 127, 38, 127)).toBeCloseTo(111.2, 0);
  });

  it('대칭이다', () => {
    const a = haversineKm(37.5, 127.0, 35.1, 129.0);
    const b = haversineKm(35.1, 129.0, 37.5, 127.0);
    expect(a).toBeCloseTo(b, 9);
  });

  it('경계 상자가 실제 반경보다 넓어 후보를 놓치지 않는다', () => {
    // findNearby 가 쓰는 델타. 정북/정동 방향 경계점이 반경 밖이면 후보 누락이 없다.
    const lat = 37.5, radiusKm = 10;
    const dLat = radiusKm / 111;
    const dLng = radiusKm / (111 * Math.max(0.2, Math.cos((lat * Math.PI) / 180)));
    expect(haversineKm(lat, 127, lat + dLat, 127)).toBeGreaterThanOrEqual(radiusKm - 0.2);
    expect(haversineKm(lat, 127, lat, 127 + dLng)).toBeGreaterThanOrEqual(radiusKm - 0.2);
  });
});
