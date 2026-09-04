// 데이터 정합 점검 — check_project.sh check 가 호출한다.
// research.md 0장 실측표 / quickstart 3장 기대값과 대조한다.
import { connect } from './lib.js';

const G = '\x1b[32m', R = '\x1b[31m', Y = '\x1b[33m', N = '\x1b[0m';
const ok = (m) => console.log(`  ${G}✓${N} ${m}`);
const bad = (m) => { console.log(`  ${R}✗${N} ${m}`); failed = true; };
const warn = (m) => console.log(`  ${Y}!${N} ${m}`);
let failed = false;

const con = await connect();
const q = async (sql, params) => (await con.query(sql, params))[0];

// 학습 데이터 (읽기 전용 — 변경되면 안 된다)
const [ds] = await q("SELECT COUNT(*) n, SUM(split='train') tr, SUM(split='test') te FROM cb_dataset_v1");
Number(ds.n) === 3000 ? ok(`cb_dataset_v1 ${ds.n}행`) : bad(`cb_dataset_v1 ${ds.n}행 (3000 기대)`);
Number(ds.tr) === 2398 && Number(ds.te) === 602
  ? ok(`분할 train ${ds.tr} / test ${ds.te}`) : bad(`분할 ${ds.tr}/${ds.te} (2398/602 기대)`);

const [fm] = await q('SELECT COUNT(*) n FROM cb_feature_meta_v1');
Number(fm.n) === 38 ? ok(`설명변수 ${fm.n}개`) : bad(`설명변수 ${fm.n}개 (38 기대)`);

// 운영 데이터
const [rg] = await q('SELECT COUNT(*) n, SUM(has_facility_data) h FROM cb_region_v1');
Number(rg.n) === 229 ? ok(`시군구 ${rg.n}개`) : bad(`시군구 ${rg.n}개 (229 기대)`);
Number(rg.h) === 221
  ? ok(`기관 데이터 확보 ${rg.h}개 (${(rg.h / rg.n * 100).toFixed(1)}%)`)
  : warn(`확보 ${rg.h}개 (221 기대)`);

const [fc] = await q('SELECT COUNT(*) n, SUM(phone IS NULL) np FROM cb_facility_v1');
Number(fc.n) > 0 ? ok(`기관 ${fc.n}건 · 전화번호 없음 ${fc.np}건`) : bad('기관 데이터 없음');

const svc = await q('SELECT service_type, COUNT(*) n FROM cb_facility_service_v1 GROUP BY service_type');
svc.length === 2
  ? ok(`서비스 ${svc.map((r) => `${r.service_type} ${r.n}`).join(' · ')}`)
  : bad(`서비스 유형 ${svc.length}종 (2 기대)`);

const [co] = await q("SELECT COUNT(*) n FROM cb_config_v1 WHERE version='v1'");
Number(co.n) >= 18 ? ok(`설정 ${co.n}건`) : bad(`설정 ${co.n}건 (18 이상 기대)`);

const [qn] = await q('SELECT COUNT(*) n, SUM(is_self_report) sr FROM cb_question_v1');
Number(qn.n) > 0 ? ok(`문항 ${qn.n - qn.sr}개 + 자가보고 ${qn.sr}개`) : bad('문항 없음 (seed:questions 필요)');

// FR-013c — 30건 미만 셀이 있으면 안 된다
const [rf] = await q('SELECT COUNT(*) n, MIN(n) mn FROM cb_reference_dist_v1');
Number(rf.n) > 0 && Number(rf.mn) >= 30
  ? ok(`참조 분포 ${rf.n}건 · 최소 셀 ${rf.mn} (>=30)`)
  : bad(`참조 분포 최소 셀 ${rf.mn} — 30 미만은 노출 금지 (FR-013c)`);

// FR-032 — 두 관측 저장소가 공통 컬럼을 갖지 않아야 한다
const cols = await q(`
  SELECT TABLE_NAME t, COLUMN_NAME c FROM information_schema.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE()
     AND TABLE_NAME IN ('cb_event_log_v1','cb_training_response_v1')`);
