// 원형 척도 선택기(ScaleDial) — 화면을 보고서야 드러났던 결함들을 여기서 고정한다.
//   ① 눈금이 원 둘레에 퍼진다 (한가운데로 뭉치던 것)
//   ② 고르기 전에는 바늘이 없다 (12시에 세워 두면 3번을 고른 것으로 읽혔다)
//   ③ 숫자는 눈금 바깥으로 (12시 눈금에서 바늘이 숫자를 덮었다)
//   ④ 색이 아니라 글자로 뜻을 전한다 (FR-041) · 키보드로 다 된다 (FR-039)
import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import ScaleDial from '../../src/components/ScaleDial.vue';

const OPTIONS = [
  { value: 1, label: '매우 싫어한다' },
  { value: 2, label: '싫어하는 편' },
  { value: 3, label: '보통' },
  { value: 4, label: '좋아하는 편' },
  { value: 5, label: '매우 좋아한다' },
];
const ARIA = '당사자는 요즘 하루하루의 일과를 어떻게 느끼고 있나요?';
const mk = (modelValue: number | null | undefined = undefined) =>
  mount(ScaleDial, { props: { options: OPTIONS, modelValue, ariaLabel: ARIA } });

// "left: 12.3%" 에서 12.3 을 꺼낸다
const num = (style: string, key: string) =>
  Number(new RegExp(`${key}:\\s*(-?[\\d.]+)%`).exec(style)?.[1] ?? NaN);

describe('ScaleDial — 눈금 배치', () => {
  it('눈금이 원 둘레에 퍼진다 — 가운데로 뭉치지 않는다', () => {
    const ticks = mk().findAll('.tick');
    expect(ticks).toHaveLength(5);
    const pos = ticks.map((t) => {
      const s = t.attributes('style') ?? '';
      return { x: num(s, 'left'), y: num(s, 'top') };
    });
    // 중심(50,50)에서 모두 같은 거리(=반지름)만큼 떨어져 있어야 한다.
    const r = pos.map((p) => Math.hypot(p.x - 50, p.y - 50));
    r.forEach((v) => expect(v).toBeGreaterThan(20));   // 뭉쳐 있던 때는 0 에 가까웠다
    expect(Math.max(...r) - Math.min(...r)).toBeLessThan(0.5);
    // 왼쪽 끝(1)부터 오른쪽 끝(5)까지 x 가 단조 증가 — 순서가 눈에 보인다
    const xs = pos.map((p) => p.x);
    expect(xs).toEqual([...xs].sort((a, b) => a - b));
    // 가운데 눈금(3)은 12시 방향
    expect(pos[2].x).toBeCloseTo(50, 5);
    expect(pos[2].y).toBeLessThan(50);
  });

  it('숫자를 눈금 바깥으로 민다 — 안쪽은 바늘이 지나가는 자리다', () => {
    const ticks = mk().findAll('.tick');
    const s3 = ticks[2].attributes('style') ?? '';        // 12시 눈금
    expect(/--nx:\s*0(\.0)?px/.test(s3)).toBe(true);      // 좌우로는 안 밀고
    const ny = Number(/--ny:\s*(-?[\d.]+)px/.exec(s3)?.[1]);
    expect(ny).toBeLessThan(0);                            // 위쪽(바깥)으로 민다
  });
});

describe('ScaleDial — 고르기 전', () => {
  it('바늘을 그리지 않는다 (고른 것처럼 보이면 안 된다)', () => {
    const w = mk(undefined);
    expect(w.find('.dial__hand').exists()).toBe(false);
    expect(w.findAll('.tick--on')).toHaveLength(0);
    expect(w.find('[aria-checked="true"]').exists()).toBe(false);
  });

  it('무엇을 하면 되는지 글자로 알린다', () => {
    expect(mk(undefined).find('.dial__hint').text()).toContain('고르세요');
  });
});

describe('ScaleDial — 고른 뒤', () => {
  it('바늘이 고른 눈금 쪽을 향하고, 뜻은 글자로 뜬다 (FR-041)', () => {
    const w = mk(5);
    expect(w.find('.dial__hand').exists()).toBe(true);
    expect(w.find('.dial__label').text()).toBe('매우 좋아한다');
    expect(w.findAll('.tick')[4].classes()).toContain('tick--on');
  });

  it('역방향 척도의 1도 정상으로 잡는다 (1이 최고부담)', () => {
    const w = mk(1);
    expect(w.find('.dial__label').text()).toBe('매우 싫어한다');
    expect(w.findAll('.tick')[0].attributes('aria-checked')).toBe('true');
  });
});

describe('ScaleDial — 조작', () => {
  it('눈금을 누르면 그 값을 올려보낸다', async () => {
    const w = mk(undefined);
    await w.findAll('.tick')[3].trigger('click');
    expect(w.emitted('update:modelValue')?.[0]).toEqual([4]);
  });

  it('키보드로 옮긴다 — 화살표·Home·End (FR-039)', async () => {
    const w = mk(3);
    await w.find('.dial').trigger('keydown', { key: 'ArrowRight' });
    await w.find('.dial').trigger('keydown', { key: 'ArrowLeft' });
    await w.find('.dial').trigger('keydown', { key: 'Home' });
    await w.find('.dial').trigger('keydown', { key: 'End' });
    expect(w.emitted('update:modelValue')).toEqual([[4], [2], [1], [5]]);
  });

  it('양 끝에서는 더 나가지 않는다', async () => {
    const w = mk(5);
    await w.find('.dial').trigger('keydown', { key: 'ArrowRight' });
    expect(w.emitted('update:modelValue')?.[0]).toEqual([5]);
  });

  it('Tab 은 다이얼 하나를 한 번에 지난다 (roving tabindex)', () => {
    const tabs = mk(2).findAll('.tick').map((t) => t.attributes('tabindex'));
    expect(tabs.filter((t) => t === '0')).toHaveLength(1);
    expect(tabs[1]).toBe('0');   // 고른 눈금이 그 하나
  });
});

describe('ScaleDial — 화면낭독기', () => {
  it('묶음에 문항 이름이 실리고, 눈금마다 선택지 전체 문구가 읽힌다', () => {
    const w = mk(undefined);
    expect(w.find('.dial').attributes('aria-label')).toBe(ARIA);
    expect(w.find('.dial').attributes('role')).toBe('radiogroup');
    const sr = w.findAll('.tick .sr').map((e) => e.text());
    expect(sr).toEqual(OPTIONS.map((o) => o.label));
  });

  it('양 끝이 무엇인지 눈으로도 남긴다 — 눈금 1·5 와 같은 높이에 붙인다', () => {
    const w = mk(undefined);
    expect(w.find('.end--min').text()).toBe('매우 싫어한다');
    expect(w.find('.end--max').text()).toBe('매우 좋아한다');
    // 라벨의 세로 자리(--end-y)가 눈금 1·5 의 세로 자리와 같아야 나란히 선다
    const endY = /--end-y:\s*([\d.]+)%/.exec(w.find('.dialwrap').attributes('style') ?? '')?.[1];
    const tickY = /top:\s*([\d.]+)%/.exec(w.findAll('.tick')[0].attributes('style') ?? '')?.[1];
    expect(Number(endY)).toBeCloseTo(Number(tickY), 5);
  });
});
