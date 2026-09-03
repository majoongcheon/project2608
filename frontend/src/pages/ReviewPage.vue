<script setup lang="ts">
/* 04 이용 후기 소통방 — 실제로 이용해 본 사람들이 기관에 대해 이야기하는 방 (2026-09-03)
 *
 * 참고: uibowl 의 리뷰 패턴(별점 · 목록 · 쓰기 폼). 다만 상점 리뷰의 노란 별과
 * 카드 그림자는 가져오지 않는다. 여기 언어는 홈과 같다 — 괘선, 크림·테라코타,
 * 명조 제목. 별점도 색이 아니라 **채워진 별 개수와 숫자**로 읽히게 둔다(FR-041).
 *
 * 로그인이 없다. 그래서
 *   · 별명만 받는다(실명·연락처를 받지 않는다).
 *   · 글을 쓰면 서버가 무작위 열쇠를 돌려주고, 그 열쇠를 가진 브라우저만
 *     자기 글을 지울 수 있다. 열쇠는 이 브라우저 안에만 있다.
 */
import { ref, computed, onMounted } from 'vue';
import RoomHead from '../components/RoomHead.vue';
import { api } from '../services/apiClient';
import { useEventStore } from '../stores/events';
import { useFavoriteStore } from '../stores/favorites';

const events = useEventStore();
const fav = useFavoriteStore();

const recent = ref<any[]>([]);
const loading = ref(true);
const error = ref('');

// ── 어느 기관에 쓸지 고르기 ───────────────────────────────────────────────
// 즐겨찾기에 담아 둔 기관이 있으면 그것부터 보여 준다 — 후기를 쓸 만한 곳은
// 대개 이미 저장해 둔 곳이다. 없으면 지역을 골라 목록에서 찾는다.
const regions = ref<any[]>([]);
const sido = ref('');
const regionCode = ref('');
const found = ref<any[]>([]);
const searching = ref(false);
const sidos = computed(() => [...new Set(regions.value.map((r) => r.sidoName))]);
const inSido = computed(() => regions.value.filter((r) => r.sidoName === sido.value));

// ── 쓰기 ──────────────────────────────────────────────────────────────────
const target = ref<{ facilityId: number; name: string } | null>(null);
const nickname = ref('');
const rating = ref(0);
const body = ref('');
const sending = ref(false);
const formError = ref('');
const done = ref(false);
const facilityReviews = ref<any[]>([]);
const facilityAvg = ref<{ count: number; averageRating: number | null } | null>(null);

const TOKENS = 'cb.reviewTokens';   // { [reviewId]: ownerToken }
const NICK = 'cb.nickname';

function tokens(): Record<string, string> {
  try { return JSON.parse(localStorage.getItem(TOKENS) ?? '{}'); } catch { return {}; }
}
function rememberToken(id: number, token: string) {
  try {
    const t = tokens(); t[String(id)] = token;
    localStorage.setItem(TOKENS, JSON.stringify(t));
  } catch { /* noop */ }
}
const mine = (id: number) => Boolean(tokens()[String(id)]);

function when(iso: string) {
  const d = new Date(iso);
  const days = Math.floor((Date.now() - d.getTime()) / 86_400_000);
  if (days <= 0) return '오늘';
  if (days === 1) return '어제';
  if (days < 30) return `${days}일 전`;
  return d.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' });
}

async function loadRecent() {
  loading.value = true;
  try { recent.value = (await api.reviews(30)).reviews; }
  catch { error.value = '후기를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.'; }
  finally { loading.value = false; }
}

async function searchRegion() {
  if (!regionCode.value) return;
  searching.value = true;
  try { found.value = (await api.facilities({ regionCode: regionCode.value, limit: 30 })).facilities; }
  catch { found.value = []; }
  finally { searching.value = false; }
}

// 목록만 다시 읽는다. 올린 직후에도 부르는데, 여기서 done 을 건드리면
// "올렸습니다" 가 뜨자마자 지워진다(실제로 그랬다 — 화면에 성공 표시가
// 한 번도 나오지 않았다).
async function loadFacilityReviews(facilityId: number) {
  try {
    const d = await api.facilityReviews(facilityId);
    facilityReviews.value = d.reviews;
    facilityAvg.value = { count: d.count, averageRating: d.averageRating };
  } catch { facilityReviews.value = []; facilityAvg.value = null; }
}

