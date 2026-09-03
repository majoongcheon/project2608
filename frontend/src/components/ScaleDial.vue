<script setup lang="ts">
/* ScaleDial — 시계 문자판처럼 돌려서 고르는 척도 선택기 (2026-09-03, 신지현)
 *
 * 근거: Ruinart Digital Fresco(SOTD 2026-04-21)의 문자판 조작.
 *
 * ── 이 화면에서 조심한 것 ────────────────────────────────────────────────
 * 레퍼런스는 **사용성 6.67 로 세 참고 사이트 중 가장 낮다.** 원형 조작은
 * 보기에 좋지만 "어디를 눌러야 하는지"가 목록보다 흐리다. 여기는 지친
 * 보호자가 7문항을 3분 안에 끝내야 하는 자리라, 예쁘다고 조작을 잃으면 안 된다.
 * 그래서 세 가지를 함께 둔다.
 *
 *   1. 눈금 하나하나가 **진짜 <button role="radio">** 다. 원을 돌리지 않고
 *      원하는 눈금을 바로 눌러도 된다. 손가락 표적은 48px 이상.
 *   2. **키보드로 다 된다** — 좌우/상하 화살표로 옮기고 Home·End 로 양 끝.
 *      roving tabindex 라 Tab 한 번이면 다이얼 하나를 지난다(FR-039).
 *   3. **목록으로 되돌릴 수 있다** — 부모가 목록 보기를 함께 제공한다.
 *      원형이 불편한 사람에게 원형만 남기지 않는다.
 *
 * 색으로 뜻을 전하지 않는다(FR-041). 고른 값의 이름은 가운데에 **글자로**
 * 크게 뜨고, 각 눈금에도 화면낭독기용 전체 문구가 들어 있다.
 * 고정 높이를 쓰지 않는다(FR-040) — 원 크기는 clamp 로 흐른다.
 */
import { computed, ref } from 'vue';

interface Option { value: number | null; label: string }

const props = defineProps<{
  options: Option[];
  modelValue: number | null | undefined;
  ariaLabel: string;
}>();
const emit = defineEmits<{ (e: 'update:modelValue', v: number | null): void }>();

// 부채꼴 범위. 위쪽을 비우면 시계라기보다 계기판으로 읽혀서, 좌우로 200° 를 쓴다.
const SPAN = 200;
const N = computed(() => props.options.length);
const angleOf = (i: number) => (N.value <= 1 ? 0 : -SPAN / 2 + (SPAN / (N.value - 1)) * i);

/* 눈금을 원 둘레에 놓는다 — 여기서 **자리를 %로 직접 계산**한다.
   CSS 로 `rotate() translateY(-40%)` 처럼 짜면 그 40% 가 원의 반지름이 아니라
   눈금 단추 자기 크기(48px)의 40% 라 전부 한가운데로 모인다(실제로 그랬다).
   left/top 의 % 는 부모(원)를 기준으로 하므로 이 방식은 원 크기가 변해도 맞는다.
   R 은 원 반지름(46%)보다 안쪽 — 아래 숫자까지 원 안에 들어오게. */
const R = 37;
const NUM_OUT = 19;   // 숫자를 눈금에서 바깥으로 밀어내는 거리(px)
const posOf = (i: number) => {
  const a = (angleOf(i) * Math.PI) / 180;   // 12시가 0°, 시계방향이 +
  return {
    left: `${50 + R * Math.sin(a)}%`,
    top: `${50 - R * Math.cos(a)}%`,
    // 숫자는 **원 바깥쪽**으로. 아래로 내렸더니 12시 눈금에서 숫자가 바늘에
    // 통째로 묻혔다(화면 보고 찾음). 바늘은 안쪽에서만 도니 바깥은 늘 비어 있다.
    '--nx': `${(NUM_OUT * Math.sin(a)).toFixed(1)}px`,
    '--ny': `${(-NUM_OUT * Math.cos(a)).toFixed(1)}px`,
  };
};

