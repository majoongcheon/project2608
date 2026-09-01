// 모델 아티팩트 로드와 정합 검증 (data-model.md 2장 불변 조건)
//   features 순서가 어긋나면 조용히 잘못된 판정이 나온다.
//   따라서 불일치를 발견하면 경고가 아니라 **기동 실패**로 처리한다.
import fs from 'node:fs';
import path from 'node:path';
import { env } from '../config/env.js';
import { query } from '../repositories/pool.js';
import type { ModelPayload, Uncertainty } from './types.js';

export interface Artifacts {
  model: ModelPayload;
  uncertainty: Uncertainty;
  contributionThreshold: number;
  questions: any;
}

let artifacts: Artifacts | null = null;

function readJson(name: string): any {
  const p = path.join(env.modelsDir, name);
  if (!fs.existsSync(p)) {
    throw new Error(`모델 아티팩트가 없습니다: ${p}\n  → 'python3 ml/train.py all' 을 먼저 실행하세요.`);
  }
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

export async function loadArtifacts(): Promise<Artifacts> {
  const model: ModelPayload = readJson('model_v1.json');
  const selection = readJson('selection_v1.json');
  const uncertainty: Uncertainty = readJson('uncertainty_v1.json');
  const contribution = readJson('contribution_v1.json');
  const questions = readJson('questions_v1.json');

  // (1) 모델 features 순서 = 선별 결과
  const a = model.features.join(',');
  const b = (selection.selected as string[]).join(',');
  if (a !== b) {
    throw new Error(`model_v1.json 의 features 가 selection_v1.json 과 다릅니다.\n  model: ${a}\n  select: ${b}`);
  }

  // (2) 문항 집합의 feature 목록 = 모델 features
  const qf = (questions.questions as any[]).map((q) => q.feature).join(',');
  if (qf !== a) {
    throw new Error(`questions_v1.json 의 feature 순서가 모델과 다릅니다.\n  model: ${a}\n  questions: ${qf}`);
  }

  // (3) DB 에 적재된 활성 문항 집합도 동일해야 한다
  const rows = await query<{ feature: string }>(
    'SELECT feature FROM cb_question_v1 WHERE question_set_version = ? AND is_self_report = 0 ORDER BY question_no',
    [model.question_set_version]);
  if (rows.length === 0) {
    throw new Error(`cb_question_v1 에 문항 집합 ${model.question_set_version} 이 없습니다.\n  → db 폴더에서 'npm run seed:questions' 를 실행하세요.`);
  }
  const df = rows.map((r) => r.feature).join(',');
  if (df !== a) {
    throw new Error(`DB 문항 집합이 모델과 다릅니다.\n  model: ${a}\n  db: ${df}`);
  }

  // (4) 지원하는 계열인지
  if (!['logit', 'rf', 'et'].includes(model.family)) {
    throw new Error(`지원하지 않는 모델 계열입니다: ${model.family}`);
  }

  artifacts = {
    model, uncertainty,
    contributionThreshold: contribution.min_threshold,
    questions,
  };
  return artifacts;
}

export function getArtifacts(): Artifacts {
  if (!artifacts) throw new Error('모델 아티팩트가 로드되지 않았습니다.');
  return artifacts;
}
