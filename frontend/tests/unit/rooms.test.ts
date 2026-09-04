// 새로 만든 방 셋의 부품 — 안내봇과 즐겨찾기 (2026-09-03)
//
// 여기서 지키려는 것은 화면 모양이 아니라 **약속**이다.
//   · 안내봇은 모르는 것을 지어내지 않는다.
//   · 등급 이름은 화면 표시 명칭과 한 글자도 다르지 않다(CLAUDE.md).
//   · 즐겨찾기는 브라우저에만 남고, 저장 공간을 못 써도 화면이 죽지 않는다.
import { describe, it, expect, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { answer, opening, TOPICS, BOT_STATS, isFallback } from '../../src/services/guideBot';
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

  it('화면에 펼쳐 둔 질문은 전부 답을 가진다 — 눌렀는데 "모르겠습니다"가 나오면 안 된다', () => {
    const all = TOPICS.flatMap((g) => g.items);
    expect(all.filter((q) => answer(q).text.includes('확실히 알지 못합니다'))).toEqual([]);
    expect(all.length).toBeGreaterThanOrEqual(100);
    expect(BOT_STATS.asks).toBe(all.length);
  });

  it('같은 질문이 두 묶음에 겹쳐 있지 않다', () => {
    const all = TOPICS.flatMap((g) => g.items);
    expect(all.filter((q, i) => all.indexOf(q) !== i)).toEqual([]);
  });

  it('화면에서 누른 질문은 열쇳말 경쟁을 거치지 않고 제 규칙으로 간다', () => {
    // 열쇳말만으로는 다른 규칙에 뺏기던 것들. 글자 그대로 맞으면 그리로 간다.
    expect(answer('형제자매도 지원이 있나요?').text).toContain('가족 지원');
    expect(answer('누가 만든 서비스인가요?').text).toContain('공식 창구가 아니고');
    expect(answer('비용이 드나요?').text).toContain('무료입니다');
    expect(answer('별점 평균은 믿을 만한가요?').text).toContain('평균이 크게 흔들립니다');
    // 띄어쓰기·물음표가 달라도 같은 답으로 간다
    expect(answer('얼마나걸리나요').text).toContain('3분쯤');
  });

  it('펼쳐 둔 질문이 엉뚱한 주제로 새지 않는다', () => {
    // 열쇳말이 겹치기 쉬운 것들만 골라 짚는다
    expect(answer('결과를 저장할 수 있나요?').text).toContain('보관하지 않습니다');
    expect(answer('위치 권한을 안 주면 어떻게 되나요?').text).toContain('직접 고르시면');
    expect(answer('우리 동네에 기관이 없다고 나와요').text).toContain('기관 정보가 들어오지 않은 지역');
    expect(answer('제가 쓴 후기를 지우고 싶어요').text).toContain('지우기');
    expect(answer('형제자매도 지원이 있나요?').text).toContain('가족 지원');
    expect(answer('누가 만든 서비스인가요?').text).toContain('공식 복지 자격 판정도 하지 않습니다');
    expect(answer('신청 방법과 서류가 궁금해요').text).toContain('확실히 안내해 드리기 어렵습니다');
  });

  it('급한 상황에는 화면에 머물지 말라고 먼저 말한다', () => {
    expect(answer('지금 급해요').text).toContain('바로 연락하시는 편이 낫습니다');
  });

  /* ── 2차 확장(09-04)에서 채운 자리 ────────────────────────────────────
     화면에 없는 말로 물었을 때 새던 것들이다. 규칙을 손보다 보면 열쇳말이
     서로 잡아먹어 조용히 되돌아가므로, 여기에 못으로 박아 둔다. */
  it('화면 목록에 없는 말로 물어도 답한다 — 자유 입력 50가지', () => {
    const asked = [
      '왜 7개인가요', '점수가 몇 점인가요', '백분위가 나오나요',
      '기관에 바로 예약할 수 있나요', '기관 운영시간이 궁금해요', '주말에도 하나요',
      '차량 지원이 되나요', '우리 지역만 보고 싶어요', '지도에서 목록으로 바꾸고 싶어요',
      '방과후활동은 몇 시부터인가요', '바우처인가요', '소득 기준이 있나요',
      '중복해서 이용할 수 있나요', '쿠키를 쓰나요', '제 정보를 제3자에게 주나요',
      '탈퇴는 어떻게 하나요', '광고가 있나요', '제 답변을 언제까지 보관하나요',
      '별점만 남길 수 있나요', '너 누구야', '사람인가요', '챗지피티인가요',
      '한국어 말고 다른 말도 되나요', '대화를 저장할 수 있나요', '다크모드 있나요',
      '앱으로 나오나요', '인터넷이 끊기면 어떻게 되나요', '어떤 브라우저에서 되나요',
      '글자를 더 크게 하고 싶어요', '아이가 학교를 안 가려고 해요', '자립지원은 어떻게 하나요',
      '문의는 어디로 하나요', '건의사항이 있어요', '후기를 수정할 수 있나요',
      '후기를 신고하고 싶어요', '후기에 사진을 올릴 수 있나요', '활동지원사는 어떻게 구하나요',
      '부모교육 프로그램 있나요', '오류를 신고하고 싶어요', '문항을 더 자세히 알려주세요',
      '결과를 인쇄할 수 있나요', '기관 운영시간이랑 차량 지원이요', '형제자매 심리상담도 되나요',
      '주간활동 시간이 얼마나 되나요', '후기 몇 자까지 쓸 수 있나요', '제 위치가 어디까지 남나요',
      '결과를 카톡으로 보내고 싶어요', '점수 알려줘', '문항이 왜 이렇게 적나요', '건의하고 싶어요',
    ];
    const missed = asked.filter((q) => answer(q).text.includes('확실히 알지 못합니다'));
    expect(missed).toEqual([]);
  });

  it('모르는 영역은 새 규칙에서도 지어내지 않는다 — 어디에 물을지로 넘긴다', () => {
    // 운영시간·소득 기준·정서적 어려움은 우리가 갖고 있지 않은 정보다.
    expect(answer('기관 운영시간이 궁금해요').text).toContain('직접 물어보시는 것이 가장 정확합니다');
    expect(answer('소득 기준이 있나요').text).toContain('확실히 말씀드릴 수 없습니다');
    expect(answer('아이가 학교를 안 가려고 해요').text).toContain('발달장애인지원센터');
  });

  it('아직 없는 기능은 없다고 말한다 — 있는 척하지 않는다', () => {
    // 신고는 09-04 오후에 실제로 만들었으므로 여기서 빠졌다. 아래 전용 테스트가 받는다.
    expect(answer('후기를 수정할 수 있나요').text).toContain('고치는 기능은 아직 없습니다');
    expect(answer('다크모드 있나요').text).toContain('아직 없습니다');
  });

  it('자기가 무엇인지 정확히 말한다 — LLM 인 척하지 않는다', () => {
    const r = answer('챗지피티인가요');
    expect(r.text).toContain('사람이 아닙니다');
    expect(r.text).toContain('미리 적어 둔 답');
  });

  it('화면 목록만 담당하는 규칙과 자유 입력만 담당하는 규칙이 갈려 있다', () => {
    // asks 가 빈 규칙은 목록을 늘리지 않는다. 목록이 길어지면 훑기가 어려워지므로
    // 덜 묻는 것은 목록 밖에 두고 자유 입력으로만 닿게 한다는 설계다.
    const listed = TOPICS.flatMap((g) => g.items);
    expect(BOT_STATS.asks).toBe(listed.length);
    expect(BOT_STATS.rules).toBeGreaterThan(listed.length / 2);
    expect(listed).not.toContain('쿠키를 쓰나요');
    expect(answer('쿠키를 쓰나요').text).toContain('쿠키는 쓰지 않습니다');
  });

  /* ── 3차(09-04 오후) — 신고·미답변 질문 수집·운영 지속 ────────────────── */
  it('답을 못 낸 것만 isFallback 이다 — 화면이 이걸로 미답변 질문을 가려낸다', () => {
    expect(isFallback(answer('오늘 서울 날씨 어때요?'))).toBe(true);
    expect(isFallback(answer('   '))).toBe(true);
    // 화면에 펼쳐 둔 질문은 하나도 미답변으로 새지 않는다 = 서버로도 안 간다
    expect(TOPICS.flatMap((g) => g.items).filter((q) => isFallback(answer(q)))).toEqual([]);
  });

  it('대화 저장 안내가 미답변 질문 수집을 숨기지 않는다', () => {
    // 이 문구가 사실과 어긋나면 서비스가 이용자에게 거짓말을 하게 된다.
    const t = answer('여기 나눈 대화는 어디에 남나요?').text;
    expect(t).toContain('브라우저 안에만 남습니다');
    expect(t).toContain('답해 드리지 못한 질문은 그 문장만 따로');
    expect(t).toContain('누가 물으셨는지는 함께 보내지 않고');
    // 개인정보 총론에도 같은 사실이 있어야 한다
    expect(answer('개인정보는 어떻게 되나요?').text).toContain('답해 드리지 못한 질문');
  });

  it('후기 신고를 이제 받는다고 말한다 — 없다고 하던 답이 남아 있으면 안 된다', () => {
    const t = answer('후기를 신고하고 싶어요').text;
    expect(t).toContain('신고');
    expect(t).not.toContain('신고를 받는 화면이 없습니다');
    expect(t).toContain('가려집니다');
  });

  it('계속 운영한다고 답한다', () => {
    expect(answer('이 서비스는 언제까지 운영하나요').text).toContain('문을 닫을 계획은 없습니다');
  });

  it('화면은 마크다운을 해석하지 않으므로 별표를 남기지 않는다', () => {
    const texts = [
      opening().text,
      ...TOPICS.flatMap((g) => g.items).map((q) => answer(q).text),
      ...['상담', '감사합니다', '안녕하세요', '알 수 없는 말'].map((q) => answer(q).text),
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
