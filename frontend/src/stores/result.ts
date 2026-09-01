import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useResultStore = defineStore('result', () => {
  const result = ref<any>(null);
  const selfReportLevel = ref<number | null>(null);
  const consent = ref<boolean | null>(null);
  function set(r: any) { result.value = r; }
  function clear() { result.value = null; selfReportLevel.value = null; consent.value = null; }
  return { result, selfReportLevel, consent, set, clear };
});
