"""[4/4] 아티팩트 내보내기. ml/train.py stage_export 이관.

**여기가 파일을 쓰는 유일한 단계다.** 그리고 쓰는 곳은 인자로 받은 out_dir 뿐이다 —
배포본(models/<release>/)을 직접 덮지 않는다(설계 4.4).
"""
import json
import time
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.preprocessing import OneHotEncoder

from cb_burden import config
from cb_burden.explain.saabas import contributions
from cb_burden.questions import SELF_REPORT, build_question
from cb_burden.stages import _core


def export_tree(t):
    """sklearn 트리를 런타임이 읽을 최소 구조로 변환한다."""
    tr = t.tree_
    val = tr.value.reshape(tr.node_count, -1)
    tot = val.sum(axis=1, keepdims=True)
    prob = np.divide(val, np.where(tot == 0, 1, tot))
    return {
        'feature': [int(f) for f in tr.feature],
        'threshold': [round(float(v), 6) for v in tr.threshold],
        'left': [int(v) for v in tr.children_left],
        'right': [int(v) for v in tr.children_right],
        'value': [[round(float(x), 6) for x in row] for row in prob],
    }


def run(snap, base, sel, cal, out_dir, model_version, question_set_version,
        verbose=True, logit_params=None):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    X, y, _ = _core.train_view(snap)
    idx = {f: i for i, f in enumerate(snap['features'])}
    cols = [idx[f] for f in sel['selected']]
    Xs = X[:, cols]

    family = base['family']
    payload = {
        'model_version': model_version,
        'question_set_version': question_set_version,
        'family': family,
        'features': sel['selected'],
        'classes': config.CLASSES,
        'decision_weights': sel['weights'],
        'missing_sentinel': config.MISSING_SENTINEL,
        'trained_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
    }

    enc = None                      # logit 이 아니면 인코더가 없다 (joblib 묶음에서 씀)
    if family == 'logit':
        # 다항 로지스틱 — 계수 행렬만 내보내면 런타임이 내적 + softmax 로 재현한다.
        enc = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
        Xoh = enc.fit_transform(Xs)
        model = _core.make_logit(**(logit_params or {}))
        model.fit(Xoh, y)

        cats = [[float(v) for v in c] for c in enc.categories_]
        # 기준값: 학습 분포에서의 기대 기여. sum(contrib) + base = logit 이 정확히 성립한다.
        col, spans, expect = 0, [], []
        for j, c in enumerate(cats):
            width = len(c)
            spans.append([col, width])
            freq = Xoh[:, col:col + width].mean(axis=0)
            expect.append((model.coef_[:, col:col + width] * freq).sum(axis=1).tolist())
            col += width
        payload.update({
            'categories': cats,
            'spans': spans,
            'coef': [[round(float(v), 6) for v in row] for row in model.coef_],
            'intercept': [round(float(v), 6) for v in model.intercept_],
            'expected_contrib': [[round(float(v), 6) for v in e] for e in expect],
        })
    else:
        model = _core.make_model(family)
        model.fit(Xs, y)
        payload['trees'] = [export_tree(t) for t in model.estimators_]

    (out_dir / 'model_v1.json').write_text(json.dumps(payload), encoding='utf-8')

    (out_dir / 'selection_v1.json').write_text(
        json.dumps({'model_version': model_version, 'k': len(sel['selected']), **sel,
                    'family_comparison': base['results']},
                   ensure_ascii=False, indent=2), encoding='utf-8')

    (out_dir / 'uncertainty_v1.json').write_text(
        json.dumps({'model_version': model_version, **cal}, ensure_ascii=False),
        encoding='utf-8')

    questions = [build_question(f, i + 1) for i, f in enumerate(sel['selected'])]
    (out_dir / 'questions_v1.json').write_text(
        json.dumps({'question_set_version': question_set_version,
                    'model_version': model_version,
                    'questions': questions,
                    'selfReport': {'questionNo': 0, 'feature': None,
                                   'originalItem': SELF_REPORT['item'],
                                   'text': SELF_REPORT['text'], 'inputType': 'choice',
                                   'options': [{'value': v, 'label': l}
                                               for v, l in SELF_REPORT['options']],
                                   'hasNotApplicable': False}},
                   ensure_ascii=False, indent=2), encoding='utf-8')

    # 기여도 구분 임계값 (FR-011-1): 학습 데이터 기여도 절댓값 분포의 하위 분위
    sample = Xs[np.random.RandomState(config.SEED).choice(
        len(Xs), size=min(300, len(Xs)), replace=False)]
    mags = []
    for row in sample:
        c, _ = contributions(payload, list(row))
        mags.extend(abs(v) for v in c)
    thr = float(np.quantile(mags, 0.55)) if mags else 0.01
    (out_dir / 'contribution_v1.json').write_text(
        json.dumps({'min_threshold': thr,
                    'basis': 'train 표본 300건 기여도 절댓값 55분위'},
                   ensure_ascii=False), encoding='utf-8')

    # 분석용 원본 모델 — **배포 대상이 아니다.** 런타임은 models/*.json 만 읽는다.
    joblib.dump({
        'model_version': model_version,
        'question_set_version': question_set_version,
        'family': family,
        'features': sel['selected'],
        'classes': config.CLASSES,
        'decision_weights': sel['weights'],
        'missing_sentinel': config.MISSING_SENTINEL,
        'model': model,
        'encoder': enc,
        'sklearn_version': sklearn.__version__,
        'trained_at': payload['trained_at'],
        'note': '분석·추론 서비스용. models/*.json 이 배포 계약이다.',
    }, out_dir / 'model_v1.joblib')

    if verbose:
        shape = (f"트리 {len(payload['trees'])}개" if 'trees' in payload
                 else f"계수 {len(payload['coef'])}x{len(payload['coef'][0])}")
        print(f"   model_v1.json         {family} · {shape} · 변수 {len(sel['selected'])}개")
        print(f"   uncertainty_v1.json   τ_conf={cal['tau_conf']:.4f} τ_dens={cal['tau_dens']:.4f}")
        print(f"   questions_v1.json     문항 {len(questions)}개 + 자가보고 1개")
        print(f"   contribution_v1.json  임계값 {thr:.5f}")
        print(f"   model_v1.joblib       분석·추론용")
    return payload
