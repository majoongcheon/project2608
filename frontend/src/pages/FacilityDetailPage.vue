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

// 이 기관에 대한 후기 — 쓰는 것은 소통방(/reviews)에서 한다. 여기서는 읽기만.
const reviews = ref<any[]>([]);
const reviewStat = ref<{ count: number; averageRating: number | null } | null>(null);

onMounted(async () => {
  try {
    f.value = await api.facility(Number(route.params.id));
    events.track('FACILITY_DETAIL');
  } catch { error.value = '기관 정보를 불러오지 못했습니다.'; }
  // 후기는 없어도 화면이 성립하므로 따로 감싼다 — 이것 때문에 기관 정보가
  // 안 보이는 일이 없게 한다.
  try {
    const d = await api.facilityReviews(Number(route.params.id));
    reviews.value = d.reviews;
    reviewStat.value = { count: d.count, averageRating: d.averageRating };
  } catch { /* 후기 없이 계속 */ }
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

      <!-- 다녀오신 분들의 이야기 (2026-09-03) -->
      <section class="card stack">
        <h2>다녀오신 분들의 이야기</h2>
        <p v-if="reviewStat?.count" class="muted">
          후기 {{ reviewStat.count }}개 · 평균 {{ reviewStat.averageRating }}점
          <span v-if="reviewStat.count < 3">— 아직 후기가 적어 평균은 참고만 해 주세요</span>
        </p>

        <ul v-if="reviews.length" class="rv">
          <li v-for="r in reviews" :key="r.reviewId" class="rv__li">
            <p class="rv__meta">
              <span class="rv__star" aria-hidden="true">{{ '★'.repeat(r.rating) }}{{ '☆'.repeat(5 - r.rating) }}</span>
              <span class="sr">{{ r.rating }}점</span>
              <b>{{ r.nickname }}</b>
            </p>
            <p class="rv__body">{{ r.body }}</p>
          </li>
        </ul>
        <p v-else class="muted">아직 이 기관의 후기가 없습니다. 첫 이야기를 남겨 주시면 다음 분께 큰 도움이 됩니다.</p>

        <RouterLink class="btn btn--secondary" to="/reviews">소통방에서 후기 남기기</RouterLink>
      </section>

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
          <!-- 자리표시글은 라벨이 아니다 — 글을 적기 시작하면 사라지고,
               화면낭독기가 읽어 주지 않는 브라우저도 있다. -->
          <label class="sel">
            <span>자세한 내용 (선택)</span>
            <textarea v-model="reportDetail" rows="3" maxlength="500"
                      placeholder="어떤 점이 다른지 적어 주세요"></textarea>
          </label>
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
.rv { list-style: none; margin: 0; padding: 0; }
.rv__li { border-top: 1px solid var(--hairline-soft); padding-block: var(--sp-md); }
.rv__li:first-child { border-top: 0; padding-top: 0; }
.rv__meta { display: flex; gap: 10px; align-items: baseline; margin: 0 0 4px; font-size: 14px; }
.rv__star { color: var(--primary); letter-spacing: 1px; }
.rv__body { margin: 0; line-height: 1.65; white-space: pre-line; }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
.btn { text-decoration: none; }
.notice { background: var(--surface-soft); color: var(--muted); font-size: 14px;
  padding: var(--sp-md); border-radius: var(--radius-sm); margin: 0; }
</style>
