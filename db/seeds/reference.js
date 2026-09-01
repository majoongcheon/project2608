// cb_reference_dist_v1 — 참조 집단 분포 (FR-013a~c-1)
//   ★ 셀 30건 미만은 적재 자체를 하지 않는다. 런타임에서 실수로 노출할 여지를 없앤다.
//   ★ 교차표는 만들지 않는다 — dist_type 은 부담 구간 또는 단일 문항 응답 범주 둘뿐이다.
import { connect, log, ok, warn } from '../scripts/lib.js';

const MIN_CELL = 30;
const con = await connect();

const [features] = await con.query('SELECT feature FROM cb_feature_meta_v1 ORDER BY feature');
const rows = [];

// (1) 전체 부담 구간 분포 — 실태조사 3,000가구 전체 기준
const [levels] = await con.query(
  'SELECT care_burden lv, COUNT(*) n FROM cb_dataset_v1 GROUP BY care_burden ORDER BY care_burden');
const total = levels.reduce((s, r) => s + Number(r.n), 0);
for (const r of levels) {
  if (Number(r.n) < MIN_CELL) { warn(`부담 구간 ${r.lv} 표본 ${r.n}건 — 30 미만이라 제외`); continue; }
  rows.push(['BURDEN_LEVEL', null, r.lv, r.n, (Number(r.n) / total * 100).toFixed(2)]);
}

// (2) 개별 문항의 단일 응답 범주 분포
let dropped = 0;
for (const { feature } of features) {
  const [cats] = await con.query(
    `SELECT \`${feature}\` v, COUNT(*) n FROM cb_dataset_v1 WHERE \`${feature}\` IS NOT NULL GROUP BY \`${feature}\``);
  const sub = cats.reduce((s, r) => s + Number(r.n), 0);
  for (const c of cats) {
    if (Number(c.n) < MIN_CELL) { dropped++; continue; }
    rows.push(['FEATURE_CATEGORY', feature, c.v, c.n, (Number(c.n) / sub * 100).toFixed(2)]);
  }
}

await con.query('DELETE FROM cb_reference_dist_v1');
await con.query(
  'INSERT INTO cb_reference_dist_v1 (dist_type, feature, category_value, n, pct) VALUES ?', [rows]);

log(`cb_reference_dist_v1 적재: ${rows.length}건`);
ok(`부담 구간 ${rows.filter((r) => r[0] === 'BURDEN_LEVEL').length}개`);
ok(`문항 응답 범주 ${rows.filter((r) => r[0] === 'FEATURE_CATEGORY').length}개`);
warn(`표본 ${MIN_CELL}건 미만이라 제외한 범주 ${dropped}개 (FR-013c)`);
const [[m]] = await con.query('SELECT MIN(n) minN FROM cb_reference_dist_v1');
ok(`최소 셀 크기 ${m.minN} (>= ${MIN_CELL} 이어야 함)`);
await con.end();
