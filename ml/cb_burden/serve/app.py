"""추론 서비스.

개인정보를 받지 않는다. 문항 응답과 정책 값만 받고, 요청 본문을 로그에 남기지 않는다
(원칙 III). 내부 전용이라 127.0.0.1 에만 바인드한다.
"""
import os

from fastapi import FastAPI, HTTPException

from cb_burden.serve.engine import Engine
from cb_burden.serve.schema import PredictRequest, PredictResponse


def create_app(release_dir=None):
    release = release_dir or os.getenv('CB_MODELS_DIR', 'models')
    engine = Engine.load(release)          # 로드 실패하면 뜨지 않는다 (fail fast)
    qnos = [q['questionNo'] for q in engine.questions['questions']]

    app = FastAPI(title='cb-burden inference',
                  version=engine.model_json['model_version'])

    @app.get('/health')
    def health():
        # artifactDecisionWeights 를 함께 낸다 — 설정과 아티팩트가 갈라지면 조용히 다른
        # 기준으로 판정한다. 백엔드가 기동 때 대조할 수 있게 한다(설계 4.9.5).
        return {'status': 'ok', 'release': engine.release,
                'modelVersion': engine.model_json['model_version'],
                'questionSetVersion': engine.model_json['question_set_version'],
                'artifactDecisionWeights': engine.model_json['decision_weights']}

    @app.post('/predict', response_model=PredictResponse)
    def predict(req: PredictRequest):
        by_no = {a.questionNo: a.value for a in req.answers}
        if sorted(by_no) != sorted(qnos):
            raise HTTPException(422, f'문항 번호가 모델과 다릅니다. 기대 {qnos}')
        row = [engine.missing if by_no[n] is None else float(by_no[n]) for n in qnos]
        p = req.policy
        return engine.decide(row, p.tauConf, p.tauDens,
                             p.decisionWeights, p.contributionMinThreshold)

    return app
