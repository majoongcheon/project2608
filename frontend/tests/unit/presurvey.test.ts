// 사전 입력 → 설문 이동 (FR-002e)
//   나이는 <input type="number"> 라 v-model 이 값을 number 로 캐스팅한다.
//   문자열로 가정하고 다루면 클릭이 예외로 죽어 이동 자체가 막힌다.
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import PreSurveyPage from '../../src/pages/PreSurveyPage.vue';
import { usePreSurveyStore } from '../../src/stores/preSurvey';

const push = vi.fn();
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }));
vi.mock('../../src/services/apiClient', () => ({
  api: { questions: vi.fn().mockResolvedValue({ version: 'qs-v1.0.0', questions: [] }),
         config: vi.fn().mockResolvedValue({}), events: vi.fn().mockResolvedValue({}) },
}));

function setup() {
  setActivePinia(createPinia());
  return mount(PreSurveyPage);
}

describe('PreSurveyPage — 나이 입력 후 진단 시작', () => {
  beforeEach(() => push.mockClear());

  it('나이를 입력하고 눌러도 설문으로 넘어간다', async () => {
    const w = setup();
    await w.get('#age').setValue('22');
    await w.get('button.btn:not(.btn--ghost)').trigger('click');
    expect(push).toHaveBeenCalledWith('/diagnosis/survey');
  });

  it('입력한 나이가 스토어에 숫자로 담긴다', async () => {
    const w = setup();
    await w.get('#age').setValue('22');
    await w.get('button.btn:not(.btn--ghost)').trigger('click');
    expect(usePreSurveyStore().careTargetAge).toBe(22);
  });

  it('비워 두고 눌러도 넘어가며 나이는 null 이다', async () => {
    const w = setup();
    await w.get('button.btn:not(.btn--ghost)').trigger('click');
    expect(push).toHaveBeenCalledWith('/diagnosis/survey');
    expect(usePreSurveyStore().careTargetAge).toBeNull();
  });
});