async function pick(f: { facilityId: number; name: string }) {
  target.value = { facilityId: f.facilityId, name: f.name };
  done.value = false;
  formError.value = '';
  await loadFacilityReviews(f.facilityId);
}

async function submit() {
  if (!target.value) return;
  formError.value = '';
  sending.value = true;
  try {
    const r = await api.writeReview(target.value.facilityId, {
      nickname: nickname.value, rating: rating.value, body: body.value,
    });
    rememberToken(r.reviewId, r.ownerToken);
    try { localStorage.setItem(NICK, nickname.value); } catch { /* noop */ }
    events.track('REVIEW_WRITE');
    done.value = true;
    body.value = '';
    rating.value = 0;
    await Promise.all([loadRecent(), loadFacilityReviews(target.value.facilityId)]);
  } catch (e: any) {
    formError.value = e?.body?.message ?? '후기를 올리지 못했습니다. 잠시 후 다시 시도해 주세요.';
  } finally { sending.value = false; }
}

async function removeMine(reviewId: number) {
  const token = tokens()[String(reviewId)];
  if (!token) return;
  try {
    await api.deleteReview(reviewId, token);
    await loadRecent();
    if (target.value) await loadFacilityReviews(target.value.facilityId);
  } catch { error.value = '글을 지우지 못했습니다.'; }
}

onMounted(async () => {
  events.track('REVIEW_ENTER');
  try { nickname.value = localStorage.getItem(NICK) ?? ''; } catch { /* noop */ }
  await loadRecent();
  try { regions.value = (await api.regions()).regions; } catch { /* 지역 목록 없이도 읽기는 된다 */ }
});
</script>

