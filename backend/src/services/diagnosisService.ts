// 판정 → 기여 요인 → 참조 비교 조립 (FR-009 ~ FR-013d)
//   ★ 내부 라벨(1~5)은 응답 본문에 넣지 않는다. 표시 명칭만 내보낸다(FR-010a, 원칙 II).
import { getArtifacts } from '../inference/modelLoader.js';
import { cfg } from '../config/configStore.js';
import { query } from '../repositories/pool.js';
import { buildReferral, type ImmediateReferral } from './referralService.js';
import { callInference, type InferenceResult } from './inferenceClient.js';

export interface AnswerInput { questionNo: number; value: number | null }

export interface DiagnosisOutput {
  decided: boolean;
  internalLabel: number | null;          // 내부 전용. API 응답에서 제거된다.
  burdenLabel: string | null;
  burdenDescription: string | null;
  isWarning: boolean;
  contributions: { text: string; isMinor: boolean }[] | null;
  comparison: { text: string; userValue: string; referencePct: number }[] | null;
  undecidableNotice: string | null;
  // FR-009a — 판정이 어렵다는 사실만이 아니라 **그 이유**까지 보호자의 말로 전한다.
  //   추론 서비스가 주는 undecidableReason(sparse|ambiguous)을 설정의 문구로 옮긴다.
  //   설정에 문구가 아직 없으면 null 이 되어 화면에서 그 줄만 빠진다(예전 화면과 같아진다).
  undecidableReasonText: string | null;
  undecidableMeaning: string | null;      // '부담 없음'으로 읽히는 것을 막는다
  undecidableNextSteps: string[] | null;  // 답을 고쳐 다시 하라는 뜻으로 읽히지 않게 쓴다
  // 추론 서비스에 연결하지 못한 경우. 판정 불가와 다르다 — 부담 수준과 무관한 장애다.
  unavailable: boolean;
  unavailableNotice: string | null;
  multipleTargetsNotice: string | null;
  immediateReferral: ImmediateReferral | null;
  modelVersion: string | null;
  disclaimer: string;
}

/** 문항 응답을 모델 입력 벡터로. "해당사항 없음"(null)은 결측 센티널이 된다(FR-004d). */
export function toFeatureVector(answers: AnswerInput[]): number[] {
  const { model, questions } = getArtifacts();
  const byNo = new Map(answers.map((a) => [a.questionNo, a.value]));
  return (questions.questions as any[]).map((q) => {
    const v = byNo.get(q.questionNo);
    return v === null || v === undefined ? model.missing_sentinel : Number(v);
  });
}

/** 미응답 문항 번호 (FR-007). "해당사항 없음"은 응답으로 친다. */
export function findUnanswered(answers: AnswerInput[]): number[] {
  const { questions } = getArtifacts();
  const answered = new Set(answers.map((a) => a.questionNo));
  return (questions.questions as any[])
    .filter((q) => !answered.has(q.questionNo))
    .map((q) => q.questionNo);
}

async function buildComparison(row: number[], internalLabel: number | null, topFeatures: string[]) {
  // FR-013b: (1) 전체 부담 구간 분포에서의 위치 (2) 기여 요인 문항의 응답 분포 비교
  // FR-013c: 30건 미만 셀은 애초에 테이블에 없다. 교차표는 만들 수 없는 구조다(FR-013c-1).
  const { model, questions } = getArtifacts();
  const out: { text: string; userValue: string; referencePct: number }[] = [];

  if (internalLabel !== null) {
    const r = await query<{ pct: number }>(
      "SELECT pct FROM cb_reference_dist_v1 WHERE dist_type='BURDEN_LEVEL' AND category_value = ?",
      [internalLabel]);
    if (r.length) {
      const labels = cfg<any>('burden.labels');
      out.push({
        text: `전국 조사에 참여한 보호자 중 ${r[0].pct}%가 같은 구간에 속합니다.`,
        userValue: labels[String(internalLabel)]?.label ?? '',
        referencePct: Number(r[0].pct),
      });
    }
  }

  for (const feature of topFeatures) {
    const j = model.features.indexOf(feature);
    if (j < 0) continue;
    const value = row[j];
    if (value === model.missing_sentinel) continue;
    const r = await query<{ pct: number }>(
      "SELECT pct FROM cb_reference_dist_v1 WHERE dist_type='FEATURE_CATEGORY' AND feature = ? AND category_value = ?",
      [feature, value]);
    if (!r.length) continue;                       // 30건 미만이면 비교를 생략한다
    const q = (questions.questions as any[]).find((x) => x.feature === feature);
    const opt = q?.options?.find((o: any) => o.value === value);
    out.push({
      text: `"${q?.text ?? feature}" 문항에서 같은 응답을 한 보호자는 ${r[0].pct}%입니다.`,
      userValue: opt?.label ?? String(value),
      referencePct: Number(r[0].pct),
    });
  }
  return out;
}

