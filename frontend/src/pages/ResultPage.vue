<script setup lang="ts">
// 진단 결과 (FR-009a·FR-010~FR-014·FR-021~FR-021j-1·FR-025)
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useResultStore } from '../stores/result';
import { usePreSurveyStore } from '../stores/preSurvey';
import { useEventStore } from '../stores/events';
import { api } from '../services/apiClient';
import BurdenResultCard from '../components/BurdenResultCard.vue';
import ContributionList from '../components/ContributionList.vue';
import ReferenceComparison from '../components/ReferenceComparison.vue';
import FacilityCard from '../components/FacilityCard.vue';

const router = useRouter();
const store = useResultStore();
const pre = usePreSurveyStore();
const events = useEventStore();
const cancelled = ref(false);

const r = computed(() => store.result);
const referral = computed(() => r.value?.immediateReferral ?? null);

onMounted(() => { if (!store.result) router.replace('/diagnosis/start'); });

async function cancelStorage() {
  if (!r.value?.cancelToken) return;
  try { await api.cancel(r.value.cancelToken); cancelled.value = true; } catch { /* noop */ }
}
function restart() { store.clear(); pre.reset(); events.renew(); router.push('/'); }
</script>

<template>
  <div v-if="r" class="container stack">
    <!-- 판정된 경우 -->
    <BurdenResultCard v-if="r.decided" :label="r.burdenLabel" :description="r.burdenDescription"
                      :is-warning="r.isWarning" :name="pre.displayName()" />

    <!-- 판정 불가 (FR-009a·FR-021j-1) — 부담 구간을 표시하지 않는다 -->
    <section v-else class="undecided" aria-label="판정 결과 안내">
      <p class="undecided__who">{{ pre.displayName() }}님께 드리는 안내</p>
      <p class="undecided__title">돌봄부담 수준을 판단하기 어렵습니다</p>
      <p class="undecided__body">{{ r.undecidableNotice }}</p>
    </section>

    <!-- FR-010d — 2인 이상 과소 추정 안내. 판정 자체와 구분되는 위치에 둔다 -->
    <p v-if="r.multipleTargetsNotice" class="adjust">{{ r.multipleTargetsNotice }}</p>

    <!-- FR-011c — 판정 불가면 기여 요인을 제시하지 않는다 -->
    <ContributionList v-if="r.contributions?.length" :items="r.contributions" />

    <!-- FR-013d — 판정 불가면 비교를 제공하지 않는다. 항목이 없으면 영역 자체를 숨긴다 -->
    <ReferenceComparison v-if="r.comparison?.length" :items="r.comparison" />

    <!-- FR-021 즉시 안내 -->
    <section v-if="referral" class="stack">
      <h2>가까운 신청 접수처</h2>

      <p v-if="referral.emphasizeCounseling" class="counsel">
        <strong>혼자 감당하지 않으셔도 됩니다.</strong>
        아래 기관에 연락하시면 상담과 서비스 신청을 함께 안내받으실 수 있습니다.
      </p>

      <!-- FR-021i-1 — 대상 범위를 벗어나도 기관은 그대로 보여준다 -->
      <div v-if="referral.ageOutOfRange" class="outrange">
        <p>{{ referral.ageOutOfRange.notice }}</p>
        <p><strong>{{ referral.ageOutOfRange.alternativeContact }}</strong></p>
        <p class="muted">아래 기관은 참고용으로 함께 보여 드립니다. 이용 가능 여부는 기관에 확인해 주세요.</p>
      </div>

      <p v-if="referral.emptyReason" class="notice">{{ referral.emptyReason }}</p>

      <div v-else class="stack">
        <FacilityCard v-for="f in referral.facilities" :key="f.facilityId" :facility="f" show-distance />
        <p class="muted">거리는 직선거리 기준이며 실제 이동 경로와 다를 수 있습니다.</p>
      </div>

      <RouterLink class="btn btn--secondary btn--block" to="/map">전체 기관 보기</RouterLink>
    </section>

    <!-- 임계값 미만이면 지도 이동 경로만 (FR-021c) -->
    <section v-else class="stack">
      <RouterLink class="btn btn--secondary btn--block" to="/map">
        우리 지역 복지서비스 신청처 찾아보기
      </RouterLink>
    </section>

    <!-- FR-013 참고 정보 고지 -->
    <p class="disclaimer">{{ r.disclaimer }}</p>

    <!-- 과소 판정 대비 상시 경로 (spec Edge Cases) -->
    <p class="muted">
      실제 상황이 결과와 다르다고 느끼신다면, 위 기관이나 지역 발달장애인지원센터에 상담을 요청해 보세요.
    </p>

    <!-- FR-025 저장 취소 -->
    <div v-if="r.cancelToken && !cancelled" class="cancelbox">
      <p class="muted">이 화면을 벗어나기 전까지 저장을 취소하실 수 있습니다. 저장된 응답은 익명이라 이후에는 찾아낼 수 없습니다.</p>
      <button class="btn btn--ghost" type="button" @click="cancelStorage">저장 취소하기</button>
    </div>
    <p v-else-if="cancelled" class="notice">저장을 취소했습니다. 응답은 학습에 사용되지 않습니다.</p>

    <div class="row">
      <button class="btn btn--ghost" type="button" @click="restart">처음으로</button>
      <span class="muted ver">모델 {{ r.modelVersion }}</span>
    </div>
  </div>
</template>

<style scoped>
.undecided { border: 2px solid var(--border-strong); background: var(--surface-soft);
  border-radius: var(--radius-lg); padding: var(--sp-lg); }
.undecided__who { font-size: 14px; color: var(--muted); margin: 0 0 var(--sp-sm); }
.undecided__title { font-size: 22px; font-weight: 700; color: var(--ink); margin: 0 0 var(--sp-sm); }
.undecided__body { margin: 0; font-size: 16px; }
.adjust { background: var(--surface-strong); border-left: 4px solid var(--border-strong);
  padding: var(--sp-md); border-radius: var(--radius-sm); font-size: 14px; margin: 0; }
.counsel { background: #fff4f1; border: 1px solid #f4c7bd; color: var(--error-text);
  padding: var(--sp-md); border-radius: var(--radius-sm); font-size: 15px; margin: 0; }
.outrange { background: var(--surface-soft); border: 1px solid var(--hairline);
  padding: var(--sp-md); border-radius: var(--radius-sm); font-size: 14px; }
.outrange p { margin: 0 0 var(--sp-xs); }
.notice { background: var(--surface-soft); color: var(--muted); font-size: 14px;
  padding: var(--sp-md); border-radius: var(--radius-sm); margin: 0; }
.disclaimer { font-size: 13px; color: var(--muted); border-top: 1px solid var(--hairline-soft); padding-top: var(--sp-md); }
.cancelbox { border: 1px dashed var(--hairline); border-radius: var(--radius-md); padding: var(--sp-md); }
.btn--block { text-decoration: none; }
.ver { align-self: center; }
</style>
