import mysql from 'mysql2/promise';
import dotenv from 'dotenv';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const ROOT = path.resolve(__dirname, '..', '..');
dotenv.config({ path: path.join(ROOT, '.env') });

export async function connect() {
  const need = ['DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME'];
  const missing = need.filter((k) => !process.env[k]);
  if (missing.length) {
    throw new Error(`.env 에 다음 값이 없습니다: ${missing.join(', ')} — .env.example 을 참고하세요.`);
  }
  return mysql.createConnection({
    host: process.env.DB_HOST,
    port: Number(process.env.DB_PORT || 3306),
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    database: process.env.DB_NAME,
    charset: process.env.DB_CHARSET || 'utf8mb4',
    multipleStatements: true,
  });
}

export const log = (...a) => console.log(...a);
export const ok = (m) => console.log(`  ✓ ${m}`);
export const warn = (m) => console.log(`  ! ${m}`);
