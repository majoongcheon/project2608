<script setup lang="ts">
// FR-001 — 두 메뉴(01 진단 · 02 위치)를 동등한 비중으로. 사전 절차 없이 곧바로 진입(FR-002).
// 2026-09-03 15:50 방 셋(03 소통 · 04 후기 · 05 마이페이지)을 아래에 더했다.
// 01·02 와 같은 부품을 쓰되 괘선 한 줄로 층을 갈라, 그 둘의 동등함은 그대로 둔다.
//
// 2026-09-03 전면 개편 — awwwards SOTD 두 건에서 가져온 네 가지.
//   ① 큰 활자   대제목을 화면 폭까지(clamp 40~104px). 본문과 6.5배차.
//   ② 여백      숨통은 트되 과하지 않게. 처음 168px 까지 벌렸다가 '너무 띄엄띄엄
//               하고 스크롤이 길다'는 확인을 받고 절반으로 줄였다(14:55).
//   ③ 이미지    노을 들판에서 맞잡은 두 손(실제 사진). 처음엔 직접 그렸으나
//               '일러스트가 구리다'는 확인을 받고 사진으로 바꿨다(15:35).
//   ④ 모션      스크롤 등장 + 히어로 시차. prefers-reduced-motion 이면 전부 끈다.
// 카드 테두리를 걷어내고 괘선과 여백으로 가른다 — 상자가 있으면 '앱'으로 읽힌다.
import { onMounted, onBeforeUnmount, ref } from 'vue';
import { useEventStore } from '../stores/events';
import { api } from '../services/apiClient';
const events = useEventStore();

const questionCount = ref<number | null>(null);

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

// ── 모션 ────────────────────────────────────────────────────────────────
// 원칙 하나 — 연출이 실패해도 내용은 보여야 한다. 관찰자를 못 만들면
// 모든 .reveal 에 즉시 .is-in 을 붙여 정지 상태로 둔다.
const art = ref<HTMLElement | null>(null);
let io: IntersectionObserver | null = null;
let raf = 0;

function showAll(root: ParentNode) {
  root.querySelectorAll('.reveal').forEach((el) => el.classList.add('is-in'));
}

onMounted(async () => {
  events.track('PRESURVEY_ENTER');
  try { questionCount.value = (await api.config()).questionCount ?? null; } catch { /* 숫자 없이 진행 */ }

  const still = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  if (still || typeof IntersectionObserver === 'undefined') { showAll(document); return; }

  // 안전장치 — 관찰자가 어떤 이유로든 안 걸리면(임베드·프리렌더·탭 비활성)
  // 1.2초 뒤 남은 것을 전부 켠다. 연출보다 내용이 우선이다.
  window.setTimeout(() => showAll(document), 1200);

  io = new IntersectionObserver(
    (entries) => entries.forEach((e) => {
      if (e.isIntersecting) { e.target.classList.add('is-in'); io?.unobserve(e.target); }
    }),
    // 아래에서 12% 올라왔을 때 시작한다. 화면에 걸치자마자 켜면 이미 다 읽은
    // 뒤에 움직여서 오히려 방해가 된다.
    { rootMargin: '0px 0px -12% 0px', threshold: 0.01 },
  );
  document.querySelectorAll('.reveal').forEach((el) => io!.observe(el));

  window.addEventListener('scroll', onScroll, { passive: true });
});

// 히어로 시차 — 스크롤량의 일부만 그림에 준다. 값이 크면 멀미가 난다.
// setup 안에서 만든다: onMounted 의 async 콜백 안에서 onBeforeUnmount 를 부르면
// await 뒤에는 컴포넌트가 붙어 있지 않아 **등록이 통째로 무시된다**. 실제로
// Vue 가 경고를 냈고, 홈을 떠나도 스크롤 감시가 남아 있었다(2026-09-03 점검).
const onScroll = () => {
  if (raf) return;
  raf = requestAnimationFrame(() => {
    raf = 0;
    const y = window.scrollY;
    if (art.value && y < window.innerHeight * 1.2) {
      art.value.style.setProperty('--shift', `${y * 0.12}px`);
      art.value.style.setProperty('--shift-far', `${y * 0.045}px`);
    }
  });
};

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll);
  io?.disconnect();
  if (raf) cancelAnimationFrame(raf);
});
</script>