<template>
  <div class="container room">
    <RoomHead
      no="04"
      eyebrow="이용 후기 소통방"
      title="다녀오신 이야기를 들려주세요"
      lead="실제로 이용해 보신 분들의 이야기가 다음 사람에게 가장 큰 도움이 됩니다. 별명으로만 기록하고 연락처는 받지 않습니다."
    />

    <!-- ── 후기 남기기 ─────────────────────────────────────────────────── -->
    <section class="panel" aria-labelledby="write-h">
      <h2 id="write-h" class="panel__h">후기 남기기</h2>

      <template v-if="!target">
        <p class="hint">어느 기관에 대한 이야기인가요?</p>

        <div v-if="fav.items.length" class="picks">
          <p class="picks__lb">즐겨찾기에 담아 두신 곳</p>
          <ul class="picks__ul">
            <li v-for="f in fav.items" :key="f.facilityId">
              <button type="button" class="pickb" @click="pick(f)">{{ f.name }}</button>
            </li>
          </ul>
        </div>

        <div class="picks">
          <p class="picks__lb">지역에서 찾기</p>
          <div class="selrow">
            <label class="sel">
              <span class="sel__lb">시 · 도</span>
              <select v-model="sido" @change="regionCode = ''; found = []">
                <option value="">선택</option>
                <option v-for="s in sidos" :key="s" :value="s">{{ s }}</option>
              </select>
            </label>
            <label class="sel">
              <span class="sel__lb">시 · 군 · 구</span>
              <select v-model="regionCode" :disabled="!sido" @change="searchRegion">
                <option value="">선택</option>
                <option v-for="r in inSido" :key="r.regionCode" :value="r.regionCode">{{ r.sigunguName }}</option>
              </select>
            </label>
          </div>
          <p v-if="searching" class="hint">찾는 중…</p>
          <ul v-else-if="found.length" class="picks__ul">
            <li v-for="f in found" :key="f.facilityId">
              <button type="button" class="pickb" @click="pick(f)">{{ f.name }}</button>
            </li>
          </ul>
          <p v-else-if="regionCode" class="hint">이 지역에서 등록된 기관을 찾지 못했습니다.</p>
        </div>
      </template>

      <template v-else>
        <p class="target">
          <b>{{ target.name }}</b>
          <button type="button" class="linklike" @click="target = null; done = false">다른 기관 고르기</button>
        </p>

        <p v-if="facilityAvg" class="avg">
          <template v-if="facilityAvg.count">
            지금까지 후기 {{ facilityAvg.count }}개 · 평균 {{ facilityAvg.averageRating }}점
            <span v-if="facilityAvg.count < 3" class="avg__few">— 아직 후기가 적어 평균은 참고만 해 주세요</span>
          </template>
          <template v-else>아직 이 기관의 첫 후기입니다.</template>
        </p>

        <form class="form" @submit.prevent="submit">
          <fieldset class="stars">
            <legend class="sel__lb">어떠셨나요?</legend>
            <button v-for="n in 5" :key="n" type="button" class="star"
                    :class="{ 'star--on': n <= rating }"
                    :aria-pressed="n <= rating" :aria-label="`${n}점`"
                    @click="rating = n">
              <span aria-hidden="true">{{ n <= rating ? '★' : '☆' }}</span>
            </button>
            <span class="stars__n">{{ rating ? `${rating}점` : '별점을 골라 주세요' }}</span>
          </fieldset>

          <label class="sel">
            <span class="sel__lb">별명</span>
            <input v-model="nickname" type="text" maxlength="20" placeholder="예: 햇살맘" />
          </label>

          <label class="sel">
            <span class="sel__lb">이야기</span>
            <textarea v-model="body" rows="4" maxlength="600"
                      placeholder="어떤 점이 도움이 되었는지, 무엇을 미리 알았으면 좋았을지 적어 주세요."></textarea>
            <span class="count">{{ body.length }} / 600</span>
          </label>

          <p class="warnbox">
            전화번호·이메일·주민등록번호는 적지 말아 주세요. 누구나 볼 수 있는 글입니다.
          </p>

          <p v-if="formError" class="err" role="alert">{{ formError }}</p>
          <p v-if="done" class="ok" role="status">올렸습니다. 고맙습니다.</p>

          <button class="btn" type="submit" :disabled="sending || !rating || body.trim().length < 5">
            {{ sending ? '올리는 중…' : '후기 올리기' }}
          </button>
        </form>

        <div v-if="facilityReviews.length" class="sub">
          <h3 class="sub__h">이 기관의 후기</h3>
          <ul class="rv">
            <li v-for="r in facilityReviews" :key="r.reviewId" class="rv__li">
              <p class="rv__meta">
                <span class="rv__star" aria-hidden="true">{{ '★'.repeat(r.rating) }}{{ '☆'.repeat(5 - r.rating) }}</span>
                <span class="sr">{{ r.rating }}점</span>
                <b>{{ r.nickname }}</b><span class="rv__when">{{ when(r.createdAt) }}</span>
                <button v-if="mine(r.reviewId)" type="button" class="linklike" @click="removeMine(r.reviewId)">지우기</button>
              </p>
              <p class="rv__body">{{ r.body }}</p>
            </li>
          </ul>
        </div>
      </template>
    </section>

    <!-- ── 최근 후기 ───────────────────────────────────────────────────── -->
    <section class="panel" aria-labelledby="recent-h">
      <h2 id="recent-h" class="panel__h">최근 올라온 이야기</h2>

      <p v-if="error" class="err" role="alert">{{ error }}</p>
      <p v-else-if="loading" class="hint">불러오는 중…</p>

      <div v-else-if="!recent.length" class="empty">
        <p class="empty__h">아직 올라온 후기가 없습니다</p>
        <p class="empty__b">
          첫 이야기를 남겨 주시면 다음에 오는 분이 훨씬 덜 헤맵니다.
          위에서 기관을 고르고 짧게라도 적어 주세요.
        </p>
      </div>

      <ul v-else class="rv">
        <li v-for="r in recent" :key="r.reviewId" class="rv__li">
          <p class="rv__meta">
            <span class="rv__star" aria-hidden="true">{{ '★'.repeat(r.rating) }}{{ '☆'.repeat(5 - r.rating) }}</span>
            <span class="sr">{{ r.rating }}점</span>
            <b>{{ r.nickname }}</b><span class="rv__when">{{ when(r.createdAt) }}</span>
            <button v-if="mine(r.reviewId)" type="button" class="linklike" @click="removeMine(r.reviewId)">지우기</button>
          </p>
          <p class="rv__body">{{ r.body }}</p>
          <RouterLink v-if="r.facilityId" class="rv__fac" :to="`/facility/${r.facilityId}`">
            {{ r.facilityName ?? '기관 보기' }} →
          </RouterLink>
        </li>
      </ul>
    </section>

    <nav class="hop" aria-label="다른 방으로">
      <RouterLink class="hop__a" to="/map">복지서비스 위치</RouterLink>
      <RouterLink class="hop__a" to="/me">마이페이지</RouterLink>
      <RouterLink class="hop__a" to="/talk">정보 소통방</RouterLink>
    </nav>
  </div>
