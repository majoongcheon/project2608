# -*- coding: utf-8 -*-
"""돌봄부담 진단 — predict(payload) -> dict

    from predict import predict
    predict({"answers": [{"questionNo": 1, "value": 4}, ...]})

같은 폴더의 세 파일을 읽는다.
    model.joblib   Pipeline(OneHotEncoder → LogisticRegression). 전처리와 확률까지.
    policy.json    결정 가중치 · 판정 불가 임계값 · 빈도표 · 기여도 기준.
    schema.json    입력 문항 · 허용 범위.

★ model.joblib 만 단독으로 쓰면 `pipe.predict()` 는 **결정 가중치와 판정 불가가 빠진**
  답을 낸다. 운영 서비스와 같은 판정을 얻으려면 이 모듈의 predict() 를 쓴다.
  자세한 것은 model_card.md 의 "사용 금지 상황".

의존: scikit-learn 1.6.1 · joblib (requirements.txt 참조). DB·네트워크를 쓰지 않는다.
"""
import json
import math
from pathlib import Path

import joblib

HERE = Path(__file__).resolve().parent

_pipe = None
_policy = None
_schema = None
_parts = None


class InvalidPayload(ValueError):
    """입력이 스키마를 만족하지 않는다."""


def _load():
    """파일을 한 번만 읽는다."""
    global _pipe, _policy, _schema, _parts
    if _pipe is not None:
        return
    _pipe = joblib.load(HERE / 'model.joblib')
    _policy = json.loads((HERE / 'policy.json').read_text(encoding='utf-8'))
    _schema = json.loads((HERE / 'schema.json').read_text(encoding='utf-8'))

    # 계수·범주는 Pipeline 을 단일 출처로 삼는다 — policy.json 에 중복 저장하지 않는다.
    enc = _pipe.named_steps['encoder']
    clf = _pipe.named_steps['classifier']
    cats = [[float(v) for v in c] for c in enc.categories_]
    spans, col = [], 0
    for c in cats:
        spans.append((col, len(c)))
        col += len(c)
    _parts = {
        'categories': cats,
        'spans': spans,
        'coef': [[float(v) for v in row] for row in clf.coef_],
        'intercept': [float(v) for v in clf.intercept_],
    }


# ───────────────────────────────────────────────────────── 입력
def _to_row(payload):
    """payload 를 모델 입력 벡터로. 검증 실패는 InvalidPayload."""
    if not isinstance(payload, dict):
        raise InvalidPayload('payload 는 객체여야 합니다')
    answers = payload.get('answers')
    if not isinstance(answers, list):
        raise InvalidPayload('answers 는 배열이어야 합니다')

    qs = _schema['questions']
    by_no = {}
    for a in answers:
        if not isinstance(a, dict) or 'questionNo' not in a:
            raise InvalidPayload('answers 의 각 항목은 questionNo 와 value 를 가져야 합니다')
        by_no[a['questionNo']] = a.get('value')

    missing = [q['questionNo'] for q in qs if q['questionNo'] not in by_no]
    if missing:
        raise InvalidPayload(f'응답하지 않은 문항이 있습니다: {missing}')

    sentinel = _policy['missing_sentinel']
    row = []
    for q in qs:
        v = by_no[q['questionNo']]
        if v is None:
            if not q['nullable']:
                raise InvalidPayload(
                    f"문항 {q['questionNo']}({q['feature']}) 는 '해당 없음'을 받지 않습니다")
            row.append(float(sentinel))
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)) or float(v) != int(v):
            raise InvalidPayload(f"문항 {q['questionNo']} 의 값은 정수여야 합니다: {v!r}")
        if int(v) == sentinel:
            # 결측 센티널을 직접 넣은 경우. 학습 데이터를 재현할 때만 쓰인다 —
            # 서비스 화면에는 이 값을 만들 선택지가 없는 문항이 있다(schema 의 nullable).
            if not q['acceptsSentinel']:
                raise InvalidPayload(
                    f"문항 {q['questionNo']}({q['feature']}) 는 결측({sentinel})을 "
                    f"학습하지 않았습니다")
            row.append(float(sentinel))
            continue
        if int(v) not in q['enum']:
            raise InvalidPayload(
                f"문항 {q['questionNo']} 의 값 {int(v)} 는 허용 범위 밖입니다 {q['enum']}")
        row.append(float(int(v)))
    return row