<template>
  <div class="home">
    <!-- ── 히어로 ────────────────────────────────────────────────────────
         글과 원반을 좌우로 나란히. 위아래로 쌓으면 첫 화면이 길어지고,
         겹치면 능선 위에서 본문 명암비가 떨어진다. -->
    <header class="hero bleed">
      <div class="hero__in container">
      <div ref="art" class="hero__art parallax">
        <!-- 원반. 띠로 깔면 위아래가 하드하게 잘려 '잘린 그림'으로 읽힌다 —
             원은 잘릴 수가 없다.

             2026-09-03 15:35 — 안쪽을 직접 그린 일러스트에서 **실제 사진**으로
             바꿨다(기획자 요청). 얼굴이 나오는 사진은 "이 사람이 당사자"로 읽힐
             수 있어 **손만 나오는 사진**을 골랐다. 노을·마른 들판이라 색을 새로
             만들지 않고도 지금 팔레트(크림·테라코타) 안에 그대로 앉는다.
             출처: Unsplash(Narissa de Villiers) · Unsplash License(무료·출처표기 불필요). -->
        <div class="hero__disc">
          <img class="hero__photo" src="/images/hero-hands.jpg" width="1100" height="1100"
               alt="해질녘 마른 들판에서 두 사람이 손을 맞잡고 나란히 서 있다" />
          <!-- 테두리 한 줄만. 처음에는 시계 문자판처럼 둘레에 눈금 24개를 둘렀는데,
               사진 위에서는 문자판이 아니라 **해에서 뻗은 빛살**로 읽혀 촌스러웠다
               (2026-09-03 기획자 확인). 원은 잘리지 않는다는 이점만 남기고 뺐다. -->
          <svg class="hero__ring" viewBox="0 0 400 400" aria-hidden="true">
            <circle cx="200" cy="200" r="176" fill="none" stroke="var(--hairline)" stroke-width="1.4" />
          </svg>
        </div>
      </div>

      <div class="hero__copy reveal is-in">
        <p class="hero__eyebrow">발달장애인 보호자를 위한 서비스</p>
        <h1 class="hero__h">
          <span class="reveal-line"><span>어떤 <em>도움</em>이</span></span>
          <span class="reveal-line" style="--reveal-delay:110ms"><span>필요하신가요?</span></span>
        </h1>
        <p class="hero__lead measure reveal" style="--reveal-delay:320ms">
          로그인도 회원가입도 없이, <b>바로</b> 이용하실 수 있습니다.
        </p>
      </div>
      </div>
    </header>

    <div class="container">
      <!-- ── 두 메뉴 ────────────────────────────────────────────────────
           상자를 없애고 번호·제목·괘선으로 세운다. 두 항목의 구조와 크기가
           같아 비중은 여전히 동등하다(FR-001). -->
      <nav class="menu" aria-label="주요 기능">
        <RouterLink class="item reveal" to="/diagnosis/start">
          <span class="item__no" aria-hidden="true">01</span>
          <span class="item__body">
            <span class="item__title">부담감 진단</span>
            <span class="item__desc measure">
              몇 가지 질문에 답하시면 지금의 돌봄부담 수준과<br />
              <b>그렇게 본 이유</b>를 알려 드립니다.
            </span>
            <span class="item__meta">
              <template v-if="questionCount">질문 {{ questionCount }}개 · </template>약 3분
            </span>
          </span>
          <span class="item__go" aria-hidden="true">
            <svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.6"
                 stroke-linecap="round" stroke-linejoin="round">
              <path d="M7 16h17M18 10l6 6-6 6" />
            </svg>
          </span>
        </RouterLink>

        <RouterLink class="item reveal" style="--reveal-delay:90ms" to="/map">
          <span class="item__no" aria-hidden="true">02</span>
          <span class="item__body">
            <span class="item__title">복지서비스 위치 · 연락처</span>
            <span class="item__desc measure">
              우리 지역의 주간활동 · 청소년 방과후활동 <b>신청 접수처</b>를<br />
              지도와 목록으로 찾아 드립니다.
            </span>
            <span class="item__meta">전국 시군구 · 지도와 목록</span>
          </span>
          <span class="item__go" aria-hidden="true">
            <svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.6"
                 stroke-linecap="round" stroke-linejoin="round">
              <path d="M7 16h17M18 10l6 6-6 6" />
            </svg>
          </span>
        </RouterLink>

        <!-- 03~05 (2026-09-03 추가). 앞의 둘과 **완전히 같은 구조**로 둔다 —
             번호·제목·설명·보조설명·화살표. 방을 늘리면서 모양이 갈라지면
             "다른 사이트"로 읽힌다. 다만 01·02 는 이 서비스가 하기로 한 두 가지고
             03~05 는 그 둘을 돕는 자리라, 사이에 괘선 하나로 층을 만든다. -->
        <span class="menu__gap" aria-hidden="true"></span>

        <RouterLink class="item reveal" style="--reveal-delay:180ms" to="/talk">
          <span class="item__no" aria-hidden="true">03</span>
          <span class="item__body">
            <span class="item__title">정보 소통방</span>
            <span class="item__desc measure">
              진단·결과·신청처가 어떻게 되는지 <b>물어보시면 답해 드립니다.</b><br />
              확실히 아는 것만 답하고, 모르는 것은 모른다고 말씀드립니다.
            </span>
            <span class="item__meta">대화는 이 브라우저 안에만 남습니다</span>
          </span>
          <span class="item__go" aria-hidden="true">
            <svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.6"
                 stroke-linecap="round" stroke-linejoin="round">
              <path d="M7 16h17M18 10l6 6-6 6" />
            </svg>
          </span>
        </RouterLink>

        <RouterLink class="item reveal" style="--reveal-delay:240ms" to="/reviews">
          <span class="item__no" aria-hidden="true">04</span>
          <span class="item__body">
            <span class="item__title">이용 후기 소통방</span>
            <span class="item__desc measure">
              먼저 다녀오신 분들이 남긴 이야기를 읽고, <b>내 경험도 남길 수 있습니다.</b><br />
              별명으로만 기록하고 연락처는 받지 않습니다.
            </span>
            <span class="item__meta">기관별 후기 · 별점</span>
          </span>
          <span class="item__go" aria-hidden="true">
            <svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.6"
                 stroke-linecap="round" stroke-linejoin="round">
              <path d="M7 16h17M18 10l6 6-6 6" />
            </svg>
          </span>
        </RouterLink>

        <RouterLink class="item reveal" style="--reveal-delay:300ms" to="/me">
          <span class="item__no" aria-hidden="true">05</span>
          <span class="item__body">
            <span class="item__title">마이페이지</span>
            <span class="item__desc measure">
              별을 눌러 <b>즐겨찾기</b>에 담아 두신 기관을 <b>한자리에 모아</b> 보여 드립니다.<br />
              전화번호와 주소를 매번 다시 찾지 않으셔도 됩니다.
            </span>
            <span class="item__meta">이 브라우저에만 저장 · 로그인 없음</span>
          </span>
          <span class="item__go" aria-hidden="true">
            <svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.6"
                 stroke-linecap="round" stroke-linejoin="round">
              <path d="M7 16h17M18 10l6 6-6 6" />
            </svg>
          </span>
        </RouterLink>
      </nav>

      <!-- ── 인사말 ─────────────────────────────────────────────────────
           가운데 정렬을 버렸다. 한글 긴 문장은 왼쪽 정렬이 눈이 덜 튄다. -->
      <section class="letter reveal">
        <p class="letter__lead measure">돌봄의 무게는 겉으로 잘 드러나지 않습니다.</p>
        <p class="letter__body measure">그래서 몇 가지만 여쭙고, 지금 어느 정도인지 함께 읽어 보려 합니다.</p>
        <p class="letter__soft measure">정답을 가리는 자리가 아니니 편한 대로 답해 주세요.</p>
      </section>
    </div>

    <!-- ── 조사 결과 ──────────────────────────────────────────────────────
         숫자를 화면 폭으로 키운다. 레퍼런스가 데이터를 다루는 방식이다. -->
    <section class="stat bleed" aria-labelledby="stat-h">
      <div class="container">
        <p class="stat__eyebrow reveal">2024년 전국 실태조사</p>
        <h2 id="stat-h" class="stat__h reveal" style="--reveal-delay:80ms">
          <b class="stat__big">{{ fmt(TOTAL) }}가구</b> 가운데
          <!-- 숫자와 뒤에 붙는 조사를 한 덩어리로 묶는다. `.stat__big` 이
               inline-block 이라 그 경계에서 줄이 끊겨 "1,629가구 / 가" 로
               갈라졌다 — word-break:keep-all 은 이 경계까지는 막지 못한다. -->
          <span class="stat__grp"><b class="stat__big stat__big--hot">{{ fmt(heavyN) }}가구</b>가</span><br />
          높은 돌봄부담을 안고 있었습니다.
        </h2>

        <!-- 1~5는 순서 있는 척도라 한 색상의 명도 단계로 그린다(무지개색 금지).
             어두울수록 부담이 크다. 색만으로 뜻이 전해지지 않게 아래 범례에
             단계 이름과 가구 수를 모두 적는다(FR-041). -->
        <div class="bar reveal" style="--reveal-delay:160ms" role="img"
             :aria-label="`전체 ${fmt(TOTAL)}가구 중 최고부담군 ${fmt(burden[0].n)}가구, 고부담군 ${fmt(burden[1].n)}가구, 중간부담군 ${fmt(burden[2].n)}가구, 저부담군 ${fmt(burden[3].n)}가구, 부담 없음 ${fmt(burden[4].n)}가구`">
          <span v-for="b in burden" :key="b.step" class="bar__seg"
                :class="`bar__seg--${b.step}`" :style="{ width: pct(b.n) + '%' }"
                :title="`${b.name} ${fmt(b.n)}가구 (${pct(b.n).toFixed(1)}%)`"></span>
        </div>
        <div class="brace reveal" style="--reveal-delay:200ms" aria-hidden="true">
          <span class="brace__hot" :style="{ width: pct(heavyN) + '%' }"></span>
        </div>
        <p class="scale reveal" style="--reveal-delay:200ms" aria-hidden="true">
          <span>← 매우 부담된다</span><span>전혀 부담되지 않는다 →</span>
        </p>

        <p class="callout reveal" style="--reveal-delay:240ms">
          <b>{{ (heavyN / TOTAL * 100).toFixed(1) }}%</b>
          <span>절반이 넘습니다</span>
        </p>

        <ul class="legend reveal" style="--reveal-delay:280ms">
          <li v-for="b in burden" :key="b.step" :class="{ 'legend--hot': b.heavy }">
            <i :class="`sw sw--${b.step}`" aria-hidden="true"></i>
            <span class="legend__nm">{{ b.name }}</span>
            <span class="legend__n">{{ fmt(b.n) }}가구</span>
          </li>
        </ul>

        <p class="stat__note reveal" style="--reveal-delay:320ms">힘든 것은 당신만의 일이 아닙니다.</p>
      </div>
    </section>

    <div class="container">
      <!-- ── 이용 흐름 ──────────────────────────────────────────────────── -->
      <section class="flow" aria-label="이용 흐름">
        <h2 class="flow__h reveal">진단은 이렇게 진행됩니다</h2>
        <ol class="flow__list">
          <li class="reveal"><b aria-hidden="true">1</b><span>몇 가지 질문에 답합니다.</span></li>
          <li class="reveal" style="--reveal-delay:90ms">
            <b aria-hidden="true">2</b><span>지금의 부담 수준과 <strong>그렇게 본 이유</strong>를 알려 드립니다.</span>
          </li>
          <li class="reveal" style="--reveal-delay:180ms">
            <b aria-hidden="true">3</b><span>가까운 <strong>신청처를 지도로</strong> 안내해 드립니다.</span>
          </li>
        </ol>
      </section>
    </div>

    <!-- ── 맺음말 ─────────────────────────────────────────────────────────
         유일한 어두운 면. 크림 글자 12.16:1 로 대비는 오히려 본문보다 높다.
         레퍼런스의 '두 색' 인상이 여기서 나온다 — 색을 더 만들지 않고,
         이미 있는 먹색과 크림을 뒤집어 쓴다. -->
    <section class="sign bleed reveal">
      <div class="container">
        <p class="sign__body measure">
          답해 주신 내용은 결과를 계산하는 데에만 쓰고, 개인을 알아볼 수 있는 형태로 남기지 않습니다.
        </p>
        <p class="sign__from">곁 드림</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* ── 히어로 ──────────────────────────────────────────────────────────────
   그림은 배경이 아니라 한 덩이의 면이다. 높이를 vh 로 잡되 상한을 둬서
   작은 노트북에서 첫 화면이 그림만으로 차지 않게 한다. */