const a = new Set(cols.filter((r) => r.t === 'cb_event_log_v1').map((r) => r.c));
const b = new Set(cols.filter((r) => r.t === 'cb_training_response_v1').map((r) => r.c));
// FR-032 가 막으려는 것은 **개별 기록의 연결**이다.
// model_version·question_set_version 은 수천 건이 공유하는 저카디널리티 속성이라
// 어느 이벤트가 어느 응답인지 좁힐 수 없고, FR-027·FR-031 이 양쪽에 요구한 항목이다.
// 그 외의 공통 컬럼(세션 식별자·해시·토큰 등)은 연결 고리가 되므로 허용하지 않는다.
const LINK_SAFE = new Set(['model_version', 'question_set_version']);
const shared = [...a].filter((c) => b.has(c));
const linkable = shared.filter((c) => !LINK_SAFE.has(c));
if (linkable.length === 0) {
  ok(`저장소 분리: 연결 가능한 공통 컬럼 0개 (FR-032)${
    shared.length ? ` · 비연결 공통 속성 ${shared.join(', ')} 은 허용` : ''}`);
} else {
  bad(`저장소 분리 위반 — 기록을 연결할 수 있는 공통 컬럼: ${linkable.join(', ')}`);
}

// 2026-09-03 — 후기 소통방 테이블이 생기면서 그물 밖에 있던 곳을 메운다.
// 후기는 사람이 직접 쓴 글이라, 관측 저장소 어느 쪽과도 개별 기록을 이어
// 붙일 수 있는 컬럼을 가져서는 안 된다(원칙 III, FR-032 의 취지).
const rvCols = await q(`
  SELECT COLUMN_NAME c FROM information_schema.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cb_facility_review_v1'`);
if (rvCols.length) {
  const rv = new Set(rvCols.map((r) => r.c));
  const rvLinkable = [...rv].filter((c) => (a.has(c) || b.has(c)) && !LINK_SAFE.has(c));
  rvLinkable.length === 0
    ? ok('후기 저장소 분리: 관측 저장소와 연결 가능한 공통 컬럼 0개')
    : bad(`후기 저장소 분리 위반 — 공통 컬럼: ${rvLinkable.join(', ')}`);
}

// 2026-09-04 — 새로 생긴 두 저장소도 같은 그물에 넣는다.
//   cb_review_report_v1   신고. 신고자를 식별하지 않는다.
//   cb_talk_unanswered_v1 안내봇이 답하지 못한 질문. 사람이 직접 쓴 글이다.
// 둘 다 관측 저장소와 개별 기록을 이어 붙일 수 있는 컬럼을 가져서는 안 된다.
for (const t of ['cb_review_report_v1', 'cb_talk_unanswered_v1']) {
  const c = await q(`
    SELECT COLUMN_NAME c FROM information_schema.COLUMNS
     WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = ?`, [t]);
  if (!c.length) { bad(`${t} 테이블이 없습니다 — db/migrations/006 을 적용하세요`); continue; }
  const names = new Set(c.map((r) => r.c));
  const linkableHere = [...names].filter((n) => (a.has(n) || b.has(n)) && !LINK_SAFE.has(n));
  linkableHere.length === 0
    ? ok(`${t} 분리: 관측 저장소와 연결 가능한 공통 컬럼 0개`)
    : bad(`${t} 분리 위반 — 공통 컬럼: ${linkableHere.join(', ')}`);
}

// 미답변 질문에는 사람이 알아볼 수 있는 정보가 남으면 안 된다.
// 백엔드가 막고 있지만, 막는 쪽이 고장 나도 여기서 걸리게 둔다.
const [tu] = await q(`SELECT COUNT(*) n FROM cb_talk_unanswered_v1
                       WHERE text REGEXP '01[0-9]{1}[- .]?[0-9]{3,4}[- .]?[0-9]{4}'
                          OR text REGEXP '[[:alnum:]._+-]+@[[:alnum:].-]+'`);
Number(tu.n) === 0
  ? ok('미답변 질문에 연락처 꼴 0건')
  : bad(`미답변 질문에 연락처로 보이는 글이 있습니다: ${tu.n}건`);

// 시각으로도 짝지을 수 없어야 한다 — 학습 저장소는 초 단위로 절삭해 저장한다.
const [ts] = await q(`SELECT COUNT(*) n FROM cb_training_response_v1
                       WHERE MICROSECOND(submitted_at) <> 0`);
Number(ts.n) === 0
  ? ok('학습 저장소 제출 시각이 초 단위로 절삭됨 (시각 대조 방지)')
  : bad(`제출 시각에 마이크로초가 남아 있습니다: ${ts.n}건`);

// FR-028 — 익명 로그에 금지 컬럼이 없어야 한다
const banned = ['ip', 'ip_address', 'nickname', 'answers_json', 'lat', 'lng', 'care_target_age'];
const found = banned.filter((c) => a.has(c));
found.length === 0 ? ok('익명 로그에 금지 항목 컬럼 없음 (FR-028)') : bad(`금지 컬럼 존재: ${found.join(', ')}`);

await con.end();
process.exit(failed ? 1 : 0);
