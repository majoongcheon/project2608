<script setup lang="ts">
// 사전 입력 (FR-002a~h) — 세 항목 모두 선택 입력이며 건너뛸 수 있다.
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { usePreSurveyStore } from '../stores/preSurvey';
import { useSurveyStore } from '../stores/survey';
import { useEventStore } from '../stores/events';

const router = useRouter();
const pre = usePreSurveyStore();
const survey = useSurveyStore();
const events = useEventStore();
// type="number" 인 입력에 붙은 v-model 은 값을 number 로 캐스팅해 넣는다(Vue 의 기본 동작).
// 비워 두면 문자열 '' 이 그대로 남아, 한 변수에 두 타입이 섞인다. 문자열로 단정하지 않는다.
const ageText = ref<string | number>(pre.careTargetAge ?? '');

onMounted(() => { void survey.load(); });

function proceed() {
  const raw = String(ageText.value).trim();
  const n = Number(raw);
  pre.careTargetAge = raw === '' || Number.isNaN(n) ? null : n;
  events.track('PRESURVEY_PASS');
  router.push('/diagnosis/survey');
}
</script>

<template>
  <div class="container stack">
    <h1>시작하기 전에</h1>
    <p class="muted">
      아래 세 가지는 <strong>모두 선택 사항</strong>입니다. 입력하지 않으셔도 진단은 그대로 진행됩니다.
    </p>

    <div class="card stack">
      <div>
        <label for="nick"><strong>1. 어떻게 불러 드릴까요?</strong> <span class="opt">선택</span></label>
        <p class="hint">결과 화면의 호칭에만 씁니다. 서버로 보내지 않고 저장하지도 않습니다.
          <strong>실명·연락처 등은 적지 말아 주세요.</strong></p>
        <input id="nick" type="text" maxlength="20" :value="pre.nickname"
               placeholder="예: 햇살맘" @input="pre.setNickname(($event.target as HTMLInputElement).value)" />
      </div>

      <div>
        <label for="age"><strong>2. 돌보고 계신 발달장애인 당사자의 만 나이</strong> <span class="opt">선택</span></label>
        <!-- FR-002e-1·e-2 — 보호자 본인이 아니라 당사자, 그리고 만 나이임을 분명히 한다 -->
        <p class="hint">보호자 본인이 아니라 <strong>돌봄을 받는 당사자</strong>의 나이입니다.
          <strong>만 나이</strong> 기준으로 적어 주세요. 연령에 맞는 서비스를 안내하는 데만 쓰고 저장하지 않습니다.</p>
        <input id="age" v-model="ageText" type="number" inputmode="numeric" min="0" max="120" placeholder="예: 22" />
      </div>

      <div>
        <fieldset>
          <legend><strong>3. 현재 돌보고 계신 발달장애인은 몇 분인가요?</strong> <span class="opt">선택</span></legend>
          <div class="row">
            <label class="choice"><input type="radio" :value="false" v-model="pre.multipleCareTargets" /> 1인</label>
            <label class="choice"><input type="radio" :value="true" v-model="pre.multipleCareTargets" /> 2인 이상</label>
          </div>
          <p v-if="pre.multipleCareTargets" class="hint">
            2인 이상이시군요. 진단은 <strong>한 분을 기준</strong>으로 답해 주세요. 어느 분을 기준으로 할지 정하신 뒤 진행하시면 됩니다.
          </p>
        </fieldset>
      </div>
    </div>

    <div class="row">
      <button class="btn" type="button" @click="proceed">진단 시작하기</button>
      <button class="btn btn--ghost" type="button" @click="proceed">건너뛰고 바로 시작</button>
    </div>
  </div>
</template>

<style scoped>
label, legend { display: block; margin-bottom: var(--sp-xs); color: var(--ink); }
.opt { color: var(--muted-soft); font-size: 13px; font-weight: 400; }
.hint { font-size: 14px; color: var(--muted); margin: 0 0 var(--sp-sm); }
input[type='text'], input[type='number'] {
  width: 100%; padding: 12px var(--sp-md); font: inherit;
  border: 1px solid var(--border-strong); border-radius: var(--radius-sm); background: var(--canvas);
}
fieldset { border: 0; padding: 0; margin: 0; }
.choice {
  display: inline-flex; align-items: center; gap: var(--sp-sm); padding: 10px var(--sp-base);
  border: 1px solid var(--hairline); border-radius: var(--radius-pill); cursor: pointer; min-height: 44px;
}
.choice:has(input:checked) { border-color: var(--ink); background: var(--surface-strong); }
</style>