/* 글과 그림을 좌우로 나란히 둔다. 위아래로 쌓으면 첫 화면이 길어져 스크롤이
   늘어나고, 겹쳐 놓으면 능선 색 위에서 본문이 4.54:1 로 AA 문턱에 걸린다.
   나란히 두면 둘 다 없다. */
.hero { position: relative; background: var(--paper); }
.hero__in {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(0, .92fr);
  align-items: center;
  gap: clamp(20px, 4vw, 56px);
  padding-block: clamp(28px, 5vw, 72px) clamp(24px, 4vw, 56px);
}
/* DOM 순서는 그림이 먼저지만(격자 순서만 바꾼다), 읽는 순서는 글이 먼저다. */
.hero__copy { order: -1; }
.hero__art { position: relative; }
.hero__disc {
  position: relative; width: 100%; max-width: 420px; aspect-ratio: 1; margin-inline: auto;
}
/* 사진은 눈금 안쪽 원(지름 352/400 = 88%)에 정확히 들어간다 — 그래서 6% 안쪽.
   크기를 %로 직접 준다: <img> 는 replaced 요소라 inset 만 주고 width:auto 로 두면
   인셋 상자가 아니라 **원본 크기(1100px)** 로 풀려 원 밖으로 터진다(실제로 그랬다). */
