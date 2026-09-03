<script setup lang="ts">
/* 05 마이페이지 — 저장해 둔 기관을 모아 보는 방 (2026-09-03)
 *
 * 참고: uibowl 의 마이페이지 패턴. 다만 계정 화면의 관례(프로필 사진·설정
 * 목록)는 쓰지 않는다 — 이 서비스에는 계정이 없다. 여기 '마이'는 사람이
 * 아니라 **이 브라우저**를 뜻하고, 그 사실을 감추지 않고 화면에 적는다.
 *
 * 즐겨찾기는 localStorage 에만 있다(stores/favorites.ts). 서버에 두려면
 * 서버가 "이 사람이 누구인지"를 알아야 하는데, 로그인이 없고 헌법 원칙 III
 * 가 개인 식별 보관을 금하므로 둘 수 없다.
 */
import { computed, onMounted, ref } from 'vue';
import RoomHead from '../components/RoomHead.vue';
import { useFavoriteStore } from '../stores/favorites';
import { useEventStore } from '../stores/events';

const fav = useFavoriteStore();
const events = useEventStore();

const LABEL: Record<string, string> = {
  DAY_ACTIVITY: '주간활동', AFTERSCHOOL_YOUTH: '청소년 방과후',
};

// 최근에 담은 것이 위로. savedAt 이 없던 옛 항목도 뒤로 밀리기만 하고 사라지지 않는다.
const items = computed(() =>
  [...fav.items].sort((a, b) => String(b.savedAt ?? '').localeCompare(String(a.savedAt ?? ''))));

const myReviewCount = ref(0);

function when(iso?: string) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const days = Math.floor((Date.now() - d.getTime()) / 86_400_000);
  if (days <= 0) return '오늘 저장';
  if (days === 1) return '어제 저장';
  return `${days}일 전 저장`;
}

function directions(f: { name: string; address: string | null }) {
  events.track('CONTACT_ACTION');
  const q = encodeURIComponent(f.address || f.name);
  window.open(`https://map.kakao.com/link/search/${q}`, '_blank', 'noopener');
}

onMounted(() => {
  events.track('MYPAGE_ENTER');
  try {
    const t = JSON.parse(localStorage.getItem('cb.reviewTokens') ?? '{}');
    myReviewCount.value = Object.keys(t).length;
  } catch { /* noop */ }
});
</script>

