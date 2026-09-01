// 결과 표시 규칙 (FR-010a·FR-010b·FR-011-1·FR-041·FR-042)
import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import BurdenResultCard from '../../src/components/BurdenResultCard.vue';
import ContributionList from '../../src/components/ContributionList.vue';

describe('BurdenResultCard', () => {
  it('구간 명칭을 텍스트로 표시한다 — 색상만으로 구분하지 않는다 (FR-041)', () => {
    const w = mount(BurdenResultCard, {
      props: { label: '고부담군', description: '설명', isWarning: true, name: '햇살맘' },
    });
    expect(w.text()).toContain('고부담군');
    expect(w.text()).toContain('햇살맘님의 진단 결과입니다');
  });

  it('경고를 텍스트로도 알린다 — 색·아이콘에만 의존하지 않는다 (FR-042)', () => {
    const warn = mount(BurdenResultCard, {
      props: { label: '최고부담군', description: '', isWarning: true, name: '보호자' },
    });
    expect(warn.text()).toContain('주의가 필요한 결과입니다');

    const calm = mount(BurdenResultCard, {
      props: { label: '저부담군', description: '', isWarning: false, name: '보호자' },
    });
    expect(calm.text()).not.toContain('주의가 필요한 결과입니다');
  });

  it('내부 라벨 숫자를 노출하지 않는다 (FR-010a)', () => {
    const w = mount(BurdenResultCard, {
      props: { label: '최고부담군', description: '돌봄 부담이 매우 큰 상태로 보입니다.', isWarning: true, name: '보호자' },
    });
    // 구간을 뜻하는 1~5 숫자가 화면에 없어야 한다
    expect(w.text()).not.toMatch(/\b[1-5]\s*(단계|등급)\b/);
  });
});

describe('ContributionList', () => {
  it('약한 요인을 구분해 표시한다 (FR-011-1)', () => {
    const w = mount(ContributionList, {
      props: {
        items: [
          { text: '도움 필요량 — "일과 대부분"', isMinor: false },
          { text: '가족 지지 — "보통"', isMinor: true },
        ],
      },
    });
    expect(w.text()).toContain('주요 근거');
    expect(w.text()).toContain('일부 영향');
  });

  it('기여도 크기를 숫자로 표기하지 않는다 (research.md R-3 폴백 규칙)', () => {
    const w = mount(ContributionList, {
      props: { items: [{ text: '요인 A', isMinor: false }] },
    });
    expect(w.text()).not.toMatch(/0\.\d{3,}/);
  });

  it('인과가 아니라 동반 관찰임을 밝힌다', () => {
    const w = mount(ContributionList, { props: { items: [{ text: 'A', isMinor: false }] } });
    expect(w.text()).toContain('원인을 말하는 것은 아닙니다');
  });
});
