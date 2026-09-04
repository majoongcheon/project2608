<script setup lang="ts">
/* 03 정보 소통방 — 안내봇과 묻고 답하는 방 (2026-09-03)
 *
 * 참고: uibowl 의 메신저 패턴(말풍선 · 빠른 답장 · 아래 고정 입력줄).
 * 다만 메신저 앱의 색과 그림자는 가져오지 않는다. 여기 규칙은 홈과 같다 —
 * 상자 대신 괘선, 크림과 테라코타 두 색, 명조 제목.
 *
 * 답은 services/guideBot.ts 의 규칙에서 나온다. 모르는 것은 지어내지 않는다.
 * 대화는 이 브라우저 안에만 남고 서버로 가지 않는다(헌법 원칙 III).
 */
import { ref, nextTick, onMounted } from 'vue';
import RoomHead from '../components/RoomHead.vue';
import { answer, opening, TOPICS, BOT_STATS, isFallback, type BotReply } from '../services/guideBot';
import { api } from '../services/apiClient';
import { useEventStore } from '../stores/events';

interface Msg {
  who: 'bot' | 'me';
  text: string;
  suggestions?: string[];
  link?: { to: string; label: string };
  at: string;
}

const KEY = 'cb.talk';
const events = useEventStore();
const msgs = ref<Msg[]>([]);
const draft = ref('');
const log = ref<HTMLElement | null>(null);
const typing = ref(false);

const askCount = BOT_STATS.asks;

const now = () => new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });

function push(m: Msg) { msgs.value = [...msgs.value, m]; save(); scroll(); }

function save() {
  // 마지막 40건만 둔다 — 브라우저 저장 공간을 무한정 쓰지 않는다.
  try { localStorage.setItem(KEY, JSON.stringify(msgs.value.slice(-40))); } catch { /* noop */ }
}

async function scroll() {
  await nextTick();
  const el = log.value;
  if (el) el.scrollTop = el.scrollHeight;
}

function fromBot(r: BotReply) {
  push({ who: 'bot', text: r.text, suggestions: r.suggestions, link: r.link, at: now() });
}

function send(text?: string) {
  const t = (text ?? draft.value).trim();
  if (!t) return;
  push({ who: 'me', text: t, at: now() });
  draft.value = '';
  events.track('TALK_MESSAGE');

  // 곧바로 답이 튀어나오면 읽기 전에 화면이 넘어간다. 한 박자만 둔다.
  typing.value = true;
  window.setTimeout(() => {
    typing.value = false;
    const r = answer(t);
    fromBot(r);
    // 답하지 못한 질문만 남긴다(2026-09-04). 무엇을 더 적어야 하는지 추측
    // 대신 실측으로 정하려는 것이다. 답을 낸 질문은 이미 규칙이 있으니
    // 보내지 않는다 — 대화가 통째로 서버에 가는 것이 아니다.
    // 화면에서 누른 단추는 반드시 답이 있으므로 자연히 걸리지 않는다.
    if (isFallback(r)) {
      api.talkUnanswered(t).catch(() => { /* 기록 실패로 대화가 끊기면 안 된다 */ });
    }
  }, 320);
}

function clearAll() {
  msgs.value = [];
  try { localStorage.removeItem(KEY); } catch { /* noop */ }
  fromBot(opening());
}

/* 저장된 대화를 다시 읽을 때는 **한 줄 한 줄 모양을 확인한다.**
   배열이라는 것만 보고 넣었더니, 안에 null 이나 숫자가 섞인 경우
   `m.who` 를 읽다 예외가 났다(2026-09-03 점검에서 실제로 터졌다).
   저장소는 이용자·확장프로그램·옛 판이 언제든 건드릴 수 있는 곳이라
   "우리가 쓴 대로 있겠지"를 전제하면 안 된다. */
function readSaved(): Msg[] {
  let raw: string | null = null;
  try { raw = localStorage.getItem(KEY); } catch { return []; }
  if (!raw) return [];
  let parsed: unknown;
  try { parsed = JSON.parse(raw); } catch { return []; }
  if (!Array.isArray(parsed)) return [];
  return parsed.filter((m: any): m is Msg =>
    !!m && typeof m === 'object'
    && (m.who === 'bot' || m.who === 'me')
    && typeof m.text === 'string');
}

onMounted(() => {
  events.track('TALK_ENTER');
  msgs.value = readSaved();
  if (!msgs.value.length) fromBot(opening());
  else scroll();
});
</script>

