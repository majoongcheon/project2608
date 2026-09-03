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
import { answer, opening, TOPICS, type BotReply } from '../services/guideBot';
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
  window.setTimeout(() => { typing.value = false; fromBot(answer(t)); }, 320);
}

function clearAll() {
  msgs.value = [];
  try { localStorage.removeItem(KEY); } catch { /* noop */ }
  fromBot(opening());
}

onMounted(() => {
  let saved: Msg[] = [];
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) saved = JSON.parse(raw);
  } catch { /* 저장 공간을 못 쓰면 새 대화로 시작한다 */ }
  msgs.value = Array.isArray(saved) ? saved : [];
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
    <details class="topics" open>
      <summary class="topics__sum">이런 것들을 물어보실 수 있어요</summary>
      <div class="topics__body">
        <section v-for="g in TOPICS" :key="g.group" class="topics__g">
          <h2 class="topics__h">{{ g.group }}</h2>
          <ul class="topics__ul">
            <li v-for="q in g.items" :key="q">
              <button type="button" class="quick__b" @click="send(q)">{{ q }}</button>
            </li>
          </ul>
        </section>
      </div>
    </details>

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

/* 물어볼 거리 목록 — 접을 수 있게 두되 처음에는 펴 둔다. 처음 온 사람에게
   가장 필요한 것이 "무엇을 물어도 되는가" 이기 때문이다. */
.topics { margin-top: clamp(16px, 2.4vw, 26px); border-top: 1px solid var(--hairline); }
.topics__sum {
  cursor: pointer; list-style: none; padding: clamp(12px, 1.6vw, 16px) 0;
  font-size: 15px; font-weight: 700; color: var(--ink);
}
.topics__sum::-webkit-details-marker { display: none; }
.topics__sum::after { content: ' ▾'; color: var(--muted-soft); font-weight: 400; }
.topics[open] .topics__sum::after { content: ' ▴'; }
.topics__body { padding-bottom: clamp(8px, 1.2vw, 14px); }
.topics__g + .topics__g { margin-top: clamp(14px, 1.8vw, 20px); }
.topics__h {
  margin: 0 0 8px; font-family: inherit; font-size: 13px; font-weight: 700;
  letter-spacing: .06em; color: var(--muted);
}
.topics__ul { list-style: none; display: flex; flex-wrap: wrap; gap: 8px; margin: 0; padding: 0; }

.ask { display: flex; gap: var(--sp-sm); margin-top: clamp(14px, 2vw, 20px); }
.ask input {
  flex: 1; min-width: 0; padding: 12px var(--sp-md); font: inherit; min-height: 48px;
  background: var(--canvas); border: 1px solid var(--border-strong); border-radius: var(--radius-sm);
}
.ask .btn { flex: none; }

.note { margin: clamp(12px, 1.6vw, 18px) 0 0; font-size: 13px; color: var(--muted); line-height: 1.6; }
.linklike {
  background: none; border: 0; padding: 0; margin-left: 6px;
  color: var(--link); text-decoration: underline; cursor: pointer; font: inherit; font-size: 13px;
}
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
</style>
