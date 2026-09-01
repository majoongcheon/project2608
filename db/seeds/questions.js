// models/questions_v1.json → cb_question_v1 (FR-004a·FR-005)
//   문항 순서는 모델의 features 순서와 반드시 일치해야 한다.
//   어긋나면 백엔드가 기동 시 실패한다(modelLoader 정합 검증).
import fs from 'node:fs';
import path from 'node:path';
import { connect, ROOT, log, ok } from '../scripts/lib.js';

const src = path.join(ROOT, 'models', 'questions_v1.json');
if (!fs.existsSync(src)) {
  console.error(`모델 문항 파일이 없습니다: ${src}\n  → python3 ml/train.py all 을 먼저 실행하세요.`);
  process.exit(1);
}
const data = JSON.parse(fs.readFileSync(src, 'utf8'));
const v = data.question_set_version;

const con = await connect();
await con.query('DELETE FROM cb_question_v1 WHERE question_set_version = ?', [v]);

const rows = data.questions.map((q) => ([
  v, q.questionNo, q.feature, q.originalItem, q.text,
  JSON.stringify({ inputType: q.inputType, min: q.min, max: q.max, unit: q.unit, options: q.options }),
  q.hasNotApplicable ? 1 : 0, q.explainTemplate, 0,
]));

const sr = data.selfReport;
rows.push([
  v, 0, '__self_report__', sr.originalItem, sr.text,
  JSON.stringify({ inputType: sr.inputType, options: sr.options }), 0,
  '자가보고 부담 수준', 1,
]);

await con.query(
  `INSERT INTO cb_question_v1
     (question_set_version, question_no, feature, original_item, question_text,
      options_json, has_not_applicable, explain_template, is_self_report)
   VALUES ?`, [rows]);

log(`cb_question_v1 적재: ${rows.length}건 (문항 ${data.questions.length} + 자가보고 1)`);
ok(`문항 집합 버전 ${v}`);
for (const q of data.questions) ok(`  ${q.questionNo}. [${q.originalItem}] ${q.text.slice(0, 40)}...`);
await con.end();
