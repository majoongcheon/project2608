import express from 'express';
import cors from 'cors';
import { env } from './config/env.js';
import { loadConfig, cfg } from './config/configStore.js';
import { loadArtifacts } from './inference/modelLoader.js';
import { inferenceHealth } from './services/inferenceClient.js';
import { questionsRouter } from './api/questions.js';
import { diagnosesRouter } from './api/diagnoses.js';
import { facilitiesRouter } from './api/facilities.js';
import { metaRouter } from './api/meta.js';
import { eventsRouter } from './api/events.js';
import { notFound, errorHandler } from './middleware/errors.js';
import { startJobs } from './jobs/scheduler.js';

export async function createApp() {
  const app = express();

  // 리버스 프록시(Nginx) 뒤에서 동작한다. req.ip 는 해시 생성에만 쓰고 저장·로깅하지 않는다.
  app.set('trust proxy', true);
  app.disable('x-powered-by');

  app.use(cors({
    origin: [env.publicOrigin, `http://localhost:${env.frontendPort}`,
             `http://127.0.0.1:${env.frontendPort}`],
    credentials: false,
  }));
  app.use(express.json({ limit: '256kb' }));

  // 요청 로그에 IP 를 남기지 않는다 (FR-028 · 원칙 III).
  // 경로와 상태만 남긴다. Nginx 쪽 log_format 에서도 $remote_addr 를 제거해야 한다.
  app.use((req, res, next) => {
    const t0 = Date.now();
    res.on('finish', () => {
      console.log(`${req.method} ${req.path} ${res.statusCode} ${Date.now() - t0}ms`);
    });
    next();
  });

  const api = express.Router();
  api.use(questionsRouter);
  api.use(diagnosesRouter);
  api.use(facilitiesRouter);
  api.use(metaRouter);
  api.use(eventsRouter);
  app.use('/api/v1', api);

  app.use(notFound);
  app.use(errorHandler);
  return app;
}

export async function bootstrap() {
  // 기동 시 정합을 검증하고 하나라도 어긋나면 뜨지 않는다 (fail fast).
  // 조용히 잘못된 판정을 내는 것보다 뜨지 않는 편이 낫다.
  await loadConfig();
  const { model } = await loadArtifacts();

  // 2026-09-02 오전, 프론트만 새 코드로 넘어가고 백엔드가 안 따라와 화면이 비었다.
  // 프로세스가 하나 늘었으니 같은 종류의 어긋남을 기동 시점에 잡는다 (설계 4.9.5).
  const health = await inferenceHealth();
  if (health && health.questionSetVersion !== model.question_set_version) {
    throw new Error(
      `추론 서비스의 문항 집합이 다릅니다.\n` +
      `  백엔드 ${model.question_set_version}\n  추론   ${health.questionSetVersion}\n` +
      `  → 두 쪽이 같은 릴리스를 보도록 CB_MODELS_DIR 을 맞추세요`);
  }

  const app = await createApp();
  const server = app.listen(env.port, () => {
    console.log(`[cb-backend] http://localhost:${env.port}/api/v1`);
    console.log(`  공개 도메인 : ${env.publicOrigin}`);
    console.log(`  모델        : ${model.model_version} (${model.family}, 문항 ${model.features.length}개)`);
    console.log(`  문항 집합   : ${model.question_set_version}`);
    console.log(`  추론 서비스 : unix:${env.inferenceSocket}` +
                `${health ? ' · ' + health.modelVersion : ' · 연결 안 됨'}`);
    if (!health) {
      console.warn('\n  [경고] 추론 서비스에 연결할 수 없습니다. 진단만 불가하고 ' +
                   '문항 조회·기관 안내는 동작합니다.\n' +
                   '         python3 -m cb_burden.serve 를 먼저 띄우세요\n');
    }
    // 설정의 결정 가중치가 학습 산출물과 갈라지면 조용히 다른 기준으로 판정한다.
    // 막지는 않는다 — 설정으로 조정하는 것이 정당한 경우가 있다(FR-022). 다만 보이게 한다.
    if (health?.artifactDecisionWeights) {
      const cfgW = cfg<{ weights: number[] }>('model.decisionWeights').weights;
      if (JSON.stringify(cfgW) !== JSON.stringify(health.artifactDecisionWeights)) {
        console.warn(`\n  [경고] 결정 가중치가 학습 산출물과 다릅니다 — 판정은 설정값을 따릅니다.` +
          `\n    설정   ${JSON.stringify(cfgW)}` +
          `\n    산출물 ${JSON.stringify(health.artifactDecisionWeights)}` +
          `\n    → 의도한 조정이 아니라면 db 폴더에서 'npm run seed:config' 를 실행하세요\n`);
      }
    }
  });
  startJobs();
  return server;
}

const isMain = process.argv[1] && import.meta.url.endsWith(process.argv[1].split('/').pop() ?? '');
if (isMain || process.env.CB_BOOTSTRAP === '1') {
  bootstrap().catch((e) => {
    console.error('\n[기동 실패] ' + (e?.message ?? e) + '\n');
    process.exit(1);
  });
}
