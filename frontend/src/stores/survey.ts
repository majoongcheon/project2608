// 설문 진행 상태 (FR-008·FR-008-1·FR-008-2)
//   ★ localStorage 에만 임시 저장하고 서버로 보내지 않는다.
//   ★ 제출 완료 · "새로 시작" · 24시간 경과 중 하나면 즉시 폐기한다.
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { api } from '../services/apiClient';

const KEY = 'cb.draft';
const DEFAULT_EXPIRY_HOURS = 24;

interface Draft { answers: Record<number, number | null>; index: number; savedAt: number; version: string }

function loadDraft(version: string, expiryHours: number): Draft | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const d = JSON.parse(raw) as Draft;
    if (d.version !== version) return null;                       // 문항 집합이 바뀌면 버린다
    if (Date.now() - d.savedAt > expiryHours * 3600_000) { localStorage.removeItem(KEY); return null; }
    return d;
  } catch { return null; }
}

export const useSurveyStore = defineStore('survey', () => {
  const questions = ref<any[]>([]);
  const selfReport = ref<any>(null);
  const version = ref('');
  const expiryHours = ref(DEFAULT_EXPIRY_HOURS);
  const answers = ref<Record<number, number | null>>({});
  const index = ref(0);
  const startedAt = ref<number>(Date.now());
  const loaded = ref(false);
  const restored = ref(false);
  // 문항을 못 받았을 때의 사유. 화면이 "불러오는 중" 에서 멈추지 않게 한다.
  const loadError = ref<string | null>(null);

  const total = computed(() => questions.value.length);
  const current = computed(() => questions.value[index.value] ?? null);
  const answeredCount = computed(() =>
    questions.value.filter((q) => q.questionNo in answers.value).length);
  const unanswered = computed(() =>
    questions.value.filter((q) => !(q.questionNo in answers.value)).map((q) => q.questionNo));

  async function load() {
    if (loaded.value) return;
    loadError.value = null;
    try {
      const [q, cfg] = await Promise.all([api.questions(), api.config().catch(() => null)]);
      // 응답에 questions 가 없으면 total·current 계산이 그대로 터진다. 빈 배열로 받는다.
      questions.value = Array.isArray(q?.questions) ? q.questions : [];
      selfReport.value = q?.selfReportQuestion ?? null;
      version.value = q?.version ?? '';
      if (cfg?.draftExpiryHours) expiryHours.value = cfg.draftExpiryHours;

      if (!questions.value.length) {
        // 200 을 받았어도 문항이 없으면 설문을 시작할 수 없다. 빈 화면 대신 사유를 남긴다.
        loadError.value = '문항을 불러오지 못했습니다.';
        return;
      }

      const d = loadDraft(version.value, expiryHours.value);
      if (d) {
        answers.value = d.answers;
        // 문항 수가 줄면 저장된 위치가 범위를 벗어난다. 음수가 되지 않게 함께 막는다.
        index.value = Math.max(0, Math.min(d.index, questions.value.length - 1));
        restored.value = true;
      } else {
        index.value = Math.max(0, Math.min(index.value, questions.value.length - 1));
      }
      loaded.value = true;
    } catch (e: any) {
      // loaded 를 세우지 않는다. 다시 부르면 재시도된다.
      loadError.value = e?.message ?? '문항을 불러오지 못했습니다.';
    }
  }

  /** 실패 후 다시 시도한다. */
  async function retry() { loadError.value = null; await load(); }

  function persist() {
    try {
      localStorage.setItem(KEY, JSON.stringify({
        answers: answers.value, index: index.value, savedAt: Date.now(), version: version.value,
      } satisfies Draft));
    } catch { /* 저장소를 못 써도 진행은 계속된다 */ }
  }

  function answer(questionNo: number, value: number | null) {
    answers.value = { ...answers.value, [questionNo]: value };
    persist();
  }

  function go(i: number) { index.value = Math.max(0, Math.min(i, total.value - 1)); persist(); }
  function next() { go(index.value + 1); }
  function prev() { go(index.value - 1); }

  /** 제출 완료 · 새로 시작 시 즉시 폐기 (FR-008-2) */
  function clearDraft() {
    answers.value = {}; index.value = 0; restored.value = false; startedAt.value = Date.now();
    try { localStorage.removeItem(KEY); } catch { /* noop */ }
  }

  function payloadAnswers() {
    return questions.value.map((q) => ({
      questionNo: q.questionNo,
      value: answers.value[q.questionNo] ?? null,
    }));
  }

  return { questions, selfReport, version, answers, index, total, current, answeredCount,
           unanswered, loaded, restored, expiryHours, startedAt,
           loadError,
           load, retry, answer, go, next, prev, clearDraft, payloadAnswers };
});