.hero__photo {
  position: absolute; top: 6%; left: 6%;
  width: 88%; height: 88%;
  border-radius: 50%;
  object-fit: cover;
  /* 맞잡은 손이 원 한가운데 오도록 아래쪽을 본다. */
  object-position: 50% 64%;
  /* 색을 새로 만들지 않고 있는 팔레트 쪽으로 아주 조금만 당긴다. */
  filter: saturate(.92) contrast(1.02);
}
/* 종이에 인쇄된 느낌 — 크림 색을 아주 옅게 덮어 화면 사진 티를 뺀다. */
.hero__disc::after {
  content: ''; position: absolute; inset: 6%; border-radius: 50%;
  background: radial-gradient(circle at 50% 30%, rgba(255, 250, 245, .28), rgba(181, 86, 58, .10));
  pointer-events: none;
}
.hero__ring { position: absolute; inset: 0; width: 100%; height: 100%; }
/* 두 사람 — 넓은 화면은 해 앞(오른쪽), 좁은 화면은 화면 가운데.
   좁은 화면에서는 좌우가 잘려 오른쪽 자리가 보이지 않는다. */
/* 좁은 화면에서는 한 줄로 세우되, 원반을 작게 둬서 첫 화면에 `01 부담감 진단`
   이 들어오게 한다. 지친 보호자가 3분 안에 끝내는 흐름이라 첫 화면은 그림이
   아니라 다음 행동을 보여 줘야 한다. */
