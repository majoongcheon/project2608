<script setup lang="ts">
// FR-001 — 두 메뉴를 동등한 비중으로. 사전 절차 없이 곧바로 진입(FR-002).
import { onMounted, ref } from 'vue';
import { useEventStore } from '../stores/events';
import { api } from '../services/apiClient';
const events = useEventStore();

const questionCount = ref<number | null>(null);
onMounted(async () => {
  events.track('PRESURVEY_ENTER');
  try { questionCount.value = (await api.config()).questionCount ?? null; } catch { /* 숫자 없이 진행 */ }
});

// 2024 발달장애인 일과 삶 실태조사 3,000가구의 실제 분포.
// 1이 가장 부담이 크고 5가 부담 없음인 역방향 척도다(CLAUDE.md).
const burden = [
  { step: 1, name: '최고부담군', n: 464,   heavy: true },
  { step: 2, name: '고부담군',   n: 1165,  heavy: true },
  { step: 3, name: '중간부담군', n: 916,   heavy: false },
  { step: 4, name: '저부담군',   n: 378,   heavy: false },
  { step: 5, name: '부담 없음',  n: 77,    heavy: false },
];
const TOTAL = 3000;
const heavyN = burden.filter((b) => b.heavy).reduce((a, b) => a + b.n, 0);
const pct = (n: number) => (n / TOTAL) * 100;
const fmt = (n: number) => n.toLocaleString('ko-KR');
</script>