# ───────────────────────────────────────────────────────── 계산
def _rarity(row):
    """응답 조합이 학습 분포에서 얼마나 드문가. 작을수록(음수로 클수록) 드물다."""
    u = _policy['undecidable']
    table, eps = u['freq_table'], u['eps']
    s = 0.0
    for j, f in enumerate(_policy['features']):
        p = table.get(f, {}).get(str(int(row[j])), eps)
        s += math.log(max(p, eps))
    return s / len(_policy['features'])


def _cat_index(j, value):
    for i, c in enumerate(_parts['categories'][j]):
        if c == value:
            return i
    return -1                      # 학습에 없던 값 — 원-핫이 전부 0


def contributions_all(row, cls_idx):
    """(변수별 기여도, 기준값). 선형 SHAP — 근사가 아니라 정확한 분해다."""
    exp = _policy['contribution']['expected_contrib']
    coef = _parts['coef']
    out = []
    for j in range(len(_policy['features'])):
        idx = _cat_index(j, row[j])
        actual = 0.0 if idx < 0 else coef[cls_idx][_parts['spans'][j][0] + idx]
        out.append(actual - exp[j][cls_idx])
    base = _parts['intercept'][cls_idx] + sum(e[cls_idx] for e in exp)
    return out, base


def predict(payload):
    """돌봄부담을 판정한다.

    반환 dict
        decided             판정이 성립했나
        internalLabel       1~5 (역방향 척도 · 1이 최고부담). 판정 불가면 None
        proba               등급별 확률 5개
        maxProba · rarity   판정 불가 판단에 쓴 두 값
        undecidableReason   'sparse' | 'ambiguous' | None
        contributions       상위 3개 기여 요인. 판정 불가면 None
        modelVersion · questionSetVersion
    """
    _load()
    row = _to_row(payload)

    proba = [float(v) for v in _pipe.predict_proba([row])[0]]
    maxp = max(proba)
    rar = _rarity(row)

    u = _policy['undecidable']
    # 두 조건은 OR. 함께 걸리면 sparse 가 우선한다 — 어느 답이 드문지 짚어 줄 수 있어
    # 이용자가 받는 설명이 더 유용하기 때문이다.
    reason = None
    if rar < u['tau_dens']:
        reason = 'sparse'
    elif maxp < u['tau_conf']:
        reason = 'ambiguous'

    out = {
        'modelVersion': _policy['model_version'],
        'questionSetVersion': _policy['question_set_version'],
        'proba': proba,
        'decided': reason is None,
        'internalLabel': None,
        'maxProba': maxp,
        'rarity': rar,
        'undecidableReason': reason,
        'contributions': None,
    }
    if reason is not None:
        # 구간도 기여 요인도 내지 않는다. "모른다"에 근거를 붙이면 오해를 부른다.
        return out

    w = _policy['decision_weights']
    idx = max(range(len(proba)), key=lambda i: proba[i] * w[i])
    out['internalLabel'] = _policy['classes'][idx]

    contrib, _base = contributions_all(row, idx)
    thr = _policy['contribution']['min_threshold']
    ranked = sorted(
        ({'feature': f, 'value': float(row[j]),
          'contrib': round(float(contrib[j]), 6),
          'isMinor': abs(contrib[j]) < thr}
         for j, f in enumerate(_policy['features'])),
        key=lambda x: -abs(x['contrib']))
    out['contributions'] = ranked[:_policy['contribution']['top_k']]
    return out


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        payload = json.loads(sys.argv[1])
    else:                                   # 예시 — 배포본에서 판정이 성립하는 응답
        payload = {'answers': [
            {'questionNo': 1, 'value': 4}, {'questionNo': 2, 'value': 4},
            {'questionNo': 3, 'value': 5}, {'questionNo': 4, 'value': 1},
            {'questionNo': 5, 'value': None}, {'questionNo': 6, 'value': 3},
            {'questionNo': 7, 'value': 1}]}
    print(json.dumps(predict(payload), ensure_ascii=False, indent=2))
