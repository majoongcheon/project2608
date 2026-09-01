// 척도 방향 회귀 테스트 (헌법 "척도 방향" · FR-010a·FR-010b·FR-021·FR-021c·FR-021e)
//   care_burden 은 1이 최고부담인 역방향 척도다. 이 프로젝트에서 가장 실수하기 쉬운 지점이라
//   quickstart 7장의 6행 표를 그대로 검증한다.
import { describe, it, expect, beforeAll } from 'vitest';
import { loadConfig, cfg } from '../../src/config/configStore.js';
import { shouldRefer, mapAgeToServiceType, checkAgeRange } from '../../src/services/referralService.js';

beforeAll(async () => { await loadConfig(); });

interface Row { label: number | null; und: boolean; name: string; warn: boolean; refer: boolean; counsel: boolean }
const TABLE: Row[] = [
  { label: 1,    und: false, name: '최고부담군', warn: true,  refer: true,  counsel: true  },
  { label: 2,    und: false, name: '고부담군',   warn: true,  refer: true,  counsel: false },
  { label: 3,    und: false, name: '중간부담군', warn: false, refer: false, counsel: false },
  { label: 4,    und: false, name: '저부담군',   warn: false, refer: false, counsel: false },
  { label: 5,    und: false, name: '부담 없음',  warn: false, refer: false, counsel: false },
  { label: null, und: true,  name: '',           warn: false, refer: true,  counsel: false },
];

describe('역방향 척도 (1=최고부담)', () => {
  it.each(TABLE)('내부 라벨 $label — 표시 명칭과 경고', (row) => {
    if (row.label === null) return;
    const labels = cfg<any>('burden.labels');
    expect(labels[String(row.label)].label).toBe(row.name);
    expect(labels[String(row.label)].warning).toBe(row.warn);
  });

  it.each(TABLE)('내부 라벨 $label — 즉시 안내 발동 여부', (row) => {
    expect(shouldRefer(row.label, row.und)).toBe(row.refer);
  });

  it('상담 강조는 최고부담군에만 적용된다 (FR-021e)', () => {
    const t = cfg<any>('referral.counselingThreshold').maxInternalLabel;
    for (const row of TABLE) {
      const emphasize = row.label !== null && row.label <= t;
      expect(emphasize).toBe(row.counsel);
    }
  });

  it('임계값 비교는 이하(<=)다 — 숫자가 작을수록 부담이 크다', () => {
    const t = cfg<any>('referral.threshold').maxInternalLabel;
    expect(t).toBe(2);
    expect(shouldRefer(1, false)).toBe(true);
    expect(shouldRefer(2, false)).toBe(true);
    expect(shouldRefer(3, false)).toBe(false);
  });

  it('판정 불가는 구간이 없어도 즉시 안내를 받는다 (FR-021j)', () => {
    expect(shouldRefer(null, true)).toBe(true);
  });
});

describe('연령 → 서비스 유형 매핑 (FR-021h)', () => {
  it.each([
    [5,  'AFTERSCHOOL_YOUTH'], [6,  'AFTERSCHOOL_YOUTH'], [17, 'AFTERSCHOOL_YOUTH'],
    [18, 'DAY_ACTIVITY'],      [64, 'DAY_ACTIVITY'],      [65, 'DAY_ACTIVITY'], [70, 'DAY_ACTIVITY'],
  ])('만 %i세 → %s', (age, expected) => {
    expect(mapAgeToServiceType(age as number)).toBe(expected);
  });

  it('연령 미입력이면 유형을 제한하지 않는다 (FR-021i)', () => {
    expect(mapAgeToServiceType(null)).toBeNull();
  });

  it('매핑 경계는 만 18세 단일 경계이며 겹치는 구간이 없다', () => {
    expect(mapAgeToServiceType(17)).not.toBe(mapAgeToServiceType(18));
  });
});

describe('이용 대상 연령 범위 (FR-021i-1)', () => {
  it.each([[0], [5]])('만 %i세는 범위 밖 — 아래 구간 안내', (age) => {
    const r = checkAgeRange(age as number);
    expect(r).not.toBeNull();
    expect(r!.alternativeContact).toContain('발달재활서비스');
  });

  it.each([[65], [70], [80]])('만 %i세는 범위 밖 — 위 구간 안내', (age) => {
    const r = checkAgeRange(age as number);
    expect(r).not.toBeNull();
    expect(r!.alternativeContact).toContain('노인장기요양보험');
  });

  it.each([[6], [17], [18], [64]])('만 %i세는 범위 안', (age) => {
    expect(checkAgeRange(age as number)).toBeNull();
  });

  it('연령 미입력이면 범위 밖 안내를 하지 않는다', () => {
    expect(checkAgeRange(null)).toBeNull();
  });
});
