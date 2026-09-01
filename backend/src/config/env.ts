import dotenv from 'dotenv';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const ROOT = path.resolve(__dirname, '..', '..', '..');
dotenv.config({ path: path.join(ROOT, '.env') });

function req(key: string): string {
  const v = process.env[key];
  if (!v) throw new Error(`.env 에 ${key} 가 없습니다. .env.example 을 참고하세요.`);
  return v;
}

export const env = {
  db: {
    host: req('DB_HOST'),
    port: Number(process.env.DB_PORT || 3306),
    user: req('DB_USER'),
    password: req('DB_PASSWORD'),
    database: req('DB_NAME'),
    charset: process.env.DB_CHARSET || 'utf8mb4',
  },
  port: Number(process.env.BACKEND_PORT || 9523),
  publicOrigin: process.env.PUBLIC_ORIGIN || 'https://p3.sumzip.com',
  publicDomain: process.env.PUBLIC_DOMAIN || 'p3.sumzip.com',
  frontendPort: Number(process.env.FRONTEND_PORT || 9503),
  // FR-036: 제출자 구분용 해시의 솔트. 원본 IP 는 어디에도 저장하지 않는다.
  submitterSalt: process.env.SUBMITTER_SALT || 'dev-only-salt',
  modelsDir: path.join(ROOT, 'models'),
};