/* 양 끝 라벨(매우 싫어한다 / 매우 좋아한다)을 **눈금 1·5 바로 옆**에 세운다.
   원 아래에 나란히 두었더니 "어느 쪽이 어느 쪽인지"가 눈금과 이어지지 않아
   첫 화면에서 무엇을 하는 자리인지 읽히지 않았다(사용자 지적). 감싸개 높이는
   원 높이와 같으므로, 눈금과 같은 세로 비율을 그대로 쓰면 정확히 나란해진다. */
const endY = computed(() => `${50 - R * Math.cos((SPAN / 2) * Math.PI / 180)}%`);

// 부채꼴 호의 양 끝. 각도를 바꾸면 호도 따라오도록 좌표를 계산해 둔다.
const arcPath = computed(() => {
  const r = R * 2, rad = (d: number) => (d * Math.PI) / 180;
  const p = (d: number) =>
    `${(100 + r * Math.sin(rad(d))).toFixed(1)} ${(100 - r * Math.cos(rad(d))).toFixed(1)}`;
  // SPAN 이 180° 를 넘으므로 large-arc = 1, 왼쪽 끝에서 위를 지나 오른쪽 끝으로 = sweep 1
  return `M ${p(-SPAN / 2)} A ${r} ${r} 0 ${SPAN > 180 ? 1 : 0} 1 ${p(SPAN / 2)}`;
});

const selectedIndex = computed(() =>
  props.options.findIndex((o) => o.value === props.modelValue));

// 아직 고르지 않았으면 바늘을 아예 그리지 않는다 — 12시에 세워 두었더니
// 한가운데 눈금(3번)을 정확히 가리켜 "이미 골랐다"로 읽혔다(화면 보고 찾음).
const handAngle = computed(() =>
  selectedIndex.value >= 0 ? angleOf(selectedIndex.value) : 0);

const centerLabel = computed(() =>
  selectedIndex.value >= 0 ? props.options[selectedIndex.value].label : '');

const dial = ref<HTMLElement | null>(null);
const dragging = ref(false);

function pick(i: number) {
  const o = props.options[i];
  if (!o) return;
  emit('update:modelValue', o.value);
}

/* ── 돌려서 고르기 ────────────────────────────────────────────────────────
   가운데를 기준으로 손가락 각도를 재서 가장 가까운 눈금으로 붙인다.
   부채꼴 밖(아래쪽)으로 나가면 양 끝으로 붙여 값이 튀지 않게 한다. */
function angleFromEvent(e: PointerEvent): number | null {
  const el = dial.value;
  if (!el) return null;
  const r = el.getBoundingClientRect();
  const dx = e.clientX - (r.left + r.width / 2);
  const dy = e.clientY - (r.top + r.height / 2);
  // 12시 방향이 0°, 시계 방향이 +
  return (Math.atan2(dx, -dy) * 180) / Math.PI;
}

function applyAngle(e: PointerEvent) {
  const a = angleFromEvent(e);
  if (a === null || N.value <= 1) return;
  const clamped = Math.max(-SPAN / 2, Math.min(SPAN / 2, a));
  const step = SPAN / (N.value - 1);
  const i = Math.round((clamped + SPAN / 2) / step);
  if (i !== selectedIndex.value) pick(i);
}

