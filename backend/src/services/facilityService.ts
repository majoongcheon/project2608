// 기관 조회와 거리 정렬 (FR-016~FR-021, research.md R-9)
//   거리는 직선거리(Haversine)로 계산한다 (FR-021-1).
//   1단계로 경계 상자를 걸어 (lat,lng) 인덱스를 태우고, 2단계에서만 삼각함수를 쓴다.
import { query } from '../repositories/pool.js';

export type ServiceType = 'DAY_ACTIVITY' | 'AFTERSCHOOL_YOUTH';

export const SERVICE_LABEL: Record<ServiceType, string> = {
  DAY_ACTIVITY: '발달장애인 주간활동서비스',
  AFTERSCHOOL_YOUTH: '청소년 발달장애인 방과후활동서비스',
};

const R_EARTH = 6371.0088;

export function haversineKm(aLat: number, aLng: number, bLat: number, bLng: number): number {
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(bLat - aLat);
  const dLng = toRad(bLng - aLng);
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(aLat)) * Math.cos(toRad(bLat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R_EARTH * Math.asin(Math.min(1, Math.sqrt(s)));
}

export interface FacilityRow {
  facility_id: number; name: string; address: string | null; phone: string | null;
  lat: number; lng: number; updated_at: Date | null; region_code: string | null;
  service_types: string;
}

export interface FacilityCard {
  facilityId: number; name: string; distanceKm: number | null;
  serviceTypes: ServiceType[]; eligibilityNote: string; phone: string | null;
  // 지도 마커와 팝업에 필요하다. 기관 좌표·주소는 공개 기관 정보라
  // 이용자 위치 보관 금지(FR-026·FR-028)와 무관하다.
  lat: number; lng: number; address: string | null;
  updatedAt?: string;
}

const BASE_SELECT = `
  SELECT f.facility_id, f.name, f.address, f.phone, f.lat, f.lng, f.updated_at, f.region_code,
         GROUP_CONCAT(s.service_type ORDER BY s.service_type) AS service_types
    FROM cb_facility_v1 f
    JOIN cb_facility_service_v1 s ON s.facility_id = f.facility_id`;

/** 기준 좌표에서 반경 안의 기관을 거리순으로. serviceType 을 주면 그 유형만. */
export async function findNearby(
  lat: number, lng: number, radiusKm: number, serviceType?: ServiceType, limit = 20
): Promise<FacilityRow[]> {
  // 위도 1도 ≈ 111km. 경도는 위도에 따라 좁아지므로 cos 로 보정한다.
  const dLat = radiusKm / 111;
  const dLng = radiusKm / (111 * Math.max(0.2, Math.cos((lat * Math.PI) / 180)));
  const params: unknown[] = [lat - dLat, lat + dLat, lng - dLng, lng + dLng];
  let sql = `${BASE_SELECT} WHERE f.lat BETWEEN ? AND ? AND f.lng BETWEEN ? AND ?`;
  if (serviceType) { sql += ' AND s.service_type = ?'; params.push(serviceType); }
  sql += ' GROUP BY f.facility_id';
  const rows = await query<FacilityRow>(sql, params);

  return rows
    .map((r) => ({ ...r, _d: haversineKm(lat, lng, Number(r.lat), Number(r.lng)) }))
    .filter((r) => r._d <= radiusKm)
    .sort((a, b) => a._d - b._d)
    .slice(0, limit) as any;
}

export async function findByRegion(
  regionCode: string, serviceType?: ServiceType, limit = 50
): Promise<FacilityRow[]> {
  const params: unknown[] = [regionCode];
  let sql = `${BASE_SELECT} WHERE f.region_code = ?`;
  if (serviceType) { sql += ' AND s.service_type = ?'; params.push(serviceType); }
  sql += ' GROUP BY f.facility_id ORDER BY f.name LIMIT ' + Number(limit);
  return query<FacilityRow>(sql, params);
}

export async function findById(id: number): Promise<FacilityRow | null> {
  const rows = await query<FacilityRow>(
    `${BASE_SELECT} WHERE f.facility_id = ? GROUP BY f.facility_id`, [id]);
  return rows[0] ?? null;
}

/** 이용 대상 조건 문구. FR-021b — 모든 카드에 반드시 표시된다(SC-015). */
export function eligibilityNote(types: ServiceType[], ranges: any): string {
  return types
    .map((t) => {
      const r = ranges[t];
      return r ? `${SERVICE_LABEL[t]}: ${r.label} 이용 대상` : SERVICE_LABEL[t];
    })
    .join(' · ');
}

export function toCard(r: FacilityRow, ranges: any, distanceKm: number | null): FacilityCard {
  const types = String(r.service_types || '').split(',').filter(Boolean) as ServiceType[];
  return {
    facilityId: r.facility_id,
    name: r.name,
    distanceKm: distanceKm === null ? null : Number(distanceKm.toFixed(2)),
    serviceTypes: types,
    eligibilityNote: eligibilityNote(types, ranges),
    phone: r.phone ?? null,             // null 이면 프론트가 통화 버튼을 숨긴다
    lat: Number(r.lat),
    lng: Number(r.lng),
    address: r.address ?? null,
  };
}
