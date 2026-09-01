import { Router } from 'express';
import { cfg } from '../config/configStore.js';
import { getArtifacts } from '../inference/modelLoader.js';
import { one } from '../repositories/pool.js';
import { wrap } from '../middleware/errors.js';

export const metaRouter = Router();

// GET /config — 화면 표시에 필요한 설정만.
//   판정 임계값·판정 불가 기준은 반환하지 않는다 (응답을 역산해 판정을 조작할 수 있다).
metaRouter.get('/config', wrap(async (_req, res) => {
  const labels = cfg<any>('burden.labels');
  res.json({
    burdenLabels: Object.fromEntries(
      Object.entries(labels).map(([k, v]: any) => [k, { label: v.label, warning: v.warning }])),
    ageMappingBoundary: cfg<any>('age.mappingBoundary').boundary,
    serviceAgeRanges: cfg<any>('age.serviceRanges'),
    outOfRangeNotices: cfg<any>('age.outOfRangeNotice'),
    facilityCount: cfg<any>('referral.facilityCount').count,
    draftExpiryHours: cfg<any>('draft.expiryHours').hours,
    notices: {
      disclaimer: cfg<any>('notice.disclaimer').text,
      cancelWindow: cfg<any>('notice.cancelWindow').text,
      selfReport: cfg<any>('selfreport.noticeText').text,
    },
  });
}));

// GET /model — 버전 공개 (FR-012a·FR-012b)
metaRouter.get('/model', wrap(async (_req, res) => {
  const { model } = getArtifacts();
  const row = await one<{ activated_at: Date; macro_f1: number; high_burden_recall: number }>(
    'SELECT activated_at, macro_f1, high_burden_recall FROM cb_model_version_v1 WHERE model_version = ?',
    [model.model_version]);
  res.json({
    modelVersion: model.model_version,
    questionSetVersion: model.question_set_version,
    activatedAt: row?.activated_at ?? null,
    changeNotice: cfg<any>('notice.modelChange').text,
  });
}));

metaRouter.get('/health', wrap(async (_req, res) => {
  const { model } = getArtifacts();
  res.json({ status: 'ok', modelVersion: model.model_version, time: new Date().toISOString() });
}));