@media (max-width: 760px) {
  .hero__in { grid-template-columns: 1fr; gap: clamp(16px, 4vw, 28px); }
  .hero__disc { max-width: min(62vw, 250px); }
}
/* 시차 — 사진이 들어오면서 능선 세 겹이 없어졌다. 원반 전체를 아주 조금만
   움직인다(값이 크면 멀미가 난다). 눈금 고리는 제자리에 두어 기준이 된다. */
.hero__art .hero__photo { transform: translateY(calc(var(--shift, 0px) * -0.5)); }

.menu__gap { display: block; height: clamp(14px, 2vw, 26px); }
.hero__copy {
  position: relative;
  width: 100%;
  padding-block: clamp(44px, 9vw, 104px) clamp(28px, 5vw, 56px);
}
.hero__eyebrow {
  margin: 0 0 clamp(10px, 1.4vw, 16px);
  font-size: 14px; font-weight: 600; letter-spacing: .09em;
  text-transform: none; color: var(--primary-on-tint);
}
.hero__h {
  margin: 0;
  font-size: var(--display-1);
  font-weight: 700;
  line-height: 1.02;
  letter-spacing: var(--tracking-display);
  color: var(--ink);
}
/* 강조어 아래를 지나는 띠. 100px 활자에서 62% 부터 깔면 띠가 아니라 글자
   뒤에 놓인 네모로 읽힌다. 밑줄로 보이도록 아래 22% 로 낮췄다. */
.hero__h em {
  font-style: normal;
  background: linear-gradient(transparent 78%, var(--tertiary) 78%);
  padding-inline: .05em;
}
.hero__lead {
  margin: clamp(16px, 2vw, 24px) 0 0;
  font-size: var(--lede);
  line-height: 1.55;
  letter-spacing: var(--tracking-lede);
  color: var(--body);
}