<template>
  <div class="container room">
    <RoomHead
      no="03"
      eyebrow="정보 소통방"
      title="무엇이든 물어보세요"
      lead="진단·결과·신청처·개인정보처럼 이 서비스에 관한 것을 안내해 드립니다. 제가 확실히 아는 것만 답하고, 모르는 것은 모른다고 말씀드립니다."
    />

    <!-- 대화 — 말풍선은 상자를 쓰되, 이 화면에서 상자는 '누가 말했는가'를
         가르는 유일한 수단이라 여기서만 허용한다. 테두리 대신 면으로 가른다. -->
    <div ref="log" class="log" role="log" aria-live="polite" aria-label="안내봇과의 대화">
      <div v-for="(m, i) in msgs" :key="i" class="turn" :class="`turn--${m.who}`">
        <p class="turn__who">{{ m.who === 'bot' ? '곁 안내' : '나' }} <span class="turn__at">{{ m.at }}</span></p>
        <div class="bubble" :class="`bubble--${m.who}`">
          <p class="bubble__tx">{{ m.text }}</p>
          <RouterLink v-if="m.link" class="bubble__go" :to="m.link.to">{{ m.link.label }} →</RouterLink>
        </div>

        <!-- 빠른 답장 — 무엇을 물어도 되는지 몰라 첫 화면에서 멈추는 것을 막는다 -->
        <ul v-if="m.suggestions?.length && i === msgs.length - 1" class="quick">
          <li v-for="s in m.suggestions" :key="s">
            <button type="button" class="quick__b" @click="send(s)">{{ s }}</button>
          </li>
        </ul>
      </div>

      <p v-if="typing" class="typing" aria-hidden="true">곁 안내가 입력 중…</p>
    </div>

    <form class="ask" @submit.prevent="send()">
      <label class="sr" for="ask">궁금한 것을 적어 주세요</label>
      <input id="ask" v-model="draft" type="text" maxlength="200" autocomplete="off"
             placeholder="궁금한 것을 적어 주세요" />
      <button class="btn" type="submit" :disabled="!draft.trim()">보내기</button>
    </form>

    <!-- 무엇을 물어도 되는지 통째로 펼쳐 둔다. 대화창은 물어볼 거리가 떠오르지
         않으면 첫 화면에서 그대로 멈춘다 — 빠른 답장 넷만으로는 이 방이 무엇을
         아는지 가늠이 되지 않았다. 여기 적힌 것은 전부 답을 가진 질문이다. -->
    <section class="topics" aria-labelledby="topics-h">
      <h2 id="topics-h" class="topics__h2">
        이런 것들을 물어보실 수 있어요
        <span class="topics__n">{{ askCount }}가지</span>
      </h2>

      <!-- 묶음마다 접어 둔다. 102가지를 한 번에 펼치면 화면이 열 배로 길어져
           정작 대화창이 밀려난다. 처음 묶음만 펴서 어떤 모양인지 보여 준다. -->
      <details v-for="(g, gi) in TOPICS" :key="g.group" class="topics__g" :open="gi === 0">
        <summary class="topics__sum">
          {{ g.group }}<span class="topics__cnt">{{ g.items.length }}</span>
        </summary>
        <ul class="topics__ul">
          <li v-for="q in g.items" :key="q">
            <button type="button" class="quick__b" @click="send(q)">{{ q }}</button>
          </li>
        </ul>
      </details>
    </section>

    <p class="note">
      대화는 이 브라우저 안에만 남고 서버로 보내지 않습니다.
      복지 자격을 판정하지 않으며, 정확한 지원 여부는 기관에 확인해 주세요.
      <button class="linklike" type="button" @click="clearAll">대화 지우기</button>
    </p>

    <nav class="hop" aria-label="다른 방으로">
      <RouterLink class="hop__a" to="/diagnosis/start">부담감 진단</RouterLink>
      <RouterLink class="hop__a" to="/map">복지서비스 위치</RouterLink>
      <RouterLink class="hop__a" to="/reviews">이용 후기 소통방</RouterLink>
    </nav>
  </div>
</template>

<style scoped>
.log {
  border-top: 1px solid var(--hairline);
  border-bottom: 1px solid var(--hairline);
  padding: clamp(16px, 2.4vw, 28px) 0;
  /* 고정 높이를 쓰지 않는다(FR-040). 화면 높이에 따라 흐르되 상한만 둔다. */
  max-height: min(58vh, 620px);
  overflow-y: auto;
  overscroll-behavior: contain;
}
.turn + .turn { margin-top: clamp(14px, 2vw, 22px); }
.turn__who {
  margin: 0 0 6px; font-size: 12px; letter-spacing: .04em; color: var(--muted-soft);
}
.turn__at { margin-left: 6px; font-variant-numeric: tabular-nums; }
.turn--me { text-align: right; }

