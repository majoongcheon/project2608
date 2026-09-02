"""배포된 model_v1.json 에서 sklearn 객체를 되살려 분석용 joblib 으로 남긴다.

왜 재학습하지 않는가
    `train.py --stage export` 를 돌리면 models/*.json 이 새로 쓰인다. v1.0.0 이 운영
    중이므로 덮어쓸 수 없다. JSON 에는 계수·절편·범주가 전부 들어 있어 **같은 모델을
    그대로 복원**할 수 있다. 복원본이 배포본과 일치하는지는 parity_v1.json 3,000건으로
    확인한다 — 일치하지 않으면 파일을 만들지 않는다.

이 파일은 분석 전용이다. 백엔드는 읽지 않는다.

    python3 ml/HG_rebuild_joblib.py              # models/ (배포본)
    python3 ml/HG_rebuild_joblib.py v1.1.0       # models/v1.1.0/ (보관본)
"""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parent.parent
TOL = 1e-9


def build_encoder(cats):
    """JSON 의 범주 목록으로 인코더를 되살린다.

    속성을 손으로 넣지 않고 **모든 범주가 한 번씩 나오는 배열에 fit** 한다.
    sklearn 내부 속성 이름은 판마다 바뀌지만 이 방법은 그 영향을 받지 않는다.
    """
    height = max(len(c) for c in cats)
    grid = np.empty((height, len(cats)))
    for j, c in enumerate(cats):
        col = list(c) + [c[-1]] * (height - len(c))     # 남는 칸은 마지막 범주로 채움
        grid[:, j] = col
    enc = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
    enc.fit(grid)
    for j, c in enumerate(cats):                        # 순서까지 같아야 계수와 맞는다
        got = [float(v) for v in enc.categories_[j]]
        if got != [float(v) for v in c]:
            raise SystemExit(f'범주 순서가 다르다 (열 {j}): {got} != {c}')
    return enc


def build_model(payload):
    clf = LogisticRegression(max_iter=2000)
    clf.coef_ = np.array(payload['coef'], dtype=float)
    clf.intercept_ = np.array(payload['intercept'], dtype=float)
    clf.classes_ = np.array(payload['classes'])
    clf.n_features_in_ = clf.coef_.shape[1]
    clf.n_iter_ = np.array([-1])                        # 복원본임을 표시
    return clf


def encode(enc, rows):
    return enc.transform(np.asarray(rows, dtype=float))


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else ''
    src = ROOT / 'models' / version if version else ROOT / 'models'
    payload = json.loads((src / 'model_v1.json').read_text(encoding='utf-8'))

    if payload['family'] != 'logit':
        raise SystemExit(f"logit 만 복원한다 (현재 {payload['family']}). 트리 계열은 재학습이 필요하다.")

    enc = build_encoder(payload['categories'])
    clf = build_model(payload)

    # 검증 — 배포본과 같은 답을 내는가. parity 기준값이 없으면 만들지 않는다.
    pf = src / 'parity_v1.json'
    if not pf.exists():
        raise SystemExit(f'{pf} 가 없어 복원본을 검증할 수 없다. 파일을 만들지 않는다.')
    fixture = json.loads(pf.read_text(encoding='utf-8'))
    rows = [c['input'] for c in fixture['cases']]
    want = np.array([c['proba'] for c in fixture['cases']])
    got = clf.predict_proba(encode(enc, rows))
    worst = float(np.abs(got - want).max())
    print(f'검증  {len(rows)}건 · 최대 오차 {worst:.3e}  (허용 {TOL:.0e})')
    if worst >= TOL:
        raise SystemExit('복원본이 배포본과 다르다. 파일을 만들지 않는다.')

    out = src / 'model_v1.joblib'
    joblib.dump({
        'model_version': payload['model_version'],
        'question_set_version': payload['question_set_version'],
        'family': payload['family'],
        'features': payload['features'],
        'classes': payload['classes'],
        'decision_weights': payload['decision_weights'],
        'missing_sentinel': payload['missing_sentinel'],
        'model': clf,
        'encoder': enc,
        'sklearn_version': sklearn.__version__,
        'trained_at': payload.get('trained_at'),
        'rebuilt_from': 'model_v1.json',
        'note': '분석 전용. 런타임은 이 파일을 읽지 않는다. 계수 복원본이라 n_iter_ 등 학습 과정 정보는 없다.',
    }, out)
    print(f'생성  {out.relative_to(ROOT)}  ({out.stat().st_size / 1024:.1f} KB)')
    print(f'      {payload["model_version"]} · 문항 {len(payload["features"])}개 · sklearn {sklearn.__version__}')


if __name__ == '__main__':
    main()