/* ── 메뉴 ────────────────────────────────────────────────────────────────
   상자 없음. 위아래 괘선과 넉넉한 안쪽 여백만으로 누를 것이라고 말한다. */
.menu { margin-top: var(--gap-section); border-top: 1px solid var(--hairline); }
.item {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: start;
  gap: clamp(16px, 3vw, 40px);
  padding-block: clamp(20px, 2.8vw, 32px);
  border-bottom: 1px solid var(--hairline);
  color: inherit;
  text-decoration: none;
  transition: background-color .35s ease, padding-inline .35s ease;
}
.item:hover { background: var(--surface-soft); padding-inline: clamp(8px, 1.6vw, 20px); }
.item__no {
  font-size: clamp(13px, 1.4vw, 15px); font-weight: 600;
  color: var(--muted-soft); font-variant-numeric: tabular-nums; padding-top: .5em;
}
.item__body { display: block; }
.item__title {
  display: block;
  font-size: var(--display-3); font-weight: 700; line-height: 1.22;
  letter-spacing: var(--tracking-display);
  color: var(--ink);
  word-break: keep-all;
}
/* 설명은 지은이가 정한 자리에서 줄을 나눈다(2026-09-03 16:50 기획자 지정).
   <br> 로 나눈 두 마디는 좁은 화면에서 각자 다시 접히므로, 뜻 덩어리는
   유지되면서 폭에도 맞는다. */
.item__desc {
  display: block; margin-top: clamp(10px, 1.4vw, 16px);
  font-size: clamp(15px, 1.5vw, 17px); line-height: 1.6; color: var(--body);
}
.item__meta {
  display: block; margin-top: clamp(10px, 1.2vw, 14px);
  font-size: 14px; color: var(--muted);
}
.item__go { width: clamp(26px, 3vw, 34px); color: var(--primary); padding-top: .35em; }
.item__go svg { width: 100%; height: auto; display: block; transition: transform .35s ease; }
.item:hover .item__go svg { transform: translateX(5px); }

/* ── 인사말 ────────────────────────────────────────────────────────────── */
.letter { margin-top: var(--gap-section); }
.letter__lead {
  margin: 0; font-size: var(--display-2); font-weight: 600; line-height: 1.28;
  letter-spacing: var(--tracking-display); color: var(--ink);
}
.letter__body {
  margin: clamp(14px, 1.8vw, 20px) 0 0;
  font-size: var(--lede); line-height: 1.58; color: var(--body);
}
.letter__soft { margin: clamp(12px, 1.6vw, 18px) 0 0; font-size: 15px; color: var(--muted); }

/* ── 조사 결과 ───────────────────────────────────────────────────────────
   살구빛 책상 위에 올려 앞뒤 섹션과 면으로 구분한다. */
.stat {
  margin-top: var(--gap-section);
  padding-block: clamp(32px, 4.4vw, 64px);
  background: var(--page);
}
.stat__eyebrow {
  margin: 0 0 clamp(14px, 2vw, 22px);
  font-size: 14px; font-weight: 600; letter-spacing: .09em; color: var(--secondary-on-tint);
}
.stat__h {
  margin: 0 0 clamp(22px, 3vw, 36px);
  font-size: clamp(20px, 2.4vw, 28px); font-weight: 500; line-height: 1.5;
  letter-spacing: var(--tracking-lede); color: var(--ink);
}
.stat__big {
  font-size: var(--display-2); font-weight: 700; line-height: 1.06;
  letter-spacing: var(--tracking-display);
  display: inline-block; padding-block: .06em;
}
.stat__big--hot { color: var(--primary-on-tint); }
.stat__grp { white-space: nowrap; }

.bar { display: flex; width: 100%; height: clamp(22px, 3vw, 34px); overflow: hidden; }
.bar__seg { display: block; height: 100%; }
/* 칸 사이를 크림으로 갈라 준다 — 인접 색끼리의 경계가 아니라 각 칸이
   검증된 크림 위에 놓이게 해서 1.4.11(3:1)을 유지한다. */