.bubble {
  display: inline-block; max-width: min(92%, 34em); text-align: left;
  padding: clamp(12px, 1.6vw, 16px) clamp(14px, 1.8vw, 18px);
  border-radius: 16px;
}
/* 안내봇 — 종이 위에 옅게 얹힌 면. 왼쪽 위만 각을 죽여 말꼬리를 만든다. */
.bubble--bot { background: var(--surface-soft); border-top-left-radius: 4px; }
/* 나 — 강조색 면. 글자는 먹색 그대로라 대비를 잃지 않는다. */
.bubble--me { background: var(--tertiary-tint); border-top-right-radius: 4px; }
.bubble__tx { margin: 0; white-space: pre-line; line-height: 1.65; color: var(--body); }
.bubble__go {
  display: inline-block; margin-top: 10px; font-weight: 700;
  color: var(--primary-on-tint); text-decoration: none; border-bottom: 1px solid currentColor;
}

.quick { list-style: none; display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0 0; padding: 0; }
.quick__b {
  min-height: 40px; padding: 8px 14px; font: inherit; font-size: 14px; cursor: pointer;
  background: none; border: 1px solid var(--hairline); border-radius: var(--radius-pill); color: var(--ink);
}
.quick__b:hover { background: var(--surface-soft); border-color: var(--border-strong); }

.typing { margin: 12px 0 0; font-size: 13px; color: var(--muted-soft); }

/* 물어볼 거리 목록 — 처음 온 사람에게 가장 필요한 것이 "무엇을 물어도 되는가"
   라서 화면에 둔다. 다만 102가지를 한꺼번에 펼치면 대화창이 저 위로 밀려나므로
   묶음마다 접고, 첫 묶음만 펴서 어떤 모양인지 보여 준다. */
.topics { margin-top: clamp(18px, 2.6vw, 28px); border-top: 1px solid var(--hairline); }
.topics__h2 {
  margin: clamp(14px, 1.8vw, 20px) 0 clamp(10px, 1.4vw, 14px);
  font-family: inherit; font-size: 15px; font-weight: 700; color: var(--ink); letter-spacing: 0;
}
.topics__n { margin-left: 8px; font-size: 13px; font-weight: 400; color: var(--muted-soft); }
.topics__g { border-top: 1px solid var(--hairline-soft); }
.topics__g:first-of-type { border-top: 0; }
.topics__sum {
  cursor: pointer; list-style: none;
  display: flex; align-items: center; gap: 8px;
  padding: 11px 0; min-height: 44px;
  font-size: 15px; color: var(--ink);
}
.topics__sum::-webkit-details-marker { display: none; }
.topics__sum::after { content: '▾'; margin-left: auto; color: var(--muted-soft); }
.topics__g[open] .topics__sum::after { content: '▴'; }
.topics__cnt {
  font-size: 12px; color: var(--muted-soft); font-variant-numeric: tabular-nums;
}
.topics__ul {
  list-style: none; display: flex; flex-wrap: wrap; gap: 8px;
  margin: 0 0 clamp(12px, 1.6vw, 18px); padding: 0;
}

.ask { display: flex; gap: var(--sp-sm); margin-top: clamp(14px, 2vw, 20px); }
.ask input {
  flex: 1; min-width: 0; padding: 12px var(--sp-md); font: inherit; min-height: 48px;
  background: var(--canvas); border: 1px solid var(--border-strong); border-radius: var(--radius-sm);
}
.ask .btn { flex: none; }

.note { margin: clamp(12px, 1.6vw, 18px) 0 0; font-size: 13px; color: var(--muted); line-height: 1.6; }
/* 문장 안에 섞인 글자 링크다. 한때 보이지 않는 44px 덮개(::after)로 표적을
   넓혔는데, 그 덮개가 **바로 위 선택지의 클릭을 가로채** 답이 안 골라졌다
   (2026-09-03 점검에서 잡음). 표적 크기 기준도 본문 속 인라인 링크는 예외로
   두는 쪽이라, 덮개를 걷고 글의 흐름을 지킨다. */
.linklike {
  background: none; border: 0; padding: 0;
  color: var(--link); text-decoration: underline; cursor: pointer; font: inherit;
}
.linklike { margin-left: 6px; font-size: 13px; }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
</style>