</template>

<style scoped>
.hint { margin: 0 0 var(--sp-sm); color: var(--muted); font-size: 15px; }
.picks + .picks { margin-top: clamp(16px, 2vw, 24px); }
.picks__lb { margin: 0 0 8px; font-size: 13px; font-weight: 700; color: var(--muted); letter-spacing: .04em; }
.picks__ul { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 8px; }
.pickb {
  min-height: 42px; padding: 8px 14px; font: inherit; font-size: 15px; cursor: pointer;
  background: none; border: 1px solid var(--hairline); border-radius: var(--radius-pill); color: var(--ink);
}
.pickb:hover { background: var(--surface-soft); border-color: var(--border-strong); }

.selrow { display: flex; gap: var(--sp-sm); flex-wrap: wrap; margin-bottom: var(--sp-sm); }
.sel { display: block; flex: 1 1 180px; }
.sel__lb { display: block; font-size: 13px; font-weight: 700; color: var(--ink); margin-bottom: 6px; }
select, input[type='text'], textarea {
  width: 100%; padding: 12px var(--sp-md); font: inherit;
  border: 1px solid var(--border-strong); border-radius: var(--radius-sm); background: var(--canvas);
}
select { min-height: 48px; }

.target { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; margin: 0 0 8px; font-size: 18px; }
.avg { margin: 0 0 var(--sp-md); font-size: 14px; color: var(--muted); }
.avg__few { display: block; }

.form { display: grid; gap: var(--sp-md); }
.stars { border: 0; padding: 0; margin: 0; display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.stars legend { float: left; width: 100%; }
.star {
  background: none; border: 0; padding: 2px 4px; cursor: pointer;
  font-size: 30px; line-height: 1; color: var(--border-strong);
}
.star--on { color: var(--primary); }
.stars__n { margin-left: 8px; font-size: 14px; color: var(--muted); }
.count { display: block; text-align: right; font-size: 12px; color: var(--muted-soft); margin-top: 4px; }
.warnbox {
  margin: 0; font-size: 13px; color: var(--muted);
  border-left: 3px solid var(--hairline); padding: 4px 0 4px 12px;
}
.err { margin: 0; color: var(--error-text); font-size: 14px; }
.ok { margin: 0; color: var(--primary-on-tint); font-size: 14px; font-weight: 700; }

.sub { margin-top: clamp(20px, 3vw, 32px); }
.sub__h { margin: 0 0 var(--sp-sm); font-size: 16px; font-weight: 700; color: var(--muted); }

.rv { list-style: none; margin: 0; padding: 0; }
.rv__li { border-top: 1px solid var(--hairline-soft); padding-block: clamp(14px, 1.8vw, 20px); }
.rv__li:first-child { border-top: 0; padding-top: 0; }
.rv__meta { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; margin: 0 0 6px; font-size: 14px; }
.rv__star { color: var(--primary); letter-spacing: 1px; }
.rv__when { color: var(--muted-soft); }
.rv__body { margin: 0; line-height: 1.65; white-space: pre-line; }
.rv__fac {
  display: inline-block; margin-top: 8px; font-size: 14px;
  color: var(--primary-on-tint); text-decoration: none; border-bottom: 1px solid currentColor;
}
/* 문장 안에 섞인 글자 링크다. 한때 보이지 않는 44px 덮개(::after)로 표적을
   넓혔는데, 그 덮개가 **바로 위 선택지의 클릭을 가로채** 답이 안 골라졌다
   (2026-09-03 점검에서 잡음). 표적 크기 기준도 본문 속 인라인 링크는 예외로
   두는 쪽이라, 덮개를 걷고 글의 흐름을 지킨다. */
.linklike {
  background: none; border: 0; padding: 0;
  color: var(--link); text-decoration: underline; cursor: pointer; font: inherit;
}
.linklike { font-size: 13px; }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
</style>