function onDown(e: PointerEvent) {
  // 눈금 단추를 직접 누른 경우는 그쪽 click 이 처리한다.
  if ((e.target as HTMLElement).closest('.tick')) return;
  dragging.value = true;
  (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  applyAngle(e);
}
function onMove(e: PointerEvent) { if (dragging.value) applyAngle(e); }
function onUp() { dragging.value = false; }

/* ── 키보드 ───────────────────────────────────────────────────────────────
   role="radio" 는 브라우저가 화살표를 대신 처리해 주지 않는다. 직접 옮긴다. */
function onKey(e: KeyboardEvent) {
  const cur = selectedIndex.value;
  let next = cur;
  switch (e.key) {
    case 'ArrowRight': case 'ArrowUp':   next = cur < 0 ? 0 : Math.min(N.value - 1, cur + 1); break;
    case 'ArrowLeft':  case 'ArrowDown': next = cur < 0 ? N.value - 1 : Math.max(0, cur - 1); break;
    case 'Home': next = 0; break;
    case 'End':  next = N.value - 1; break;
    default: return;
  }
  e.preventDefault();
  pick(next);
  // 옮긴 눈금으로 초점을 따라 보낸다 — 초점이 뒤에 남으면 화면낭독기가 헤맨다.
  const el = dial.value?.querySelectorAll<HTMLElement>('.tick')[next];
  el?.focus();
}

// roving tabindex — 고른 것이 있으면 그것만, 없으면 첫 눈금만 Tab 대상이 된다.
const tabIndexOf = (i: number) =>
  (selectedIndex.value < 0 ? i === 0 : i === selectedIndex.value) ? 0 : -1;
</script>

<template>
  <div class="dialwrap" :style="{ '--end-y': endY }">
    <span class="end end--min" aria-hidden="true">{{ options[0]?.label }}</span>
    <span class="end end--max" aria-hidden="true">{{ options[options.length - 1]?.label }}</span>
    <div
      ref="dial"
      class="dial"
      :class="{ 'is-dragging': dragging }"
      role="radiogroup"
      :aria-label="ariaLabel"
      @pointerdown="onDown"
      @pointermove="onMove"
      @pointerup="onUp"
      @pointercancel="onUp"
      @keydown="onKey"
    >
      <!-- 문자판 -->
      <svg class="dial__face" viewBox="0 0 200 200" aria-hidden="true">
        <circle cx="100" cy="100" r="92" fill="var(--surface-soft)" stroke="var(--hairline)" stroke-width="1.2" />
        <!-- 눈금 사이를 잇는 호. 어디까지 고를 수 있는지 눈으로 알린다. -->
        <path :d="arcPath"
              fill="none" stroke="var(--hairline)" stroke-width="1.6" stroke-linecap="round" />
        <!-- 바늘 — 고른 것이 있을 때만 진하게. -->
        <g v-if="selectedIndex >= 0" :style="{ transform: `rotate(${handAngle}deg)` }" class="dial__hand">
          <line x1="100" y1="100" x2="100" y2="36"
                stroke="var(--primary)" stroke-width="2.6" stroke-linecap="round" />
        </g>
        <circle cx="100" cy="100" :r="selectedIndex >= 0 ? 5.5 : 3.5"
                :fill="selectedIndex >= 0 ? 'var(--primary)' : 'var(--hairline)'" />
      </svg>

      <!-- 눈금 = 선택지. 각각이 진짜 라디오 단추다. -->
      <button
        v-for="(o, i) in options"
        :key="String(o.value)"
        type="button"
        class="tick"
        :class="{ 'tick--on': i === selectedIndex }"
        :style="posOf(i)"
        role="radio"
        :aria-checked="i === selectedIndex"
        :tabindex="tabIndexOf(i)"
        @click="pick(i)"
      >
        <span class="tick__dot" aria-hidden="true"></span>
        <span class="tick__num" aria-hidden="true">{{ i + 1 }}</span>
        <span class="sr">{{ o.label }}</span>
      </button>

      <!-- 가운데 — 고른 값의 이름을 글자로 크게. 색이 아니라 이 글자가
           의미를 전한다(FR-041). -->
      <p class="dial__center" aria-hidden="true">
        <span v-if="centerLabel" class="dial__label">{{ centerLabel }}</span>
        <span v-else class="dial__hint">눈금을 누르거나<br />돌려서 고르세요</span>
      </p>
    </div>

  </div>
</template>

<style scoped>
/* 감싸개는 원과 양 끝 라벨을 함께 담는다. 좌우 여백만큼 원이 줄어든다. */
.dialwrap { position: relative; padding-inline: clamp(54px, 17%, 76px); }
.dial {
  position: relative;
  width: min(100%, 300px);
  aspect-ratio: 1;
  margin: 0 auto;
  touch-action: none;          /* 돌리는 동안 화면이 같이 스크롤되지 않게 */
  cursor: grab;
}
.dial.is-dragging { cursor: grabbing; }
.dial__face { position: absolute; inset: 0; width: 100%; height: 100%; }
.dial__hand { transform-origin: 100px 100px; transition: transform .28s cubic-bezier(.22,.61,.36,1); }

/* 눈금 — 자리(left·top)는 원 기준으로 스크립트가 계산해 넣는다.
   여기 translate 의 -50% 는 눈금 자기 크기 기준이라 그 자리에 중심이 맞는다. */
.tick {
  position: absolute;
  width: 48px; height: 48px;   /* 손가락 표적 최소치 */
  display: grid; place-items: center;
  transform: translate(-50%, -50%);
  background: none; border: 0; padding: 0; cursor: pointer;
  color: var(--muted);
  font: inherit;
}
.tick__dot {
  position: absolute; inset: 0; margin: auto;
  width: 13px; height: 13px; border-radius: 50%;
  background: var(--canvas); border: 2px solid var(--border-strong);
}
.tick__num { position: relative; font-size: 12px; transform: translate(var(--nx, 0px), var(--ny, 0px)); }
.tick:hover .tick__dot { border-color: var(--primary); }

/* 초점 표시 — 48px 표적 전체에 사각 링을 두르면 그 선이 눈금 숫자를 덮어
   가린다(화면 보고 찾음). 링을 **점에만** 둘러 숫자를 살린다. 지우는 게
   아니라 자리를 옮기는 것이다(FR-039). */
.tick:focus-visible { outline: none; }
.tick:focus-visible .tick__dot { outline: 3px solid var(--primary); outline-offset: 3px; }
.tick--on .tick__dot {
  background: var(--primary); border-color: var(--primary);
  box-shadow: 0 0 0 4px var(--tertiary-tint);
}
.tick--on { color: var(--primary-on-tint); font-weight: 700; }

/* 가운데 글자 — 눈금 단추와 겹치지 않게 클릭을 통과시킨다. */
.dial__center {
  position: absolute; left: 50%; top: 68%;
  transform: translate(-50%, -50%);
  width: 62%; margin: 0; text-align: center; pointer-events: none;
}
.dial__label {
  font-size: clamp(17px, 4.6vw, 22px); font-weight: 700; line-height: 1.3;
  color: var(--ink); word-break: keep-all;
}
.dial__hint { font-size: 13px; line-height: 1.5; color: var(--muted); }

/* 양 끝 라벨 — 눈금 1·5 와 같은 높이(--end-y)에서 원 바깥에 붙는다.
   감싸개 높이 = 원 높이라 이 비율이 곧 눈금의 세로 자리다. */
.end {
  position: absolute; top: var(--end-y, 50%); transform: translateY(-50%);
  width: clamp(50px, 16%, 72px);
  font-size: 13px; line-height: 1.35; color: var(--muted);
  word-break: keep-all;
}
.end--min { left: 0; text-align: right; }
.end--max { right: 0; text-align: left; }

/* 화면낭독기 전용 — 눈에는 안 보이지만 읽힌다. display:none 은 읽히지 않는다. */
.sr {
  position: absolute; width: 1px; height: 1px; overflow: hidden;
  clip: rect(0 0 0 0); clip-path: inset(50%); white-space: nowrap;
}

@media (prefers-reduced-motion: reduce) {
  .dial__hand { transition: none; }
}
</style>