export async function diagnose(params: {
  answers: AnswerInput[];
  careTargetAge: number | null;
  multipleCareTargets: boolean | null;
  lat: number | null; lng: number | null; regionCode: string | null;
}): Promise<DiagnosisOutput> {
  const { model, questions } = getArtifacts();
  const row = toFeatureVector(params.answers);

  // 판정 정책은 설정이 소유한다(FR-009c). 파이썬은 상태 없는 계산기이고, 기준은 여기서 준다.
  const tau = cfg<{ tauConf: number; tauDens: number }>('undecidable.thresholds');
  const weights = cfg<{ weights: number[] }>('model.decisionWeights').weights;
  const contributionThreshold = cfg<{ value: number }>('contribution.minThreshold').value;

  // 판정은 파이썬 추론 서비스가 한다. 실패해도 예외가 오지 않는다 — 값으로 온다.
  const outcome = await callInference({
    answers: params.answers,
    policy: {
      tauConf: tau.tauConf, tauDens: tau.tauDens,
      decisionWeights: weights, contributionMinThreshold: contributionThreshold,
    },
  });
  if (!outcome.ok) {
    // 틀린 판정을 내느니 안 하는 편이 낫다. 다만 기관 안내는 계속 제공한다(FR-021j 취지).
    const referral = await buildReferral({
      internalLabel: null, undecidable: true,
      careTargetAge: params.careTargetAge,
      lat: params.lat, lng: params.lng, regionCode: params.regionCode,
    });
    return {
      decided: false, internalLabel: null, burdenLabel: null, burdenDescription: null,
      isWarning: false, contributions: null, comparison: null,
      undecidableNotice: null,
      undecidableReasonText: null, undecidableMeaning: null, undecidableNextSteps: null,
      unavailable: true,
      unavailableNotice: cfg<any>('notice.inferenceUnavailable').text,
      multipleTargetsNotice: null, immediateReferral: referral,
      modelVersion: null, disclaimer: cfg<any>('notice.disclaimer').text,
    };
  }
  const remote: InferenceResult = outcome.value;
  const undecidable = !remote.decided;

  const labels = cfg<any>('burden.labels');
  const notice = cfg<any>('undecidable.noticeText');
  const internalLabel = remote.internalLabel;
  const labelInfo = internalLabel !== null ? labels[String(internalLabel)] : null;

  // 기여 요인 (FR-011·FR-011a·FR-011-1) — 판정 불가면 제시하지 않는다(FR-011c)
  let contribOut: { text: string; isMinor: boolean }[] | null = null;
  let topFeatures: string[] = [];
  if (!undecidable) {
    // 순위와 강약 판단은 계산한 쪽(파이썬)을 그대로 쓴다. 여기서 다시 계산하면 갈라진다.
    const ranked = (remote.contributions ?? []).map((c) => ({
      feature: c.feature, value: c.contrib, abs: Math.abs(c.contrib),
    }));
    topFeatures = ranked.map((r) => r.feature);
    contribOut = ranked.map((r) => {
      const q = (questions.questions as any[]).find((x) => x.feature === r.feature);
      const j = model.features.indexOf(r.feature);
      const opt = q?.options?.find((o: any) => o.value === row[j]);
      const answer = opt?.label ?? (row[j] === model.missing_sentinel ? '해당사항 없음' : String(row[j]));
      return {
        // research.md R-3: 인과가 아니라 동반 관찰 표현으로 쓴다.
        text: `${q?.explainTemplate ?? r.feature} — "${answer}"`,
        isMinor: r.abs < contributionThreshold,
      };
    });
  }

  // 참조 집단 비교 (FR-013a~d) — 판정 불가면 제공하지 않는다
  let comparison = null as DiagnosisOutput['comparison'];
  if (!undecidable) {
    const c = await buildComparison(row, internalLabel, topFeatures);
    comparison = c.length ? c : null;      // 비교할 항목이 없으면 영역 자체를 숨긴다
  }

  const referral = await buildReferral({
    internalLabel, undecidable,
    careTargetAge: params.careTargetAge,
    lat: params.lat, lng: params.lng, regionCode: params.regionCode,
  });

  return {
    decided: !undecidable,
    internalLabel,
    burdenLabel: labelInfo?.label ?? null,
    burdenDescription: labelInfo?.description ?? null,
    isWarning: Boolean(labelInfo?.warning),
    contributions: contribOut,
    comparison,
    undecidableNotice: undecidable ? notice.text : null,
    // 어느 갈래로 막혔는지는 추론 서비스가 이미 알려 준다. 내부 용어(희소성·확신도)는
    // 화면에 내보내지 않고, 설정이 가진 보호자용 문구로 바꿔서 내보낸다.
    undecidableReasonText:
      undecidable && remote.undecidableReason
        ? (notice.reasons?.[remote.undecidableReason] ?? null)
        : null,
    undecidableMeaning: undecidable ? (notice.meaning ?? null) : null,
    undecidableNextSteps: undecidable ? (notice.nextSteps ?? null) : null,
    unavailable: false,
    unavailableNotice: null,
    // FR-010d — 단, 판정 불가면 표시하지 않는다(FR-010f)
    multipleTargetsNotice:
      !undecidable && params.multipleCareTargets ? cfg<any>('notice.multipleTargets').text : null,
    immediateReferral: referral,
    modelVersion: model.model_version,
    disclaimer: cfg<any>('notice.disclaimer').text,
  };
}