<template>
  <div class="container stack">
    <header class="hero">
      <p class="hero__eyebrow">발달장애인 보호자를 위한 서비스</p>
      <h1 class="hero__h">어떤 <em>도움</em>이<br />필요하신가요?</h1>
      <p class="hero__lead measure">
        로그인도 회원가입도 없이, <b>바로</b> 이용하실 수 있습니다.
      </p>
    </header>

    <!-- 두 메뉴를 맨 위로. 색을 나눠 한눈에 구분되게 한다.
         두 카드는 크기·구조가 같아 비중은 동등하다(FR-001). -->
    <nav class="menu" aria-label="주요 기능">
      <RouterLink class="card card--diag" to="/diagnosis/start">
        <span class="card__icon" aria-hidden="true">
          <svg viewBox="0 0 44 44">
            <rect x="10" y="5" width="24" height="34" rx="4.5" fill="currentColor" />
            <path d="M16 14h12M16 21h8" stroke="#fff" stroke-width="2.2" stroke-linecap="round" />
            <path d="M25.6 25.6c1.15-1.2 3.05-1.2 4.2 0 1.15 1.2 1.15 3.15 0 4.35L25.6 34.4l-4.2-4.45c-1.15-1.2-1.15-3.15 0-4.35 1.15-1.2 3.05-1.2 4.2 0Z"
                  fill="#fff" />
          </svg>
        </span>
        <span class="card__title">부담감 진단</span>
        <span class="card__desc">몇 가지 질문에 답하시면 지금의 돌봄부담 수준과 <b>그렇게 본 이유</b>를 알려 드립니다.</span>
        <span class="card__meta">
          <template v-if="questionCount">질문 {{ questionCount }}개 · </template>약 3분
        </span>
      </RouterLink>

      <RouterLink class="card card--map" to="/map">
        <span class="card__icon" aria-hidden="true">
          <svg viewBox="0 0 44 44">
            <path d="M22 39s12-9.8 12-19a12 12 0 1 0-24 0c0 9.2 12 19 12 19Z" fill="currentColor" />
            <circle cx="22" cy="19.4" r="4.8" fill="#fff" />
          </svg>
        </span>
        <span class="card__title">복지서비스 위치 · 연락처</span>
        <span class="card__desc">우리 지역의 주간활동 · 청소년 방과후활동 <b>신청 접수처</b>를 지도와 목록으로 찾아 드립니다.</span>
        <span class="card__meta">전국 시군구 · 지도와 목록</span>
      </RouterLink>
    </nav>

    <div class="side">
      <!-- 인사말 -->
      <div class="letter measure">
        <p>돌봄의 무게는 겉으로 잘 드러나지 않습니다.</p>
        <p class="letter__lead">그래서 몇 가지만 여쭙고, 지금 어느 정도인지 함께 읽어 보려 합니다.</p>
        <p class="letter__soft">정답을 가리는 자리가 아니니 편한 대로 답해 주세요.</p>
      </div>

      <!-- 조사 결과 -->
      <section class="stat" aria-labelledby="stat-h">
        <p class="stat__eyebrow">2024년 전국 실태조사</p>
        <h2 id="stat-h" class="stat__h">
          <b>{{ fmt(TOTAL) }}가구</b> 가운데 <b class="hot">{{ fmt(heavyN) }}가구</b>가
          높은 돌봄부담을 안고 있었습니다.
        </h2>

        <!-- 1~5는 순서 있는 척도라 한 색상의 명도 단계로 그린다(무지개색 금지).
             어두울수록 부담이 크다. 색만으로 뜻이 전해지지 않게 아래 범례에
             단계 이름과 가구 수를 모두 적는다(FR-041). -->
        <div class="bar" role="img"
             :aria-label="`전체 ${fmt(TOTAL)}가구 중 최고부담군 ${fmt(burden[0].n)}가구, 고부담군 ${fmt(burden[1].n)}가구, 중간부담군 ${fmt(burden[2].n)}가구, 저부담군 ${fmt(burden[3].n)}가구, 부담 없음 ${fmt(burden[4].n)}가구`">
          <span v-for="b in burden" :key="b.step" class="bar__seg"
                :class="`bar__seg--${b.step}`" :style="{ width: pct(b.n) + '%' }"
                :title="`${b.name} ${fmt(b.n)}가구 (${pct(b.n).toFixed(1)}%)`"></span>
        </div>
        <div class="brace" aria-hidden="true">
          <span class="brace__hot" :style="{ width: pct(heavyN) + '%' }"></span>
          <span class="brace__rest"></span>
        </div>
        <p class="scale" aria-hidden="true">
          <span>← 매우 부담된다</span><span>전혀 부담되지 않는다 →</span>
        </p>
        <p class="bar__callout">
          <b>{{ (heavyN / TOTAL * 100).toFixed(1) }}%</b> — 절반이 넘습니다
        </p>

        <ul class="legend">
          <li v-for="b in burden" :key="b.step" :class="{ 'legend--hot': b.heavy }">
            <i :class="`sw sw--${b.step}`" aria-hidden="true"></i>
            <span class="legend__nm">{{ b.name }}</span>
            <span class="legend__n">{{ fmt(b.n) }}가구</span>
          </li>
        </ul>

        <p class="stat__note">힘든 것은 당신만의 일이 아닙니다.</p>
      </section>
    </div>

    <!-- 이용 흐름 -->
    <section class="flow" aria-label="이용 흐름">
      <h2 class="flow__h">진단은 이렇게 진행됩니다</h2>
      <ol class="flow__list">
        <li><b aria-hidden="true">1</b><span>몇 가지 질문에 답합니다.</span></li>
        <li><b aria-hidden="true">2</b><span>지금의 부담 수준과 <strong>그렇게 본 이유</strong>를 알려 드립니다.</span></li>
        <li><b aria-hidden="true">3</b><span>가까운 <strong class="map">신청처를 지도로</strong> 안내해 드립니다.</span></li>
      </ol>
    </section>

    <!-- 맺음말 -->
    <div class="sign">
      <p class="sign__body measure">
        답해 주신 내용은 결과를 계산하는 데에만 쓰고, 개인을 알아볼 수 있는 형태로 남기지 않습니다.
      </p>
      <p class="sign__from">곁 드림</p>
    </div>
  </div>
</template>

<style scoped>
/* ── 제목 ──────────────────────────────────────────────────────────────
   눈썹 문구 → 큰 제목 → 안내 한 줄. 세 단이 크기·색·굵기로 갈린다. */
