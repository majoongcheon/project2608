"""골든 케이스 생성.

TS 이식본이 사라지면 "패리티(두 구현 대조)"라는 이름이 뜻을 잃는다. 같은 형식을
`golden_v1.json` 으로 만들어, **재학습·리팩터링 뒤에도 같은 답을 내는지** 확인하는 데 쓴다.
"""
import json
from pathlib import Path

from cb_burden.explain.saabas import predict_proba


def build(payload, snap, out_dir):
    idx = {f: i for i, f in enumerate(snap['features'])}
    cols = [idx[f] for f in payload['features']]
    cases = []
    for row in snap['X'][:, cols]:
        r = [float(v) for v in row]
        cases.append({'input': r, 'proba': list(predict_proba(payload, r))})

    out = Path(out_dir) / 'golden_v1.json'
    out.write_text(json.dumps({
        'model_version': payload['model_version'],
        'features': payload['features'],
        'n': len(cases),
        'cases': cases,
    }), encoding='utf-8')
    return out
