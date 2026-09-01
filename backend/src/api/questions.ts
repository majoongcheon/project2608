import { Router } from 'express';
import { getArtifacts } from '../inference/modelLoader.js';
import { cfg } from '../config/configStore.js';
import { wrap } from '../middleware/errors.js';

export const questionsRouter = Router();

// GET /questions — 진행률(FR-005)의 분모는 totalCount. 사전 입력은 포함하지 않는다(FR-002b).
questionsRouter.get('/questions', wrap(async (_req, res) => {
  const { questions, model } = getArtifacts();
  const qs = (questions.questions as any[]).map((q) => ({
    questionNo: q.questionNo,
    text: q.text,
    inputType: q.inputType,
    min: q.min ?? null, max: q.max ?? null, unit: q.unit ?? null,
    options: q.options,
    hasNotApplicable: q.hasNotApplicable,
  }));
  res.json({
    version: model.question_set_version,
    totalCount: qs.length,
    questions: qs,
    selfReportQuestion: {
      questionNo: 0,
      text: questions.selfReport.text,
      inputType: 'choice',
      options: questions.selfReport.options,
      hasNotApplicable: false,
      notice: cfg<any>('selfreport.noticeText').text,     // FR-008d
    },
  });
}));
