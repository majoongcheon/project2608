// cb_config_v1 — FR-022 가 열거한 외부화 설정 (원칙 IV)
//
//   학습으로 산출되는 값은 models/*.json 에서 직접 읽는다.
//   여기에 숫자를 손으로 적어두면 재학습 후 갱신을 잊어 운영값과 모델값이 갈라진다.
//   (2026-09-01 실제로 그렇게 어긋나 있었다: tauConf 0.34 vs 0.3239, minThreshold 0.01 vs 0.1325)
import fs from 'node:fs';
import path from 'node:path';
import { connect, ROOT, log, ok } from '../scripts/lib.js';

const MODELS = path.join(ROOT, process.env.CB_MODELS_DIR || 'models');
function readModel(name) {
  const f = path.join(MODELS, name);
  if (!fs.existsSync(f)) {
    console.error(`모델 산출물이 없습니다: ${f}\n  → python3 ml/train.py build 를 먼저 실행하세요.`);
    process.exit(1);
  }
  return JSON.parse(fs.readFileSync(f, 'utf8'));
}
const UNC     = readModel('uncertainty_v1.json');
const CONTRIB = readModel('contribution_v1.json');

const CONFIG = {
  // 연계 (FR-021·FR-021e·FR-021f)
  'referral.threshold':            { maxInternalLabel: 2, note: '내부 라벨 이하면 즉시 안내. 1=최고부담이라 비교는 <=' },
  'referral.counselingThreshold':  { maxInternalLabel: 1 },
  'referral.facilityCount':        { count: 3 },
  'referral.radiusStepsKm':        { steps: [10, 20, 50] },

  // 연령 (FR-021h·FR-021i-1·FR-021i-3)
  'age.mappingBoundary':           { boundary: 18 },
  'age.serviceRanges': {
    AFTERSCHOOL_YOUTH: { min: 6,  max: 17, label: '만 6~17세 청소년' },
    DAY_ACTIVITY:      { min: 18, max: 64, label: '만 18~64세 성인' },
  },
  'age.outOfRangeNotice': {
    under: { threshold: 6,  notice: '입력하신 나이는 두 서비스의 이용 대상 연령 범위보다 어립니다.',
             alternativeContact: '발달재활서비스 — 거주지 주민센터로 문의하세요.' },
    over:  { threshold: 65, notice: '입력하신 나이는 두 서비스의 이용 대상 연령 범위를 넘습니다.',
             alternativeContact: '노인장기요양보험(국민건강보험공단 1577-1000) 및 지역 발달장애인지원센터로 문의하세요.' },
  },

  // 판정 (FR-009c·FR-021j-1·FR-011-1)
  'undecidable.thresholds': {
    tauConf: UNC.tau_conf, tauDens: UNC.tau_dens,
    source: `models/uncertainty_v1.json (${UNC.model_version})`,
  },
  'undecidable.noticeText': {
    text: '현재 응답만으로는 돌봄부담 수준을 정확히 판단하기 어렵습니다. 다만 필요한 지원을 놓치지 않도록 가까운 상담·서비스 기관을 안내합니다.',
    note: '판정 불가는 고부담군 판정이 아니다. 안전망 목적임을 밝힌다 (FR-021j-1)',
  },
  'contribution.minThreshold': {
    value: CONTRIB.min_threshold,
    source: `models/contribution_v1.json — ${CONTRIB.basis}`,
  },

  // 자가보고 (FR-008d)
  'selfreport.noticeText': {
    text: '이 질문은 앞으로 진단 정확도를 개선하기 위한 검증 목적으로 사용됩니다. 현재 결과 계산에는 반영되지 않습니다.',
  },

  // 표시 명칭 (FR-010a) — 내부 라벨 1=최고부담 역방향 척도
  'burden.labels': {
    1: { label: '최고부담군', warning: true,  description: '돌봄 부담이 매우 큰 상태로 보입니다. 혼자 감당하기 어려운 수준일 수 있습니다.' },
    2: { label: '고부담군',   warning: true,  description: '돌봄 부담이 큰 상태로 보입니다. 이용할 수 있는 지원을 함께 확인해 보세요.' },
    3: { label: '중간부담군', warning: false, description: '돌봄 부담이 중간 정도로 보입니다.' },
    4: { label: '저부담군',   warning: false, description: '돌봄 부담이 비교적 크지 않은 상태로 보입니다.' },
    5: { label: '부담 없음',  warning: false, description: '현재는 돌봄 부담을 크게 느끼지 않는 상태로 보입니다.' },
  },

  // 클라이언트 상태·제출 제어 (FR-008-2·FR-036c)
  'draft.expiryHours':             { hours: 24 },
  'submit.rateLimit':              { windowMinutes: 10, maxSubmissions: 5, note: '자동 차단이 아니라 플래그만 기록 (FR-036a)' },

  // 고지 문구 (FR-013·FR-012b·FR-025)
  'notice.disclaimer':             { text: '이 결과는 참고 정보이며 공식 복지 자격 판정이 아닙니다. 실제 서비스 이용 가능 여부는 관할 기관에서 확인해 주세요.' },
  'notice.modelChange':            { text: '진단 모델이 갱신되면 같은 응답이라도 결과가 달라질 수 있습니다.' },
  'notice.cancelWindow':           { text: '결과 화면을 벗어나기 전까지 저장을 취소할 수 있습니다. 저장된 응답은 익명이라 이후에는 특정할 수 없습니다.' },
  'notice.multipleTargets':        { text: '돌봄 대상이 2인 이상이라고 응답하셨습니다. 이 진단은 지정하신 한 분을 기준으로 산출되어, 실제 돌봄부담은 결과보다 높을 수 있습니다.' },
};

const con = await connect();
const rows = Object.entries(CONFIG).map(([k, v]) => [k, 'v1', JSON.stringify(v)]);
await con.query('DELETE FROM cb_config_v1');
await con.query('INSERT INTO cb_config_v1 (config_key, version, value_json) VALUES ?', [rows]);
log(`cb_config_v1 적재: ${rows.length}건`);
log(`  모델 산출값 반영: tauConf ${UNC.tau_conf} · tauDens ${UNC.tau_dens} · minThreshold ${CONTRIB.min_threshold}`);
for (const [k] of rows) ok(k);
await con.end();
