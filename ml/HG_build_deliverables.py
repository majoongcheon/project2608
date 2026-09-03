"""제출용 산출물 생성 (읽기 전용 → deliverables/ 에만 쓴다).

**재학습하지 않는다.** 배포본 models/ 의 joblib 에서 encoder·model 객체를 그대로 꺼내
sklearn Pipeline 으로 재조립한다. train --stage export 를 돌리면 운영 중인 v1.0.0 의
models/*.json 이 덮여 쓰이므로 절대 부르지 않는다(HG_rebuild_joblib.py 와 같은 이유).

만드는 것
    deliverables/model.joblib   Pipeline(OneHotEncoder → LogisticRegression)
    deliverables/policy.json    판정 불가 임계값 · 결정 가중치 · 빈도표 · 기여도 기준
    deliverables/schema.json    입력 문항 · 타입 · 허용 범위 · 결측 규칙

검증
    만든 Pipeline 의 확률을 models/parity_v1.json 3,000건과 대조한다.
    한 건이라도 어긋나면 파일을 만들지 않는다.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, 'ml/.pylibs'); sys.path.insert(0, 'ml')

import joblib
import numpy as np
import sklearn
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'models'
OUT = ROOT / 'deliverables'
TOL = 1e-9


def rd(name, base=SRC):
    return json.loads((base / name).read_text(encoding='utf-8'))


def main():
    bundle = joblib.load(SRC / 'model_v1.joblib')
    model_json = rd('model_v1.json')
    unc = rd('uncertainty_v1.json')
    contrib = rd('contribution_v1.json')
    questions = rd('questions_v1.json')

    if bundle['family'] != 'logit':
        raise SystemExit(f"이 스크립트는 logit 전용입니다: {bundle['family']}")
    if list(bundle['features']) != list(model_json['features']):
        raise SystemExit('joblib 과 model_v1.json 의 features 가 다릅니다')

    enc, clf = bundle['encoder'], bundle['model']

    # ── Pipeline 재조립. 이미 fit 된 객체를 그대로 끼운다 (재학습 없음)
    pipe = Pipeline([('encoder', enc), ('classifier', clf)])

    # ── 검증 ①  Pipeline 확률 == parity 3,000건
    fx = rd('parity_v1.json')
    X = np.array([c['input'] for c in fx['cases']], dtype=float)
    expect = np.array([c['proba'] for c in fx['cases']], dtype=float)
    got = pipe.predict_proba(X)
    worst = float(np.abs(got - expect).max())
    print(f'[검증①] Pipeline 확률 vs parity {len(fx["cases"]):,}건 — 최대 오차 {worst:.3e}')
    if worst >= TOL:
        raise SystemExit(f'  오차가 {TOL} 이상입니다. 파일을 만들지 않습니다')

    # ── 검증 ②  Pipeline 에서 꺼낸 계수 == model_v1.json 의 계수
    #    predict.py 는 Pipeline 을 단일 출처로 쓰므로 이 둘이 같아야 한다.
    cats = [list(map(float, c)) for c in enc.categories_]
    spans, col = [], 0
    for c in cats:
        spans.append([col, len(c)]); col += len(c)
    d_coef = float(np.abs(np.asarray(clf.coef_) - np.asarray(model_json['coef'])).max())
    d_int = float(np.abs(np.asarray(clf.intercept_) - np.asarray(model_json['intercept'])).max())
    ok_cat = cats == [[float(v) for v in c] for c in model_json['categories']]
    ok_span = spans == [list(s) for s in model_json['spans']]
    print(f'[검증②] 계수 차이 {d_coef:.3e} · 절편 차이 {d_int:.3e} · '
          f'범주 {"일치" if ok_cat else "★불일치"} · spans {"일치" if ok_span else "★불일치"}')
    if not (d_coef < TOL and d_int < TOL and ok_cat and ok_span):
        raise SystemExit('  Pipeline 과 model_v1.json 이 어긋납니다. 파일을 만들지 않습니다')

    OUT.mkdir(exist_ok=True)

    # ── model.joblib
    joblib.dump(pipe, OUT / 'model.joblib')

    # ── policy.json  (Pipeline 이 담지 못하는 것들)
    policy = {
        'model_version': model_json['model_version'],
        'question_set_version': model_json['question_set_version'],
        'sklearn_version': sklearn.__version__,
        'classes': model_json['classes'],
        'missing_sentinel': model_json['missing_sentinel'],
        'features': model_json['features'],
        'decision_weights': model_json['decision_weights'],
        'undecidable': {
            'tau_conf': unc['tau_conf'],
            'tau_dens': unc['tau_dens'],
            'eps': 1e-4,
            'freq_table': unc['freq_table'],
        },
        'contribution': {
            'min_threshold': contrib['min_threshold'],
            'top_k': 3,
            'expected_contrib': model_json['expected_contrib'],
        },
        'note': ('model.joblib(Pipeline) 은 전처리와 확률까지만 담당한다. '
                 '결정 가중치·판정 불가·기여 요인은 이 파일의 값으로 predict.py 가 처리한다.'),
    }
    (OUT / 'policy.json').write_text(
        json.dumps(policy, ensure_ascii=False, indent=2), encoding='utf-8')

    # ── schema.json
    props = []
    for q, cat in zip(questions['questions'], cats):
        allowed = sorted(v for v in cat if v != model_json['missing_sentinel'])
        has_na = model_json['missing_sentinel'] in cat
        opts = q.get('options') or []
        props.append({
            'questionNo': q['questionNo'],
            'feature': q['feature'],
            'text': q['text'],
            'type': 'integer',
            'enum': [int(v) for v in allowed],
            # nullable  = 서비스 화면이 '해당 없음' 선택지를 제공하는가
            # acceptsSentinel = 모델이 결측(-1)을 학습한 범주로 갖는가
            #   둘이 어긋나는 문항이 있다(1·2번). 학습 데이터에는 결측이 3건씩 있으나
            #   화면에는 선택지가 없어 실서비스에서는 나올 수 없는 값이다.
            'nullable': bool(q.get('hasNotApplicable')),
            'acceptsSentinel': has_na,
            'missingSentinel': model_json['missing_sentinel'],
            'labels': {str(o['value']): o['label'] for o in opts if o.get('value') is not None},
        })
    schema = {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        'title': 'cb-burden 입력 스키마',
        'model_version': model_json['model_version'],
        'question_set_version': model_json['question_set_version'],
        'description': ('돌봄부담 진단 입력. answers 는 questionNo 오름차순일 필요는 없으나 '
                        '7문항이 모두 있어야 한다. value 가 null 이면 "해당 없음"이며 '
                        'missingSentinel(-1) 로 치환된다. nullable=false 인 문항에도 '
                        'acceptsSentinel=true 이면 -1 을 직접 넣을 수 있다 — 학습 데이터를 '
                        '그대로 재현할 때만 쓰고, 서비스 화면에서는 나오지 않는 값이다.'),
        'type': 'object',
        'required': ['answers'],
        'properties': {
            'answers': {
                'type': 'array', 'minItems': len(props), 'maxItems': len(props),
                'items': {
                    'type': 'object',
                    'required': ['questionNo', 'value'],
                    'properties': {
                        'questionNo': {'type': 'integer',
                                       'enum': [p['questionNo'] for p in props]},
                        'value': {'type': ['integer', 'null']},
                    },
                },
            },
        },
        'questions': props,
        'featureOrder': model_json['features'],
    }
    (OUT / 'schema.json').write_text(
        json.dumps(schema, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f'\n생성 완료 → {OUT}')
    for f in ('model.joblib', 'policy.json', 'schema.json'):
        print(f'   {f:16s} {(OUT / f).stat().st_size:>9,} B')


if __name__ == '__main__':
    main()