.hero { display: grid; gap: var(--sp-sm); }
.hero__eyebrow {
  font-size: 13px; font-weight: 700; letter-spacing: .06em;
  color: var(--primary-on-tint); margin: 0;
}
.hero__h {
  font-size: 34px; font-weight: 700; line-height: 1.4; color: var(--ink);
  margin: 0; word-break: keep-all;
}
/* 강조어에만 색과 밑선. 밑선은 글자 아래를 지나가는 띠라 획을 가리지 않는다. */
.hero__h em {
  font-style: normal; color: var(--primary-on-tint);
  background: linear-gradient(var(--tertiary-tint), var(--tertiary-tint)) 0 82% / 100% 34% no-repeat;
  padding-inline: 2px;
}
.hero__lead { font-size: 16px; color: var(--muted); margin: 0; }
.hero__lead b { color: var(--ink); font-weight: 700; }

/* 척도 양끝 — 막대가 무엇에서 무엇으로 가는지 글로 밝힌다 */
.scale {
  display: flex; justify-content: space-between; gap: var(--sp-sm);
  font-size: 12px; color: var(--muted-soft); margin: 0 0 var(--sp-base);
}

/* .stack 의 간격 규칙은 .container 의 직계 자식에만 닿는다. .side 안의
   두 덩어리는 여기서 직접 띄운다.
   인사말과 조사 결과는 화면 폭과 상관없이 늘 위에서 아래로 읽는다. 좌우로
   나란히 놓으면 눈이 어디를 먼저 볼지 헷갈리고 두 단의 높이도 어긋난다.
   대신 위 두 메뉴 카드와 같은 폭을 그대로 써서 편지지의 여백선을 맞춘다. */
.side { display: grid; gap: var(--sp-xl); }

/* ── 홈페이지 모드에서 넓어진 자리를 채운다 ───────────────────────────── */
@media (min-width: 900px) {
  :root[data-width="wide"] .hero__h { font-size: 42px; }
  /* 인사말과 맺음말은 한 문장이 한 줄에 앉을 때 가장 잘 읽힌다. .measure 의
     62ch 규칙이 도로 접어 버리므로 여기서 풀고 줄바꿈을 막는다.
     좁은 종이(640px)에서는 넘치므로 넓은 모드에서만 건다. */
  :root[data-width="wide"] .letter,
  :root[data-width="wide"] .sign__body { max-width: none; }
  :root[data-width="wide"] .letter__lead,
  :root[data-width="wide"] .sign__body { white-space: nowrap; }
  /* 조사 결과도 종이 폭을 다 쓴다. 안쪽 여백만 한 단 더 넓힌다. */
  :root[data-width="wide"] .stat { padding: var(--sp-xxl) var(--sp-xl); }
}

/* ── 두 메뉴 ────────────────────────────────────────────────────────────
   구조·크기는 같게(동등 비중), 색만 나눈다. */
.menu { display: grid; gap: var(--sp-base); grid-template-columns: 1fr; }
@media (min-width: 620px) { .menu { grid-template-columns: 1fr 1fr; } }
.card {
  --hue: var(--primary); --hue-tx: var(--primary-on-tint);
  display: flex; flex-direction: column; gap: var(--sp-sm);
  border: 1px solid var(--hairline); border-top: 4px solid var(--hue);
  border-radius: var(--radius-lg); padding: var(--sp-lg);
  text-decoration: none; color: var(--body);
  background: var(--canvas); box-shadow: var(--shadow-soft);
}
/* 아이콘 글리프는 --icon-hue 로 따로 뽑아 둔다. 테두리·제목은 카드의 --hue 를
   그대로 쓰고, 아이콘만 한 단 진하게 눌러 두 카드를 구분한다. */