<template>
  <div class="container room">
    <RoomHead
      no="05"
      eyebrow="마이페이지"
      title="저장해 두신 곳"
      lead="기관 카드의 별을 누르면 여기에 모입니다. 전화번호와 주소를 매번 다시 찾지 않으셔도 됩니다."
    />

    <section class="panel" aria-labelledby="fav-h">
      <h2 id="fav-h" class="panel__h">
        즐겨찾기<span v-if="items.length" class="cnt">{{ items.length }}곳</span>
      </h2>

      <div v-if="!items.length" class="empty">
        <p class="empty__h">아직 저장해 두신 곳이 없습니다</p>
        <p class="empty__b">
          지도나 진단 결과에서 마음에 드는 기관을 찾으시면, 카드 오른쪽 위의 별(☆)을 눌러 두세요.
          다음에 오실 때 여기에서 바로 전화하실 수 있습니다.
        </p>
        <RouterLink class="btn" to="/map">기관 찾으러 가기</RouterLink>
      </div>

      <ul v-else class="favs">
        <li v-for="f in items" :key="f.facilityId" class="fav">
          <div class="fav__top">
            <RouterLink class="fav__name" :to="`/facility/${f.facilityId}`">{{ f.name }}</RouterLink>
            <button type="button" class="fav__off" :aria-label="`${f.name} 즐겨찾기 해제`"
                    @click="fav.remove(f.facilityId)">별 해제</button>
          </div>

          <p v-if="f.serviceTypes?.length" class="fav__chips">
            <span v-for="t in f.serviceTypes" :key="t" class="chip">{{ LABEL[t] ?? t }}</span>
          </p>
          <p v-if="f.address" class="fav__addr">{{ f.address }}</p>
          <p class="fav__when">{{ when(f.savedAt) }}</p>

          <div class="fav__row">
            <a v-if="f.phone" class="btn btn--secondary" :href="`tel:${f.phone}`">전화 {{ f.phone }}</a>
            <span v-else class="fav__nophone">등록된 전화번호가 없습니다.</span>
            <button class="btn btn--ghost" type="button" @click="directions(f)">길찾기</button>
          </div>
        </li>
      </ul>
    </section>

    <section class="panel" aria-labelledby="note-h">
      <h2 id="note-h" class="panel__h">이 방에 대해</h2>
      <ul class="notes">
        <li>
          <b>이 목록은 지금 쓰시는 브라우저 안에만 저장됩니다.</b>
          로그인이 없어 서버는 누가 무엇을 저장했는지 알지 못합니다.
          다른 기기나 시크릿 창에서는 보이지 않고, 브라우저 기록을 지우면 함께 지워집니다.
        </li>
        <li v-if="myReviewCount">
          이 브라우저에서 올린 후기가 {{ myReviewCount }}개 있습니다.
          <RouterLink to="/reviews">소통방</RouterLink>에서 직접 지우실 수 있습니다.
        </li>
        <li>
          진단 결과는 여기에 남기지 않습니다. 결과는 그때그때 계산해 보여 드리고,
          개인을 알아볼 수 있는 형태로는 저장하지 않습니다.
        </li>
      </ul>
    </section>

    <nav class="hop" aria-label="다른 방으로">
      <RouterLink class="hop__a" to="/map">복지서비스 위치</RouterLink>
      <RouterLink class="hop__a" to="/reviews">이용 후기 소통방</RouterLink>
      <RouterLink class="hop__a" to="/diagnosis/start">부담감 진단</RouterLink>
    </nav>
  </div>
</template>

<style scoped>
.cnt { margin-left: 12px; font-family: system-ui, sans-serif; font-size: 14px; color: var(--muted); letter-spacing: 0; }
.empty .btn { margin-top: var(--sp-md); text-decoration: none; display: inline-block; }

.favs { list-style: none; margin: 0; padding: 0; }
.fav { border-top: 1px solid var(--hairline-soft); padding-block: clamp(16px, 2vw, 24px); }
.fav:first-child { border-top: 0; padding-top: 0; }
.fav__top { display: flex; align-items: baseline; gap: var(--sp-md); }
.fav__name { font-size: 19px; font-weight: 700; color: var(--ink); text-decoration: none; }
.fav__name:hover { text-decoration: underline; }
.fav__off {
  margin-left: auto; flex: none; min-height: 36px; padding: 6px 12px; cursor: pointer;
  background: none; border: 1px solid var(--hairline); border-radius: var(--radius-pill);
  font: inherit; font-size: 13px; color: var(--muted);
}
.fav__off:hover { background: var(--surface-soft); color: var(--ink); border-color: var(--border-strong); }
.fav__chips { display: flex; gap: 6px; flex-wrap: wrap; margin: 10px 0 6px; }
.chip { font-size: 12px; background: var(--surface-strong); border-radius: var(--radius-pill); padding: 4px 10px; color: var(--ink); }
.fav__addr { margin: 0 0 4px; font-size: 15px; }
.fav__when { margin: 0 0 var(--sp-md); font-size: 13px; color: var(--muted-soft); }
.fav__row { display: flex; gap: var(--sp-sm); flex-wrap: wrap; align-items: center; }
.fav__row .btn { text-decoration: none; font-size: 15px; min-height: 44px; padding: 10px var(--sp-base); }
.fav__nophone { font-size: 13px; color: var(--muted); }

.notes { margin: 0; padding-left: 1.15em; }
.notes li { margin-bottom: var(--sp-sm); line-height: 1.65; color: var(--body); }
</style>
