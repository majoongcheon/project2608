<script setup lang="ts">
// 기관 상세 (FR-017·FR-018·FR-019·FR-019b)
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { api } from '../services/apiClient';
import { useEventStore } from '../stores/events';
import FacilityCard from '../components/FacilityCard.vue';

const route = useRoute();
const events = useEventStore();
const f = ref<any>(null);
const reportType = ref('');
const reportDetail = ref('');
const reported = ref(false);
const error = ref('');

onMounted(async () => {
  try {
    f.value = await api.facility(Number(route.params.id));
    events.track('FACILITY_DETAIL');
  } catch { error.value = '기관 정보를 불러오지 못했습니다.'; }
});

async function submitReport() {
  if (!reportType.value) return;
  try {
    await api.report(Number(route.params.id), { reportType: reportType.value, detail: reportDetail.value });
    reported.value = true;
  } catch { error.value = '신고를 접수하지 못했습니다. 잠시 후 다시 시도해 주세요.'; }
}
</script>

<template>
  <div class="container stack">
    <p v-if="error" class="notice">{{ error }}</p>
    <template v-if="f">
      <h1>{{ f.name }}</h1>
      <FacilityCard :facility="f" />

      <p class="muted">최종 갱신일: {{ f.updatedAt ?? '정보 없음' }}</p>

      <section class="card stack">
        <h2>정보가 잘못되었나요?</h2>
        <p class="muted">확인 후 수정하겠습니다. 연락처는 받지 않으니 개인 정보는 적지 말아 주세요.</p>
        <template v-if="!reported">
          <label class="sel">
            <span>어떤 정보가 잘못되었나요?</span>
            <select v-model="reportType">
              <option value="">선택하세요</option>
              <option value="PHONE">전화번호가 다름</option>
              <option value="ADDRESS">주소가 다름</option>
              <option value="CLOSED">운영하지 않음</option>
              <option value="SERVICE">제공 서비스가 다름</option>
              <option value="OTHER">기타</option>
            </select>
          </label>
          <textarea v-model="reportDetail" rows="3" maxlength="500"
                    placeholder="자세한 내용을 적어 주세요 (선택)"></textarea>
          <button class="btn" type="button" :disabled="!reportType" @click="submitReport">신고하기</button>
        </template>
        <p v-else class="notice">신고가 접수되었습니다. 확인 후 반영하겠습니다.</p>
      </section>
    </template>
  </div>
</template>

<style scoped>
.sel span { display: block; font-size: 14px; font-weight: 600; color: var(--ink); margin-bottom: var(--sp-xs); }
select, textarea { width: 100%; padding: 12px var(--sp-md); font: inherit;
  border: 1px solid var(--border-strong); border-radius: var(--radius-sm); background: var(--canvas); }
select { min-height: 48px; }
.notice { background: var(--surface-soft); color: var(--muted); font-size: 14px;
  padding: var(--sp-md); border-radius: var(--radius-sm); margin: 0; }
</style>