.bar__seg + .bar__seg { border-left: 2px solid var(--paper); }
.bar__seg--1 { background: var(--burden-1); }
.bar__seg--2 { background: var(--burden-2); }
.bar__seg--3 { background: var(--burden-3); }
.bar__seg--4 { background: var(--burden-4); }
.bar__seg--5 { background: var(--burden-5); }

.brace { display: flex; height: 8px; margin-top: 6px; }
.brace__hot {
  display: block; height: 100%;
  border-left: 2px solid var(--primary); border-right: 2px solid var(--primary);
  border-bottom: 2px solid var(--primary);
}
.scale {
  display: flex; justify-content: space-between; margin: 10px 0 0;
  font-size: 13px; color: var(--muted);
}

.callout {
  display: flex; align-items: baseline; gap: clamp(12px, 1.6vw, 20px);
  margin: clamp(20px, 2.6vw, 32px) 0 0;
}
.callout b {
  font-size: var(--display-2); font-weight: 700; line-height: 1;
  letter-spacing: var(--tracking-display); color: var(--primary-on-tint);
  font-variant-numeric: tabular-nums;
}
.callout span { font-size: var(--lede); color: var(--body); }

.legend {
  list-style: none; margin: clamp(20px, 2.6vw, 30px) 0 0; padding: 0;
  display: grid; gap: 0;
  border-top: 1px solid var(--hairline);
}
.legend li {
  display: grid; grid-template-columns: auto 1fr auto; align-items: center;
  gap: 12px; padding-block: 13px;
  border-bottom: 1px solid var(--hairline);
  font-size: 15px; color: var(--body);
}
.legend--hot { font-weight: 600; color: var(--ink); }
.sw { width: 15px; height: 15px; border-radius: 3px; display: block; }
.sw--1 { background: var(--burden-1); } .sw--2 { background: var(--burden-2); }
.sw--3 { background: var(--burden-3); } .sw--4 { background: var(--burden-4); }
.sw--5 { background: var(--burden-5); border: 1px solid var(--hairline); }
.legend__n { color: var(--muted); font-variant-numeric: tabular-nums; }
.stat__note {
  margin: clamp(20px, 2.6vw, 30px) 0 0;
  font-size: var(--lede); color: var(--plum-on-tint);
}

/* ── 이용 흐름 ─────────────────────────────────────────────────────────── */
.flow { margin-top: var(--gap-section); }
.flow__h {
  margin: 0 0 clamp(16px, 2.2vw, 26px);
  font-size: var(--display-3); font-weight: 700; color: var(--ink);
}
.flow__list { list-style: none; margin: 0; padding: 0; border-top: 1px solid var(--hairline); }
.flow__list li {
  display: grid; grid-template-columns: auto 1fr; align-items: baseline;
  gap: clamp(16px, 2.4vw, 32px);
  padding-block: clamp(15px, 1.9vw, 22px);
  border-bottom: 1px solid var(--hairline);
  font-size: clamp(16px, 1.7vw, 19px); line-height: 1.55; color: var(--body);
}
.flow__list b {
  font-size: clamp(15px, 1.5vw, 17px); font-weight: 600;
  color: var(--muted-soft); font-variant-numeric: tabular-nums;
}
.flow__list strong { color: var(--ink); font-weight: 600; }

/* ── 맺음말 ─────────────────────────────────────────────────────────────
   화면에서 유일하게 뒤집힌 면. 크림 글자가 먹색 위에서 12.16:1 이다. */
.sign {
  margin-top: var(--gap-section);
  padding-block: clamp(36px, 4.8vw, 72px);
  background: var(--ink);
}
.sign__body {
  margin: 0;
  font-size: clamp(19px, 2.6vw, 30px); font-weight: 500; line-height: 1.55;
  letter-spacing: var(--tracking-lede);
  color: var(--paper);
}
.sign__from {
  margin: clamp(18px, 2.4vw, 28px) 0 0;
  font-size: var(--lede); color: var(--tertiary);
}

/* ── 좁은 화면 ───────────────────────────────────────────────────────────
   화살표를 지우고 번호를 제목 위로 올린다. 430px 에서 3열은 제목이 두
   글자씩 끊긴다. */
@media (max-width: 560px) {
  .item { grid-template-columns: 1fr; gap: 0; }
  .item__no { padding-top: 0; margin-bottom: 8px; }
  .item__go { display: none; }
  .legend li { grid-template-columns: auto 1fr; }
  .legend__n { grid-column: 2; text-align: right; }
}
</style>
