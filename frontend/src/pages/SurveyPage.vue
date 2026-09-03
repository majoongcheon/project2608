<script setup lang="ts">
// 진단 설문 (FR-004d·FR-005·FR-006·FR-007·FR-011b)
//   진행률 표시 · 이전 문항 이동 · "해당사항 없음" 선택지.
//   설문 도중에는 어떤 중간 결과도 보여주지 않는다.
import { computed, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useSurveyStore } from '../stores/survey';
import { useEventStore } from '../stores/events';
import ScaleDial from '../components/ScaleDial.vue';

const router = useRouter();
const s = useSurveyStore();
const events = useEventStore();

onMounted(async () => { await s.load(); events.track('SURVEY_START'); });

/* ── 원형 다이얼을 쓸 문항 고르기 ───────────────────────────────────────
   시계 문자판은 **순서**를 뜻한다. 1~5 처럼 한 방향으로 세지는 척도에만 맞다.
   실측(2026-09-03): 7문항 중 1·2·3 만 5단계 척도이고, 4번(생계 책임자 8지)
   5번(퇴사 사유 15지 + 해당사항 없음) 6번(관계)은 **순서가 없는 항목**이다.
   여기에 다이얼을 쓰면 "아버지가 형제자매보다 낮은 값"처럼 읽힌다 — 쓰지 않는다.

   문항 데이터에 척도 여부 표시가 없어 형태로 가른다: 선택지가 정확히 5개이고
   값이 1..5 로 연속이며 빈 값이 없을 것. (문항 집합에 `scale` 표시를 넣는 것이
   본래 맞고, 그러면 이 추정은 지울 수 있다.) */
function isScale(q: any): boolean {
  const o = q?.options;
  if (!Array.isArray(o) || o.length !== 5) return false;
  return o.every((x: any, i: number) => x?.value === i + 1);
}
// 보기 전환. 원형이 불편한 사람에게 원형만 남기지 않는다 — 고른 값은 기억한다.
const MODE_KEY = 'cb.answerMode';
const mode = ref<'dial' | 'list'>('dial');
try { if (localStorage.getItem(MODE_KEY) === 'list') mode.value = 'list'; } catch { /* noop */ }
watch(mode, (m) => { try { localStorage.setItem(MODE_KEY, m); } catch { /* noop */ } });

const useDial = computed(() => mode.value === 'dial' && !!s.current && isScale(s.current));

const pct = computed(() => (s.total ? Math.round(((s.index + 1) / s.total) * 100) : 0));
const value = computed(() => (s.current ? s.answers[s.current.questionNo] : undefined));
const isLast = computed(() => s.index === s.total - 1);
const answered = computed(() => s.current !== null && s.current.questionNo in s.answers);

function choose(v: number | null) {
  if (!s.current) return;
  s.answer(s.current.questionNo, v);
  events.track('QUESTION_MOVE', { questionNo: s.current.questionNo });
  // 목록에서 한 번 누르는 것은 확정이라 바로 넘긴다. 다이얼은 돌리는 동안
  // 값이 계속 바뀌므로 넘기면 안 된다 — 지나가는 값에서 화면이 튄다.
  if (!isLast.value && !useDial.value) setTimeout(() => s.next(), 160);
}

function onNumber(e: Event) {
  const raw = (e.target as HTMLInputElement).value;
  if (!s.current) return;
  s.answer(s.current.questionNo, raw === '' ? null : Number(raw));
}

function finish() {
  if (s.unanswered.length) { s.go(s.questions.findIndex((q) => q.questionNo === s.unanswered[0])); return; }
  events.track('SURVEY_COMPLETE');
  router.push('/diagnosis/consent');
}

function restart() { s.clearDraft(); router.push('/diagnosis/start'); }
</script>

