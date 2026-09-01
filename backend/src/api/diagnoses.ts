import { Router } from 'express';
import { diagnose, findUnanswered, type AnswerInput } from '../services/diagnosisService.js';
import { storeTrainingResponse, cancelTrainingResponse, submitterHash, recentSubmissionCount }
  from '../services/consentService.js';
import { getArtifacts } from '../inference/modelLoader.js';
import { ApiError, wrap } from '../middleware/errors.js';

export const diagnosesRouter = Router();

// POST /diagnoses — 제출과 판정 (FR-007·FR-009~FR-013·FR-021·FR-031·FR-033)
diagnosesRouter.post('/diagnoses', wrap(async (req, res) => {
  const t0 = Date.now();
  const b = req.body ?? {};
  const { model } = getArtifacts();

  if (b.questionSetVersion && b.questionSetVersion !== model.question_set_version) {
    throw new ApiError(409, 'STALE_QUESTION_SET',
      '문항 집합이 갱신되었습니다. 새로고침 후 다시 진행해 주세요.',
      { currentVersion: model.question_set_version });
  }

  const answers: AnswerInput[] = Array.isArray(b.answers)
    ? b.answers.map((a: any) => ({
        questionNo: Number(a.questionNo),
        value: a.value === null || a.value === undefined ? null : Number(a.value),
      }))
    : [];

  // FR-007 — 미응답이 있으면 판정하지 않고 해당 문항으로 돌려보낸다
  const unanswered = findUnanswered(answers);
  if (unanswered.length) {
    throw new ApiError(422, 'UNANSWERED_QUESTIONS', '아직 응답하지 않은 문항이 있습니다.',
      { unansweredQuestionNos: unanswered });
  }

  const consent = b.consentTraining === true;
  const selfReport = b.selfReportLevel == null ? null : Number(b.selfReportLevel);

  // FR-008e — 동의한 경우에만 자가보고 문항이 제시되므로, 동의했다면 응답이 있어야 한다
  if (consent && (selfReport === null || Number.isNaN(selfReport))) {
    throw new ApiError(422, 'UNANSWERED_QUESTIONS', '자가보고 부담 문항에 응답해 주세요.',
      { unansweredQuestionNos: [0] });
  }

  const loc = b.location ?? {};
  const result = await diagnose({
    answers,
    careTargetAge: b.careTargetAge == null ? null : Number(b.careTargetAge),
    multipleCareTargets: b.multipleCareTargets ?? null,
    lat: loc.lat == null ? null : Number(loc.lat),
    lng: loc.lng == null ? null : Number(loc.lng),
    regionCode: loc.regionCode ?? null,
  });

  // FR-031·FR-033 — 동의한 경우에만 저장한다. 미동의 제출은 어떤 행도 만들지 않는다.
  let cancelToken: string | null = null;
  let duplicateFlag = false;
  if (consent) {
    const { hash } = await submitterHash(req.ip);
    duplicateFlag = (await recentSubmissionCount(hash)) > 0;   // 차단하지 않고 기록만 (FR-036a)
    cancelToken = await storeTrainingResponse({
      questionSetVersion: model.question_set_version,
      answers,
      selfReportLevel: selfReport,
      surveyDurationSec: b.surveyDurationSec == null ? null : Number(b.surveyDurationSec),
      predictedLevel: result.internalLabel,
      modelVersion: model.model_version,
      ip: req.ip,
    });
  }

  // ★ internalLabel 은 응답에서 제거한다 — 내부 라벨 비노출(FR-010a, 원칙 II)
  const { internalLabel, ...visible } = result;
  res.json({ ...visible, cancelToken, durationMs: Date.now() - t0, duplicateFlag });
}));

// DELETE /diagnoses/:token — 학습용 저장 취소 (FR-025)
//   존재 여부를 노출하지 않도록 삭제/미존재 모두 204 로 답한다.
diagnosesRouter.delete('/diagnoses/:token', wrap(async (req, res) => {
  await cancelTrainingResponse(String(req.params.token));
  res.status(204).end();
}));
