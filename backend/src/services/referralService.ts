// 즉시 연계 (FR-021 ~ FR-021j-1)
//   3축: 부담 구간 = 발동 임계값 · 연령 = 유형 필터 · 거리 = 정렬 기준
//   내부 라벨은 1이 최고부담인 역방향 척도이므로 임계값 비교는 '이하'다.
import { cfg } from '../config/configStore.js';
import {
  findNearby, findByRegion, toCard, type ServiceType, type FacilityCard, haversineKm,
} from './facilityService.js';
import { one } from '../repositories/pool.js';

export interface ReferralInput {
  internalLabel: number | null;       // null = 판정 불가
  undecidable: boolean;
  careTargetAge: number | null;
  lat: number | null;
  lng: number | null;
  regionCode: string | null;
}

export interface AgeOutOfRange { notice: string; alternativeContact: string }

export interface ImmediateReferral {
  facilities: FacilityCard[];
  emphasizeCounseling: boolean;
  ageOutOfRange: AgeOutOfRange | null;
  emptyReason: string | null;
  appliedServiceType: ServiceType | null;
  radiusKm: number | null;
}

/** 판정 구간이 즉시 안내를 발동시키는가. 판정 불가도 발동한다(FR-021j). */
export function shouldRefer(internalLabel: number | null, undecidable: boolean): boolean {
  if (undecidable) return true;
  if (internalLabel === null) return false;
  return internalLabel <= cfg<{ maxInternalLabel: number }>('referral.threshold').maxInternalLabel;
}

/**
 * 연령 → 서비스 유형 매핑 (FR-021h).
 * 이 매핑은 **안내할 유형을 정하는 절차이지 이용 자격 판정이 아니다**(FR-021h-1).
 * 연령을 이유로 목록을 차단하지 않는다(FR-021i-2).
 */
export function mapAgeToServiceType(age: number | null): ServiceType | null {
  if (age === null || Number.isNaN(age)) return null;      // 미입력 → 전체 유형(FR-021i)
  const boundary = cfg<{ boundary: number }>('age.mappingBoundary').boundary;
  return age < boundary ? 'AFTERSCHOOL_YOUTH' : 'DAY_ACTIVITY';
}

/** 이용 대상 연령 범위를 벗어났는지 (FR-021i-1). 벗어나도 기관은 그대로 표시한다. */
export function checkAgeRange(age: number | null): AgeOutOfRange | null {
  if (age === null || Number.isNaN(age)) return null;
  const n = cfg<any>('age.outOfRangeNotice');
  if (age < n.under.threshold) {
    return { notice: n.under.notice, alternativeContact: n.under.alternativeContact };
  }
  if (age >= n.over.threshold) {
    return { notice: n.over.notice, alternativeContact: n.over.alternativeContact };
  }
  return null;
}

export async function buildReferral(input: ReferralInput): Promise<ImmediateReferral | null> {
  if (!shouldRefer(input.internalLabel, input.undecidable)) return null;

  const ranges = cfg<any>('age.serviceRanges');
  const count = cfg<{ count: number }>('referral.facilityCount').count;
  const steps = cfg<{ steps: number[] }>('referral.radiusStepsKm').steps;
  const counselThreshold =
    cfg<{ maxInternalLabel: number }>('referral.counselingThreshold').maxInternalLabel;

  const serviceType = mapAgeToServiceType(input.careTargetAge);
  const ageOutOfRange = checkAgeRange(input.careTargetAge);

  // 기준 좌표 결정: 실제 위치 우선, 없으면 선택한 지역의 대표 좌표(FR-021d)
  let lat = input.lat, lng = input.lng;
  if ((lat === null || lng === null) && input.regionCode) {
    const r = await one<{ center_lat: number; center_lng: number }>(
      'SELECT center_lat, center_lng FROM cb_region_v1 WHERE region_code = ?', [input.regionCode]);
    if (r) { lat = Number(r.center_lat); lng = Number(r.center_lng); }
  }

  const emphasize = input.internalLabel !== null && input.internalLabel <= counselThreshold;

  if (lat === null || lng === null) {
    return {
      facilities: [], emphasizeCounseling: emphasize, ageOutOfRange,
      emptyReason: '기준 위치를 확인할 수 없습니다. 지역을 선택하시면 가까운 기관을 안내해 드립니다.',
      appliedServiceType: serviceType, radiusKm: null,
    };
  }

  // 반경을 단계적으로 넓혀 가며 찾는다 (FR-021f)
  for (const radius of steps) {
    let rows = await findNearby(lat, lng, radius, serviceType ?? undefined, count);
    // 연령에 맞는 유형이 인근에 없으면 유형 제한을 풀어 안내한다.
    // 대상 조건은 카드에 병기되므로 오안내가 아니다(FR-021b·FR-021i-2).
    if (rows.length === 0 && serviceType) {
      rows = await findNearby(lat, lng, radius, undefined, count);
    }
    if (rows.length > 0) {
      return {
        facilities: rows.map((r) =>
          toCard(r, ranges, haversineKm(lat!, lng!, Number(r.lat), Number(r.lng)))),
        emphasizeCounseling: emphasize,
        ageOutOfRange,
        emptyReason: null,
        appliedServiceType: serviceType,
        radiusKm: radius,
      };
    }
  }

  return {
    facilities: [], emphasizeCounseling: emphasize, ageOutOfRange,
    emptyReason: `기준 위치에서 ${steps[steps.length - 1]}km 안에 등록된 신청 접수처가 없습니다. 광역 대표 문의처로 연락해 보세요.`,
    appliedServiceType: serviceType, radiusKm: steps[steps.length - 1],
  };
}
