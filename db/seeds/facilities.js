// services_with_coords_std09 → cb_facility_v1 + cb_facility_service_v1 (research.md R-8)
//  - 한글 컬럼을 영문 스키마로 매핑
//  - 사업유형을 코드값으로 (DAY_ACTIVITY / AFTERSCHOOL_YOUTH)
//  - 전화번호 결측·형식오류는 빈 문자열이 아니라 NULL (FR-018 분기를 명확히 하기 위해)
//  - 같은 기관이 두 유형을 제공하면 기관 1행 + 서비스 2행으로 분리
import { connect, log, ok, warn } from '../scripts/lib.js';

const TYPE_MAP = {
  '발달장애인 주간활동서비스': 'DAY_ACTIVITY',
  '청소년 발달장애인 방과후활동서비스': 'AFTERSCHOOL_YOUTH',
};

// 국내 전화번호로 볼 수 있는 최소 형태. 숫자 9~11자리를 만족해야 통화 연결이 가능하다.
function normalizePhone(raw) {
  if (raw == null) return null;
  const digits = String(raw).replace(/[^0-9]/g, '');
  if (digits.length < 9 || digits.length > 11) return null;
  return String(raw).trim();
}

const con = await connect();

const [rows] = await con.query(`
  SELECT 시도 AS sido,
         NULLIF(TRIM(REPLACE(시군구, 시도, '')), '') AS sigungu,
         제공기관_명 AS name, 사업명 AS program, 사업유형 AS stype,
         전화번호 AS phone, 주소 AS addr, 주소_상세 AS addr2, full_addr, lat, lng
    FROM services_with_coords_std09
   WHERE lat IS NOT NULL AND lng IS NOT NULL`);
log(`원천 ${rows.length}건 조회`);

const [regions] = await con.query('SELECT region_code, sido_name, sigungu_name FROM cb_region_v1');
const regionMap = new Map(regions.map((r) => [`${r.sido_name}|${r.sigungu_name}`, r.region_code]));

// 같은 기관을 (이름 + 좌표)로 식별해 묶는다. 유형만 다른 중복 행을 한 기관으로 만든다.
const facilities = new Map();
let unmapped = 0, badType = 0;
for (const r of rows) {
  const sigungu = r.sigungu ?? r.sido;
  const regionCode = regionMap.get(`${r.sido}|${sigungu}`) ?? null;
  if (!regionCode) unmapped++;
  const serviceType = TYPE_MAP[String(r.stype || '').trim()];
  if (!serviceType) { badType++; continue; }

  const key = `${String(r.name).trim()}|${Number(r.lat).toFixed(6)}|${Number(r.lng).toFixed(6)}`;
  if (!facilities.has(key)) {
    facilities.set(key, {
      regionCode,
      name: String(r.name).trim().slice(0, 160),
      address: (r.full_addr || r.addr || '').trim().slice(0, 255) || null,
      addressDetail: (r.addr2 || '').trim().slice(0, 255) || null,
      phone: normalizePhone(r.phone),
      lat: Number(r.lat), lng: Number(r.lng),
      services: new Map(),
    });
  }
  const f = facilities.get(key);
  if (!f.phone) f.phone = normalizePhone(r.phone);       // 유형별 행 중 하나에만 번호가 있을 수 있다
  if (!f.services.has(serviceType)) {
    f.services.set(serviceType, (r.program || '').trim().slice(0, 160) || null);
  }
}

await con.query('DELETE FROM cb_facility_service_v1');
await con.query('DELETE FROM cb_facility_v1');
await con.query('ALTER TABLE cb_facility_v1 AUTO_INCREMENT = 1');

const today = new Date().toISOString().slice(0, 10);
const batch = `src-${today}`;
const list = [...facilities.values()];
const facRows = list.map((f) => [f.regionCode, f.name, f.address, f.addressDetail, f.phone, f.lat, f.lng, today, batch]);

await con.query(
  `INSERT INTO cb_facility_v1 (region_code, name, address, address_detail, phone, lat, lng, updated_at, source_batch)
   VALUES ?`, [facRows]);

const [inserted] = await con.query(
  'SELECT facility_id, name, lat, lng FROM cb_facility_v1 ORDER BY facility_id');
const idMap = new Map(inserted.map((r) => [`${r.name}|${Number(r.lat).toFixed(6)}|${Number(r.lng).toFixed(6)}`, r.facility_id]));

const svcRows = [];
for (const [key, f] of facilities) {
  const id = idMap.get(key);
  if (!id) continue;
  for (const [type, program] of f.services) svcRows.push([id, type, program]);
}
await con.query(
  'INSERT INTO cb_facility_service_v1 (facility_id, service_type, program_name) VALUES ?', [svcRows]);

// has_facility_data 갱신
await con.query('UPDATE cb_region_v1 SET has_facility_data = 0');
await con.query(`
  UPDATE cb_region_v1 r
     SET has_facility_data = 1
   WHERE EXISTS (SELECT 1 FROM cb_facility_v1 f WHERE f.region_code = r.region_code)`);

log('');
ok(`cb_facility_v1        ${facRows.length}건 (원천 ${rows.length}행에서 기관 단위로 묶음)`);
ok(`cb_facility_service_v1 ${svcRows.length}건`);
if (unmapped) warn(`지역 코드 미매핑 ${unmapped}건`);
if (badType) warn(`알 수 없는 사업유형 ${badType}건 — 제외됨`);

const [[c1]] = await con.query('SELECT COUNT(*) n FROM cb_facility_v1 WHERE phone IS NULL');
const [[c2]] = await con.query('SELECT COUNT(*) n FROM cb_region_v1 WHERE has_facility_data = 1');
const [c3] = await con.query('SELECT service_type, COUNT(*) n FROM cb_facility_service_v1 GROUP BY service_type');
ok(`전화번호 없음 ${c1.n}건 · 데이터 확보 시군구 ${c2.n}개`);
for (const r of c3) ok(`  ${r.service_type}: ${r.n}건`);

await con.end();
