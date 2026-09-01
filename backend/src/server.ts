import express from 'express';
import cors from 'cors';
import { env } from './config/env.js';
import { loadConfig } from './config/configStore.js';
import { loadArtifacts } from './inference/modelLoader.js';
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
  const app = await createApp();
  const server = app.listen(env.port, () => {
    console.log(`[cb-backend] http://localhost:${env.port}/api/v1`);
    console.log(`  공개 도메인 : ${env.publicOrigin}`);
    console.log(`  모델        : ${model.model_version} (${model.family}, 문항 ${model.features.length}개)`);
    console.log(`  문항 집합   : ${model.question_set_version}`);
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