.card--map {
  --hue: var(--secondary); --hue-tx: var(--secondary-on-tint);
  --icon-fill: 26%; --icon-hue: var(--secondary-deep);
}
.card:hover { box-shadow: var(--shadow-card); border-color: var(--hairline); border-top-color: var(--hue); }
.card__icon {
  display: inline-flex; align-items: center; justify-content: center;
  width: 60px; height: 60px; border-radius: 16px;
  background: var(--surface-strong);                       /* color-mix 미지원 폴백 */
  background: color-mix(in srgb, var(--hue) var(--icon-fill, 15%), var(--canvas));
  color: var(--icon-hue, var(--hue));
}
.card__icon svg { width: 40px; height: 40px; display: block; }
.card__title { font-size: 21px; font-weight: 700; color: var(--hue-tx); line-height: 1.4; }
.card__desc { font-size: 15px; color: var(--muted); line-height: 1.75; word-break: keep-all; }
.card__desc b { color: var(--ink); font-weight: 700; }
.card__meta {
  margin-top: auto; padding-top: var(--sp-sm);
  border-top: 1px solid var(--hairline-soft);
  font-size: 13px; color: var(--muted-soft);
}

/* ── 인사말 ── */
/* 첫 문장 앞을 한 줄 비운다. 16px × 행간 1.85 = 30px 이 빈 줄 한 개다. */
.letter { color: var(--body); text-align: center; padding-top: 30px; }
.letter p { margin: 0 0 var(--sp-lg); word-break: keep-all; }
.letter p:last-child { margin-bottom: 0; }
.letter__lead { font-size: 19px; line-height: 1.9; color: var(--ink); font-weight: 500; }
.letter__soft { font-size: 15px; color: var(--muted); }

/* ── 조사 결과 ── */
.stat {
  background: var(--surface-soft); border: 1px solid var(--hairline);
  border-radius: var(--radius-md); padding: var(--sp-xl) var(--sp-lg);
}
.stat__eyebrow {
  font-size: 12px; font-weight: 700; letter-spacing: .06em;
  color: var(--muted-soft); margin: 0 0 var(--sp-base);
}
.stat__h {
  font-size: 19px; font-weight: 400; line-height: 1.95; color: var(--body);
  margin: 0 0 var(--sp-xl); word-break: keep-all;
}
.stat__h b { color: var(--ink); font-weight: 700; }
.stat__h b.hot { color: var(--plum-on-tint); font-size: 21px; }

.bar { display: flex; gap: 2px; height: 30px; margin-bottom: var(--sp-sm); }
.bar__seg { display: block; height: 100%; }
.bar__seg:first-child { border-radius: 4px 0 0 4px; }
.bar__seg:last-child { border-radius: 0 4px 4px 0; }
.bar__seg--1 { background: var(--burden-1); }
.bar__seg--2 { background: var(--burden-2); }
.bar__seg--3 { background: var(--burden-3); }
.bar__seg--4 { background: var(--burden-4); }
.bar__seg--5 { background: var(--burden-5); }

/* 막대와 같은 flex·gap 구조라 간격 계산까지 일치한다. 퍼센트만 맞추면
   2px 간격 4개 때문에 몇 px 어긋난다. */
.brace { display: flex; gap: 2px; margin-bottom: 6px; }
.brace__hot {
  height: 7px; flex: none;
  border: 2px solid var(--burden-2); border-top: 0; border-radius: 0 0 3px 3px;
}
.brace__rest { flex: 1; }
.bar__callout { font-size: 14px; color: var(--muted); margin: 0 0 var(--sp-lg); }
.bar__callout b { color: var(--tertiary-on-tint); font-size: 17px; font-weight: 700; }

.legend { list-style: none; margin: 0 0 var(--sp-lg); padding: 0; display: grid; gap: var(--sp-md); }
.legend li {
  display: grid; grid-template-columns: auto 1fr auto; gap: var(--sp-md);
  align-items: center; font-size: 14.5px; color: var(--muted);
  padding-bottom: var(--sp-md); border-bottom: 1px solid var(--hairline-soft);
}
.legend li:last-child { padding-bottom: 0; border-bottom: 0; }
.legend--hot { color: var(--ink); font-weight: 600; }
.sw { width: 11px; height: 11px; border-radius: 3px; display: block; }
.sw--1 { background: var(--burden-1); } .sw--2 { background: var(--burden-2); }
.sw--3 { background: var(--burden-3); } .sw--4 { background: var(--burden-4); }
.sw--5 { background: var(--burden-5); border: 1px solid var(--hairline); }
.legend__n { font-variant-numeric: tabular-nums; color: var(--muted-soft); }
.legend--hot .legend__n { color: var(--body); }

