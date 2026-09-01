import { Router } from 'express';
import { query, one, exec } from '../repositories/pool.js';
import { cfg } from '../config/configStore.js';
import {
  findNearby, findByRegion, findById, toCard, haversineKm, type ServiceType,
} from '../services/facilityService.js';
import { ApiError, wrap } from '../middleware/errors.js';

export const facilitiesRouter = Router();

// GET /regions — 전국 229개. hasFacilityData 로 확보 여부를 알린다(FR-016a·FR-016b)
facilitiesRouter.get('/regions', wrap(async (_req, res) => {
  const rows = await query(
    `SELECT region_code, sido_name, sigungu_name, center_lat, center_lng,
            has_facility_data, metro_contact_name, metro_contact_phone
       FROM cb_region_v1 ORDER BY sido_name, sigungu_name`);
  res.json({
    regions: rows.map((r: any) => ({
      regionCode: r.region_code,
      sidoName: r.sido_name,
      sigunguName: r.sigungu_name,
      centerLat: r.center_lat == null ? null : Number(r.center_lat),
      centerLng: r.center_lng == null ? null : Number(r.center_lng),
      hasFacilityData: Boolean(r.has_facility_data),
    })),
  });
}));

// GET /facilities — 거리순 조회 (FR-016·FR-020·FR-021-1)
facilitiesRouter.get('/facilities', wrap(async (req, res) => {
  const ranges = cfg<any>('age.serviceRanges');
  const steps = cfg<{ steps: number[] }>('referral.radiusStepsKm').steps;

  const q = req.query;
  const serviceType = q.serviceType ? (String(q.serviceType) as ServiceType) : undefined;
  const limit = Math.min(Number(q.limit ?? 20), 100);
  let lat = q.lat == null ? null : Number(q.lat);
  let lng = q.lng == null ? null : Number(q.lng);
  const regionCode = q.regionCode ? String(q.regionCode) : null;

  if ((lat === null || lng === null) && !regionCode) {
    throw new ApiError(400, 'LOCATION_REQUIRED', 'lat/lng 또는 regionCode 중 하나가 필요합니다.');
  }

  let regionDataPending = false;
  let metroContact: any = null;
  let regionCenter: { lat: number; lng: number } | null = null;
  if (regionCode) {
    const r = await one<any>(
      `SELECT center_lat, center_lng, has_facility_data, metro_contact_name, metro_contact_phone
         FROM cb_region_v1 WHERE region_code = ?`, [regionCode]);
    if (!r) throw new ApiError(404, 'REGION_NOT_FOUND', '해당 지역을 찾을 수 없습니다.');
    regionDataPending = !r.has_facility_data;
    if (regionDataPending) {
      metroContact = { name: r.metro_contact_name, phone: r.metro_contact_phone };
    }
    if (r.center_lat != null && r.center_lng != null) {
      regionCenter = { lat: Number(r.center_lat), lng: Number(r.center_lng) };
    }
  }

  // 지역만 고른 경우에는 **그 지역 안의 기관만** 돌려준다.
  // 인근 지역 기관을 조용히 섞으면 보호자가 선택한 지역에 있는 것으로 오인한다.
  // 범위 확대는 FR-020 에 따라 '선택지'로 제공하며, 프론트가 regionCenter 좌표로 다시 호출한다.
  if (regionCode && (q.lat == null || q.lng == null)) {
    const rows = await findByRegion(regionCode, serviceType, limit);
    return res.json({
      facilities: rows.map((r) => toCard(r, ranges, null)),
      radiusKm: null,
      suggestedRadiusKm: rows.length === 0 ? steps[0] : null,
      regionDataPending,
      metroContact,
      regionCenter,
    });
  }

  // 좌표가 주어졌으면 거리순 조회
  if (lat !== null && lng !== null) {
    const requested = q.radiusKm == null ? steps[0] : Number(q.radiusKm);
    const rows = await findNearby(lat, lng, requested, serviceType, limit);
    let suggested: number | null = null;
    if (rows.length === 0) {
      suggested = steps.find((s) => s > requested) ?? null;
    }
    return res.json({
      facilities: rows.map((r) => toCard(r, ranges, haversineKm(lat!, lng!, Number(r.lat), Number(r.lng)))),
      radiusKm: requested,
      suggestedRadiusKm: suggested,
      regionDataPending,
      metroContact,
      regionCenter,
    });
  }

  throw new ApiError(400, 'LOCATION_REQUIRED', '기준 위치를 확인할 수 없습니다.');
}));

// GET /facilities/:id — 상세 (FR-017·FR-019)
facilitiesRouter.get('/facilities/:id', wrap(async (req, res) => {
  const ranges = cfg<any>('age.serviceRanges');
  const r = await findById(Number(req.params.id));
  if (!r) throw new ApiError(404, 'NOT_FOUND', '기관을 찾을 수 없습니다.');
  const card = toCard(r, ranges, null);   // lat·lng·address 는 카드에 이미 포함된다
  res.json({
    ...card,
    updatedAt: r.updated_at ? new Date(r.updated_at).toISOString().slice(0, 10) : null,
  });
}));

// POST /facilities/:id/reports — 정보 오류 신고 (FR-019b). 신고자 연락처는 받지 않는다.
facilitiesRouter.post('/facilities/:id/reports', wrap(async (req, res) => {
  const allowed = ['PHONE', 'ADDRESS', 'CLOSED', 'SERVICE', 'OTHER'];
  const type = String(req.body?.reportType ?? '');
  if (!allowed.includes(type)) {
    throw new ApiError(400, 'INVALID_REPORT_TYPE', '신고 유형이 올바르지 않습니다.');
  }
  const facility = await findById(Number(req.params.id));
  if (!facility) throw new ApiError(404, 'NOT_FOUND', '기관을 찾을 수 없습니다.');
  const detail = req.body?.detail == null ? null : String(req.body.detail).slice(0, 500);
  await exec(
    'INSERT INTO cb_facility_report_v1 (facility_id, report_type, detail) VALUES (?, ?, ?)',
    [Number(req.params.id), type, detail]);
  res.status(202).json({ status: 'RECEIVED' });
}));
