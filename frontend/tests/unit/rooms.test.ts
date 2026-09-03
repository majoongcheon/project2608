// 새로 만든 방 셋의 부품 — 안내봇과 즐겨찾기 (2026-09-03)
//
// 여기서 지키려는 것은 화면 모양이 아니라 **약속**이다.
//   · 안내봇은 모르는 것을 지어내지 않는다.
//   · 등급 이름은 화면 표시 명칭과 한 글자도 다르지 않다(CLAUDE.md).
//   · 즐겨찾기는 브라우저에만 남고, 저장 공간을 못 써도 화면이 죽지 않는다.
import { describe, it, expect, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { answer, opening } from '../../src/services/guideBot';
import { useFavoriteStore } from '../../src/stores/favorites';

/* 이 실행 환경이 주는 localStorage 는 반쪽짜리다(clear 가 없다). 저장소는
   이 테스트가 재려는 대상 그 자체이므로, 환경에 기대지 않고 직접 세워 쓴다.
   실패를 흉내 내는 것도 여기서 함께 한다 — 사생활 보호 모드처럼 쓰기가
   막히는 브라우저가 실제로 있고, 그때 화면이 죽으면 안 된다. */
function installStorage(opts: { failWrites?: boolean } = {}) {
  const map = new Map<string, string>();
  const stub = {
    getItem: (k: string) => (map.has(k) ? map.get(k)! : null),
    setItem: (k: string, v: string) => {
      if (opts.failWrites) throw new Error('QuotaExceededError');
      map.set(k, String(v));
    },
    removeItem: (k: string) => { map.delete(k); },
    clear: () => map.clear(),
  };
  Object.defineProperty(globalThis, 'localStorage', {
    value: stub, configurable: true, writable: true,
  });
  return stub;
}

describe('안내봇 — 무엇을 답하는가', () => {
  it('처음 열면 무엇을 물어도 되는지 먼저 보여 준다', () => {
    const o = opening();
    expect(o.text).toContain('곁');
    expect(o.suggestions?.length).toBeGreaterThanOrEqual(3);
  });

  it('판정 불가를 물으면 "부담 없음"으로도 "부담이 크다"로도 읽히지 않게 답한다', () => {
    const r = answer('판정 불가가 무슨 뜻인가요?');
    expect(r.text).toContain('부담이 없다는 뜻도, 크다는 뜻도 아닙니다');
  });

  it('더 구체적인 열쇳말이 이긴다 — "판정 불가"가 "진단"에 밀리지 않는다', () => {
    const a = answer('진단에서 판정 불가가 나왔어요');
    expect(a.text).toContain('한 구간을 고르기 어렵다');
  });

  it('등급 이름은 화면 표시 명칭 그대로다 (CLAUDE.md)', () => {
    const r = answer('결과는 어떻게 나오나요?');
    for (const g of ['최고부담군', '고부담군', '중간부담군', '저부담군', '부담 없음']) {
      expect(r.text).toContain(g);
    }
    // 내부 라벨 숫자를 노출하지 않는다 (FR-010a)
    expect(r.text).not.toMatch(/\b[1-5]\s*(등급|단계)\b/);
  });

  it('자격을 판정하지 않는다고 분명히 말한다', () => {
    expect(answer('저희 아이가 이용 대상이 되나요?').text).toContain('자격을 판정하지 않습니다');
  });

  it('모르는 것은 지어내지 않고 모른다고 답한다', () => {
    const r = answer('오늘 서울 날씨 어때요?');
    expect(r.text).toContain('확실히 알지 못합니다');
    expect(r.suggestions?.length).toBeGreaterThan(0);
  });

  it('빈 입력에도 무너지지 않는다', () => {
    expect(answer('   ').text).toContain('확실히 알지 못합니다');
  });

  it('화면은 마크다운을 해석하지 않으므로 별표를 남기지 않는다', () => {
    const texts = [
      opening().text,
      ...['진단', '결과', '판정 불가', '개인정보', '신청처', '이용 대상', '후기', '즐겨찾기',
        '상담', '모델', '비용', '감사합니다', '안녕하세요', '알 수 없는 말'].map((q) => answer(q).text),
    ];
    for (const t of texts) expect(t).not.toContain('**');
  });
});

describe('즐겨찾기 — 브라우저에만 남는 목록', () => {
  const F = {
    facilityId: 7, name: '강릉시 주간활동서비스 센터', phone: '033-000-0000',
    address: '강원 강릉시', serviceTypes: ['DAY_ACTIVITY'],
  };

  beforeEach(() => {
    installStorage();
    setActivePinia(createPinia());
  });

  it('담고 빼는 것이 눌린 대로 동작한다', () => {
    const fav = useFavoriteStore();
    expect(fav.has(7)).toBe(false);
    expect(fav.toggle(F)).toBe(true);
    expect(fav.has(7)).toBe(true);
    expect(fav.toggle(F)).toBe(false);
    expect(fav.has(7)).toBe(false);
  });

  it('같은 기관을 두 번 담아도 하나만 남는다', () => {
    const fav = useFavoriteStore();
    fav.add(F); fav.add(F);
    expect(fav.items).toHaveLength(1);
  });

  it('브라우저에 저장되고 언제 담았는지 남는다', () => {
    const fav = useFavoriteStore();
    fav.add(F);
    const saved = JSON.parse(localStorage.getItem('cb.favorites') ?? '[]');
    expect(saved[0].facilityId).toBe(7);
    expect(Date.parse(saved[0].savedAt)).not.toBeNaN();
  });

  it('저장 공간을 못 쓰는 브라우저에서도 화면이 죽지 않는다', () => {
    installStorage({ failWrites: true });   // 사생활 보호 모드 등
    setActivePinia(createPinia());
    const fav = useFavoriteStore();
    expect(() => fav.add(F)).not.toThrow();
    expect(fav.has(7)).toBe(true);   // 이번 방문 동안에는 그대로 쓸 수 있다
  });

  it('저장된 값이 망가져 있어도 빈 목록으로 시작한다', () => {
    localStorage.setItem('cb.favorites', '{ 이건 JSON 이 아니다');
    setActivePinia(createPinia());
    expect(useFavoriteStore().items).toEqual([]);
  });
});
