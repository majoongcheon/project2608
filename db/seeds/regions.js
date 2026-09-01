// 전국 229개 시군구 적재 (FR-016a·FR-016b)
//
// region_code = 행정표준 시도코드(2) + 프로젝트 부여 일련번호(3).
//   시도 접두는 행정안전부 표준이며, 뒤 3자리는 가나다순 일련번호다(법정동코드가 아님).
// center_lat/lng = 해당 시군구 기관 좌표의 평균. 기관이 없는 8개 지역은
//   소속 시도의 기관 좌표 평균으로 대체한다(범위 확대 시 인접 기관 탐색이 가능하도록).
import { connect, log, ok, warn } from '../scripts/lib.js';

const SIDO = {
  '서울특별시': '11', '부산광역시': '26', '대구광역시': '27', '인천광역시': '28',
  '광주광역시': '29', '대전광역시': '30', '울산광역시': '31', '세종특별자치시': '36',
  '경기도': '41', '강원특별자치도': '51', '충청북도': '43', '충청남도': '44',
  '전북특별자치도': '52', '전라남도': '46', '경상북도': '47', '경상남도': '48',
  '제주특별자치도': '50',
};

// 229개 기초자치단체 (2024 기준. 군위군 대구 편입 반영, 제주 2개 행정시 포함)
const REGIONS = {
  '서울특별시': ['강남구','강동구','강북구','강서구','관악구','광진구','구로구','금천구','노원구','도봉구','동대문구','동작구','마포구','서대문구','서초구','성동구','성북구','송파구','양천구','영등포구','용산구','은평구','종로구','중구','중랑구'],
  '부산광역시': ['강서구','금정구','기장군','남구','동구','동래구','부산진구','북구','사상구','사하구','서구','수영구','연제구','영도구','중구','해운대구'],
  '대구광역시': ['남구','달서구','달성군','동구','북구','서구','수성구','중구','군위군'],
  '인천광역시': ['계양구','남동구','동구','미추홀구','부평구','서구','연수구','중구','강화군','옹진군'],
  '광주광역시': ['광산구','남구','동구','북구','서구'],
  '대전광역시': ['대덕구','동구','서구','유성구','중구'],
  '울산광역시': ['남구','동구','북구','중구','울주군'],
  '세종특별자치시': ['세종특별자치시'],
  '경기도': ['고양시','과천시','광명시','광주시','구리시','군포시','김포시','남양주시','동두천시','부천시','성남시','수원시','시흥시','안산시','안성시','안양시','양주시','양평군','여주시','연천군','용인시','의왕시','의정부시','이천시','파주시','평택시','포천시','하남시','화성시','오산시','가평군'],
  '강원특별자치도': ['강릉시','고성군','동해시','삼척시','속초시','양구군','양양군','영월군','원주시','인제군','정선군','철원군','춘천시','태백시','평창군','홍천군','화천군','횡성군'],
  '충청북도': ['괴산군','단양군','보은군','영동군','옥천군','음성군','제천시','증평군','진천군','청주시','충주시'],
  '충청남도': ['계룡시','공주시','금산군','논산시','당진시','보령시','부여군','서산시','서천군','아산시','예산군','천안시','청양군','태안군','홍성군'],
  '전북특별자치도': ['고창군','군산시','김제시','남원시','무주군','부안군','순창군','완주군','익산시','임실군','장수군','전주시','정읍시','진안군'],
  '전라남도': ['강진군','고흥군','곡성군','광양시','구례군','나주시','담양군','목포시','무안군','보성군','순천시','신안군','여수시','영광군','영암군','완도군','장흥군','진도군','함평군','해남군','화순군','장성군'],
  '경상북도': ['경산시','경주시','구미시','김천시','문경시','봉화군','상주시','성주군','안동시','영덕군','영양군','영주시','영천시','예천군','울진군','의성군','청도군','청송군','칠곡군','포항시','고령군','울릉군'],
  '경상남도': ['거제시','거창군','고성군','김해시','남해군','밀양시','사천시','산청군','양산시','의령군','진주시','창녕군','창원시','통영시','하동군','함안군','함양군','합천군'],
  '제주특별자치도': ['서귀포시','제주시'],
};

const con = await connect();

// 원천 데이터의 시군구별 기관 좌표 평균과 건수
const [srcRows] = await con.query(`
  SELECT 시도 AS sido,
         NULLIF(TRIM(REPLACE(시군구, 시도, '')), '') AS sigungu,
         AVG(lat) AS clat, AVG(lng) AS clng, COUNT(*) AS n
    FROM services_with_coords_std09
   WHERE lat IS NOT NULL AND lng IS NOT NULL
   GROUP BY 시도, NULLIF(TRIM(REPLACE(시군구, 시도, '')), '')`);
// 세종처럼 시군구명이 시도명과 같아 빈 값이 되는 경우 시도명으로 되돌린다
const srcMap = new Map(srcRows.map((r) => [`${r.sido}|${r.sigungu ?? r.sido}`, r]));

const [sidoRows] = await con.query(
  `SELECT 시도 AS sido, AVG(lat) AS clat, AVG(lng) AS clng FROM services_with_coords_std09 GROUP BY 시도`);
const sidoMap = new Map(sidoRows.map((r) => [r.sido, r]));

const rows = [];
const missing = [];
for (const [sido, list] of Object.entries(REGIONS)) {
  const prefix = SIDO[sido];
  const sorted = [...list].sort((a, b) => a.localeCompare(b, 'ko'));
  sorted.forEach((name, i) => {
    const code = prefix + String(i + 1).padStart(3, '0');
    const hit = srcMap.get(`${sido}|${name}`);
    const fallback = sidoMap.get(sido);
    const has = hit ? 1 : 0;
    if (!has) missing.push(`${sido} ${name}`);
    rows.push([
      code, sido, name,
      hit ? Number(hit.clat) : (fallback ? Number(fallback.clat) : null),
      hit ? Number(hit.clng) : (fallback ? Number(fallback.clng) : null),
      has,
      has ? null : `${sido} 장애인복지 담당부서`,
      null,
    ]);
  });
}

await con.query('DELETE FROM cb_region_v1');
await con.query(
  `INSERT INTO cb_region_v1
     (region_code, sido_name, sigungu_name, center_lat, center_lng, has_facility_data,
      metro_contact_name, metro_contact_phone)
   VALUES ?`, [rows]);

log(`cb_region_v1 적재: ${rows.length}건`);
const [[chk]] = await con.query(
  'SELECT COUNT(*) total, SUM(has_facility_data) has_data FROM cb_region_v1');
ok(`전체 ${chk.total}개 · 기관 데이터 확보 ${chk.has_data}개 (${(chk.has_data / chk.total * 100).toFixed(1)}%)`);

if (Number(chk.total) !== 229) throw new Error(`시군구 수가 229가 아닙니다: ${chk.total}`);
warn(`미확보 ${missing.length}개: ${missing.join(', ')}`);

// 원천에 있는데 표준 목록에 없는 이름 = 표기 불일치 탐지
const known = new Set(rows.map((r) => `${r[1]}|${r[2]}`));
const orphan = [...srcMap.keys()].filter((k) => !known.has(k));
if (orphan.length) warn(`표준 목록에 없는 원천 표기 ${orphan.length}건: ${orphan.join(', ')}`);
else ok('원천 시군구 표기가 모두 표준 목록과 일치');

await con.end();
