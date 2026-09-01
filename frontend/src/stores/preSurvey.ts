// 사전 입력 (FR-002a~h)
//   별명 : sessionStorage — 탭을 닫으면 사라진다. 재접속 시 복구하지 않는 것이
//          의도된 동작이며 개인정보 최소화를 우선한 결정이다(FR-002d, 검토 6번).
//   연령 : 메모리만. 보관하지 않는다(FR-002e).
import { defineStore } from 'pinia';
import { ref } from 'vue';

const NICK_KEY = 'cb.nickname';

export const usePreSurveyStore = defineStore('preSurvey', () => {
  const nickname = ref<string>(sessionStorage.getItem(NICK_KEY) ?? '');
  const careTargetAge = ref<number | null>(null);       // 메모리 전용
  const multipleCareTargets = ref<boolean | null>(null);

  function setNickname(v: string) {
    nickname.value = v.slice(0, 20);
    try {
      if (nickname.value) sessionStorage.setItem(NICK_KEY, nickname.value);
      else sessionStorage.removeItem(NICK_KEY);
    } catch { /* 저장소를 못 써도 진단은 계속된다 */ }
  }

  function displayName() {
    return nickname.value.trim() || '보호자';
  }

  function reset() {
    nickname.value = ''; careTargetAge.value = null; multipleCareTargets.value = null;
    try { sessionStorage.removeItem(NICK_KEY); } catch { /* noop */ }
  }

  return { nickname, careTargetAge, multipleCareTargets, setNickname, displayName, reset };
});