<template>
  <div class="container stack">
    <!-- 실패를 먼저 본다. 그러지 않으면 "불러오는 중" 에서 영영 멈춘다. -->
    <div v-if="s.loadError" class="card stack" role="alert">
      <h2>문항을 불러오지 못했습니다</h2>
      <p class="notice">
        잠시 후 다시 시도해 주세요. 계속 같은 화면이 나오면 잠시 뒤에 다시 들어와 주세요.
      </p>
      <div class="nav">
        <button class="btn" type="button" @click="s.retry()">다시 시도</button>
        <button class="btn btn--ghost" type="button" @click="router.push('/')">처음 화면으로</button>
      </div>
    </div>

    <div v-else-if="!s.loaded" class="card">문항을 불러오는 중입니다…</div>

    <template v-else-if="s.current">
      <!-- FR-005 진행률 -->
      <div class="progress">
        <div class="progress__bar" role="progressbar" :aria-valuenow="s.index + 1" aria-valuemin="1"
             :aria-valuemax="s.total" :aria-label="`전체 ${s.total}문항 중 ${s.index + 1}번째`">
          <span :style="{ width: pct + '%' }"></span>
        </div>
        <p class="progress__text">{{ s.index + 1 }} / {{ s.total }} 문항</p>
      </div>

      <p v-if="s.restored" class="notice">
        이전에 진행하시던 응답을 이어서 표시했습니다.
        <button class="linklike" type="button" @click="restart">처음부터 새로 시작</button>
      </p>

      <div class="card stack">
        <h2 class="q">{{ s.current.text }}</h2>

        <div v-if="s.current.inputType === 'number'" class="numwrap">
          <input type="number" :min="s.current.min ?? 0" :max="s.current.max ?? 200"
                 inputmode="numeric" :value="value ?? ''" @input="onNumber"
                 :ariaLabel="s.current.text" />
          <span class="unit">{{ s.current.unit }}</span>
        </div>

        <ScaleDial
          v-else-if="useDial"
          :options="s.current.options"
          :model-value="value"
          :ariaLabel="s.current.text"
          @update:model-value="choose"
        />

        <div v-else class="options" role="radiogroup" :aria-label="s.current.text">
          <button v-for="o in s.current.options" :key="String(o.value)" type="button"
                  class="option" :class="{ 'option--on': value === o.value }"
                  role="radio" :aria-checked="value === o.value" @click="choose(o.value)">
            <span class="option__mark" aria-hidden="true"></span>
            <span>{{ o.label }}</span>
          </button>
        </div>

        <!-- 원형이 불편하면 목록으로. 척도 문항에서만 뜻이 있는 단추다. -->
        <p v-if="s.current.inputType !== 'number' && isScale(s.current)" class="modeline">
          <button class="linklike" type="button"
                  @click="mode = mode === 'dial' ? 'list' : 'dial'">
            {{ mode === 'dial' ? '목록으로 고르기' : '문자판으로 고르기' }}
          </button>
        </p>
      </div>

      <div class="nav">
        <button class="btn btn--ghost" type="button" :disabled="s.index === 0" @click="s.prev()">이전</button>
        <button v-if="!isLast" class="btn btn--secondary" type="button" :disabled="!answered" @click="s.next()">다음</button>
        <button v-else class="btn" type="button" :disabled="s.unanswered.length > 0" @click="finish">응답 마치기</button>
      </div>

      <p v-if="isLast && s.unanswered.length" class="warn">
        아직 응답하지 않은 문항이 {{ s.unanswered.length }}개 있습니다.
        <button class="linklike" type="button" @click="s.go(s.questions.findIndex((q:any) => q.questionNo === s.unanswered[0]))">
          {{ s.unanswered[0] }}번 문항으로 이동
        </button>
      </p>
    </template>

    <!-- loaded 인데 current 가 없는 경우. 여기가 비어 있어서 빈 화면이 나왔다. -->
    <div v-else class="card stack" role="alert">
      <h2>진단을 이어갈 수 없습니다</h2>
      <p class="notice">표시할 문항을 찾지 못했습니다. 처음부터 다시 시작해 주세요.</p>
      <div class="nav">
        <button class="btn" type="button" @click="restart">처음부터 새로 시작</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.progress__bar { height: 8px; background: var(--surface-strong); border-radius: var(--radius-pill); overflow: hidden; }
.progress__bar span { display: block; height: 100%; background: var(--primary); transition: width .25s; }
.progress__text { font-size: 14px; color: var(--muted); margin: var(--sp-xs) 0 0; }
.q { font-size: 20px; line-height: 1.4; }
.options { display: grid; gap: var(--sp-sm); }
.option {
  display: flex; align-items: center; gap: var(--sp-md); width: 100%; text-align: left;
  padding: 14px var(--sp-base); min-height: 52px; font: inherit; cursor: pointer;
  border: 1px solid var(--hairline); border-radius: var(--radius-md); background: var(--canvas); color: var(--body);
}
.option:hover { border-color: var(--border-strong); background: var(--surface-soft); }
.option--on { border-color: var(--ink); border-width: 2px; background: var(--surface-strong); font-weight: 600; color: var(--ink); }
.option__mark { width: 20px; height: 20px; border-radius: 50%; border: 2px solid var(--border-strong); flex: none; }
.option--on .option__mark { border-color: var(--ink); background: var(--ink); box-shadow: inset 0 0 0 4px var(--canvas); }
.numwrap { display: flex; align-items: center; gap: var(--sp-sm); }
.numwrap input { flex: 1; padding: 12px var(--sp-md); font: inherit; border: 1px solid var(--border-strong); border-radius: var(--radius-sm); }
.nav { display: flex; gap: var(--sp-sm); }
.nav .btn { flex: 1; }
.notice, .warn { font-size: 14px; padding: var(--sp-md); border-radius: var(--radius-sm); margin: 0; }
.notice { background: var(--surface-soft); color: var(--muted); }
.warn { background: #fff4f1; color: var(--error-text); border: 1px solid #f4c7bd; }
.modeline { margin: var(--sp-sm) 0 0; text-align: right; font-size: 13px; }
.linklike { background: none; border: 0; padding: 0; color: var(--link); text-decoration: underline; cursor: pointer; font: inherit; }
</style>
