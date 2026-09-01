import fs from 'node:fs';
import path from 'node:path';
import { connect, ROOT, log, ok } from './lib.js';

const dir = path.join(ROOT, 'db', 'migrations');
const files = fs.readdirSync(dir).filter((f) => f.endsWith('.sql')).sort();

const con = await connect();
log(`마이그레이션 ${files.length}개 실행`);
for (const f of files) {
  const sql = fs.readFileSync(path.join(dir, f), 'utf8');
  await con.query(sql);
  ok(f);
}
const [rows] = await con.query(
  "SELECT TABLE_NAME t FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME LIKE 'cb\\_%' ORDER BY TABLE_NAME"
);
log(`\ncb_ 테이블 ${rows.length}개: ${rows.map((r) => r.t).join(', ')}`);
await con.end();
