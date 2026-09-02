// 추론 서비스 장애 안내 (설계 4.9.4)
//   판정 불가와 구분되어야 한다 — 부담 수준과 무관한 일시적 장애다.
import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import UnavailableNotice from '../../src/components/UnavailableNotice.vue';

const NOTICE = '지금은 진단 결과를 드릴 수 없습니다. 잠시 후 다시 시도해 주세요.';

describe('UnavailableNotice', () => {
  it('진단을 드릴 수 없다는 사실을 알린다', () => {
    const w = mount(UnavailableNotice, { props: { name: '햇살맘', notice: NOTICE } });
    expect(w.text()).toContain('햇살맘님께 드리는 안내');
    expect(w.text()).toContain('지금은 진단 결과를 드릴 수 없습니다');
  });

  it('부담 구간을 뜻하는 말을 쓰지 않는다', () => {
    // 장애를 판정 결과로 오해하게 만들면 안 된다
    const w = mount(UnavailableNotice, { props: { name: '보호자', notice: NOTICE } });
    expect(w.text()).not.toContain('부담군');
    expect(w.text()).not.toContain('판정 불가');
  });

  it('내부 라벨 숫자를 노출하지 않는다 (FR-010a)', () => {
    const w = mount(UnavailableNotice, { props: { name: '보호자', notice: NOTICE } });
    expect(w.text()).not.toMatch(/\b[1-5]\s*(단계|등급)\b/);
  });
});