.stat__note {
  font-size: 17px; color: var(--ink); font-weight: 700;
  margin: var(--sp-lg) 0 0; padding-top: var(--sp-lg);
  border-top: 1px solid var(--hairline);
}

/* ── 이용 흐름 ── */
.flow { border-top: 1px solid var(--hairline); padding-top: var(--sp-lg); }
/* 제목 아래 한 줄을 비운다. 16px × 행간 1.7 = 27px 이 빈 줄 한 개다. */
.flow__h { font-size: 16px; color: var(--muted); font-weight: 600; margin: 0 0 calc(var(--sp-md) + 27px); }
.flow__list { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--sp-base); }
.flow__list li {
  display: grid; grid-template-columns: auto 1fr; gap: var(--sp-md);
  align-items: start; align-content: start;
  border: 1px solid var(--hairline); border-radius: var(--radius-md);
  padding: var(--sp-base); background: var(--canvas);
}
/* 1 → 3 으로 갈수록 동그라미가 진해진다. 걸음이 쌓여 결론으로 가는 순서를
   명도 하나로만 말한다(무지개색 금지). 배경 명도 L 이
   0.62 → 0.168 → 0.096 으로 단조 감소해 색을 못 봐도 순서가 읽힌다.
   2·3 번의 흰 숫자는 각각 4.82:1 · 7.17:1 로 AA 를 넘는다. */
.flow__list b {
  display: inline-flex; align-items: center; justify-content: center;
  width: 27px; height: 27px; border-radius: 50%; flex: none;
  background: var(--primary); color: #fff; font-size: 14px; font-weight: 700;
}
/* 첫 걸음은 가볍게 — 채운 색면 대신 연한 살구빛에 진한 숫자를 얹는다. */
.flow__list li:first-child b {
  background: var(--primary-disabled);                     /* color-mix 미지원 폴백 */
  background: color-mix(in srgb, var(--primary) 20%, var(--canvas));
  color: var(--primary-on-tint);
}
/* 마지막 걸음이 가장 진하다. 지도 카드 아이콘과 같은 색이라 "지도로
   안내" 라는 문장과 위의 복지서비스 카드가 눈으로 이어진다. */
.flow__list li:last-child b { background: var(--secondary-deep); }
.flow__list span { font-size: 16px; line-height: 1.7; color: var(--body); word-break: keep-all; }
.flow__list strong { color: var(--ink); font-weight: 700; }
.flow__list strong.map { color: var(--secondary-on-tint); }

/* 세 단으로 벌릴 때는 숫자를 글 옆이 아니라 글 위에 얹는다.
   옆에 두면 칸 너비는 같아도 문장 길이가 제각각이라, 1번 문장이 짧아 다음
   숫자까지 텅 비고 2번 문장은 길어 3번 숫자에 바싹 붙어 보인다. 숫자를 한
   줄 위로 올리면 세 숫자가 같은 줄에 같은 간격으로 놓인다. */
@media (min-width: 860px) {
  .flow__list { grid-template-columns: repeat(3, 1fr); column-gap: var(--sp-xl); }
  .flow__list li { grid-template-columns: 1fr; gap: var(--sp-base); }
}

/* ── 맺음말 ── */
.sign { border-top: 1px solid var(--hairline); padding-top: var(--sp-lg); }
.sign__body { font-size: 14px; color: var(--muted); margin: 0 auto; word-break: keep-all; line-height: 1.75; text-align: center; }
/* 맺음말과 서명 사이를 두 줄 비운다. 본문 14px × 행간 1.75 × 2줄 = 49px. */
.sign__from { font-size: 18px; font-weight: 700; color: var(--plum); text-align: right; margin: 49px 0 0; }
</style>
