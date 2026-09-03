<script setup lang="ts">
// 학습 이용 동의 → 자가보고 부담 문항 (FR-033 → FR-008a·c·d·e)
//   ★ 동의 고지가 자가보고 문항보다 앞에 온다. 동의하지 않으면 문항을 제시하지 않는다.
//   ★ 동의하지 않아도 진단·결과·연계 안내는 모두 그대로 제공된다.
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import RoomHead from '../components/RoomHead.vue';
import { useSurveyStore } from '../stores/survey';
import { usePreSurveyStore } from '../stores/preSurvey';
import { useResultStore } from '../stores/result';
import { useEventStore } from '../stores/events';
import { api } from '../services/apiClient';

const router = useRouter();
const s = useSurveyStore();
const pre = usePreSurveyStore();
const result = useResultStore();
const events = useEventStore();

const consent = ref<boolean | null>(null);
const selfReport = ref<number | null>(null);
const submitting = ref(false);
const error = ref('');

const canSubmit = computed(() =>
  consent.value === false || (consent.value === true && selfReport.value !== null));

async function submit() {
  submitting.value = true; error.value = '';
  try {
    const coords = await getCoords();
    const body = {
      questionSetVersion: s.version,
      answers: s.payloadAnswers(),
      selfReportLevel: consent.value ? selfReport.value : null,
      consentTraining: consent.value === true,
      careTargetAge: pre.careTargetAge,
      multipleCareTargets: pre.multipleCareTargets,
      surveyDurationSec: Math.round((Date.now() - s.startedAt) / 1000),
      location: coords,
    };
    const r = await api.diagnose(body);
    result.set(r);
    result.consent = consent.value;
    events.track('RESULT_SHOWN', {
      modelVersion: r.modelVersion, durationMs: r.durationMs,
      isUndecidable: !r.decided, consentTraining: consent.value,
    });
    s.clearDraft();                       // FR-008-2 — 제출 완료 시 임시 저장 폐기
    router.push('/diagnosis/result');
  } catch (e: any) {
    error.value = e?.message ?? '결과를 계산하지 못했습니다. 잠시 후 다시 시도해 주세요.';
  } finally {
    submitting.value = false;
  }
}

/** 위치는 즉시 안내에만 쓰고 보관하지 않는다(FR-026). 거부해도 진행된다(FR-021d). */
function getCoords(): Promise<{ lat?: number; lng?: number }> {
  return new Promise((resolve) => {
    if (!navigator.geolocation) return resolve({});
    const t = setTimeout(() => resolve({}), 4000);
    navigator.geolocation.getCurrentPosition(
      (p) => { clearTimeout(t); resolve({ lat: p.coords.latitude, lng: p.coords.longitude }); },
      () => { clearTimeout(t); resolve({}); },
      { timeout: 4000, maximumAge: 60000 });
  });
}
</script>

<template>
  <div class="container room stack">
    <RoomHead
      no="01"
      eyebrow="부담감 진단"
      title="거의 다 왔습니다"
    />

    <div class="card stack">
      <h2>응답을 진단 정확도 개선에 사용해도 될까요?</h2>
      <p class="hint">
        보내주신 응답은 진단 모델의 <strong>학습과 검증</strong>에만 쓰입니다.
        이름·연락처·별명·위치는 저장하지 않으며, 개인을 알아볼 수 있는 형태로 남지 않습니다.
      </p>
      <p class="hint"><strong>동의하지 않으셔도 진단 결과와 기관 안내는 똑같이 받아 보실 수 있습니다.</strong></p>

      <div class="row">
        <label class="choice"><input type="radio" :value="true" v-model="consent" /> 동의합니다</label>
        <label class="choice"><input type="radio" :value="false" v-model="consent" /> 동의하지 않습니다</label>
      </div>
    </div>

    <!-- FR-008e — 동의한 경우에만 자가보고 문항을 제시한다 -->
    <div v-if="consent === true && s.selfReport" class="card stack">
      <h2>{{ s.selfReport.text }}</h2>
      <!-- FR-008d — 왜 묻는지 밝힌다 -->
      <p class="notice">{{ s.selfReport.notice }}</p>
      <div class="options" role="radiogroup" :aria-label="s.selfReport.text">
        <button v-for="o in s.selfReport.options" :key="o.value" type="button"
                class="option" :class="{ 'option--on': selfReport === o.value }"
                role="radio" :aria-checked="selfReport === o.value" @click="selfReport = o.value">
          <span class="option__mark" aria-hidden="true"></span><span>{{ o.label }}</span>
        </button>
      </div>
    </div>

    <p v-if="consent === false" class="notice">
      알겠습니다. 응답은 저장하지 않고 결과 계산에만 사용한 뒤 폐기합니다.
    </p>

    <p v-if="error" class="warn">{{ error }}</p>

    <button class="btn btn--block" type="button" :disabled="!canSubmit || submitting" @click="submit">
      {{ submitting ? '결과를 계산하고 있습니다…' : '결과 보기' }}
    </button>
    <p v-if="submitting" class="hint">잠시만 기다려 주세요.</p>
  </div>
</template>

<style scoped>
.hint { font-size: 14px; color: var(--muted); margin: 0; }
.choice { display: inline-flex; align-items: center; gap: var(--sp-sm); padding: 12px var(--sp-base);
  border: 1px solid var(--hairline); border-radius: var(--radius-pill); cursor: pointer; min-height: 48px; }
.choice:has(input:checked) { border-color: var(--ink); background: var(--surface-strong); font-weight: 600; }
.options { display: grid; gap: var(--sp-sm); }
.option { display: flex; align-items: center; gap: var(--sp-md); width: 100%; text-align: left;
  padding: 14px var(--sp-base); min-height: 52px; font: inherit; cursor: pointer;
  border: 1px solid var(--hairline); border-radius: var(--radius-md); background: var(--canvas); color: var(--body); }
.option--on { border-color: var(--ink); border-width: 2px; background: var(--surface-strong); font-weight: 600; color: var(--ink); }
.option__mark { width: 20px; height: 20px; border-radius: 50%; border: 2px solid var(--border-strong); flex: none; }
.option--on .option__mark { border-color: var(--ink); background: var(--ink); box-shadow: inset 0 0 0 4px var(--canvas); }
.notice { background: var(--surface-soft); color: var(--muted); font-size: 14px; padding: var(--sp-md); border-radius: var(--radius-sm); margin: 0; }
.warn { background: #fff4f1; color: var(--error-text); border: 1px solid #f4c7bd; padding: var(--sp-md); border-radius: var(--radius-sm); font-size: 14px; }
</style>
