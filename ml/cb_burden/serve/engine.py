"""추론 엔진 — 상태 없는 계산기.

파일은 load 할 때 한 번만 읽고, 그 뒤로는 파일도 DB 도 건드리지 않는다.
**판정 임계값과 결정 가중치는 호출자가 준다** — 그 값은 설정(cb_config_v1)이 소유하고,
코드 수정 없이 조정할 수 있어야 하기 때문이다(FR-009c).

기여도 분해는 ml/cb_burden/explain/saabas.py 와 같은 알고리즘이다. 여기서 다시 구현하지
않고 그 모듈을 쓴다 — 두 벌이 되면 갈라진다.
"""
import json
import os
import warnings
from pathlib import Path

import joblib
import numpy as np
import sklearn

from cb_burden.explain.saabas import contributions as saabas_contributions

EPS = 1e-4
ALLOW_MISMATCH = 'CB_ALLOW_SKLEARN_MISMATCH'


def _check_sklearn_version(saved, release_dir):
    """joblib 은 만든 sklearn 과 읽는 sklearn 이 같아야 한다.

    다르면 sklearn 이 "결과가 잘못될 수 있다"고 경고만 하고 넘어간다. 경고로 두면
    **조용히 틀린 판정**이 나갈 수 있으므로 기동을 막는다.
    옛 파일에는 기록이 없을 수 있는데, 그건 막지 않는다.
    """
    now = sklearn.__version__
    if not saved or saved == now:
        return
    msg = (f'모델을 만든 sklearn 과 지금 sklearn 이 다릅니다 ({release_dir})\n'
           f'  만든 것 {saved}\n  지금   {now}\n'
           f'  → ml/requirements.txt 의 버전으로 맞추세요:\n'
           f'     pip3 install --target ml/.pylibs -r ml/requirements.txt\n'
           f'  (사정을 알고 넘기려면 {ALLOW_MISMATCH}=1)')
    if os.getenv(ALLOW_MISMATCH) == '1':
        warnings.warn(msg, RuntimeWarning)
        return
    raise ValueError(msg)


class Engine:
    def __init__(self, bundle, model_json, uncertainty, questions, release):
        self.b = bundle
        self.model_json = model_json
        self.unc = uncertainty
        self.questions = questions
        self.release = str(release)
        self.features = list(bundle['features'])
        self.classes = list(bundle['classes'])
        self.missing = bundle['missing_sentinel']

    @classmethod
    def load(cls, release_dir):
        d = Path(release_dir)
        bundle = joblib.load(d / 'model_v1.joblib')

        def rd(name):
            return json.loads((d / name).read_text(encoding='utf-8'))

        _check_sklearn_version(bundle.get('sklearn_version'), d)

        model_json = rd('model_v1.json')
        if list(bundle['features']) != list(model_json['features']):
            raise ValueError(
                f'joblib 과 model_v1.json 의 features 가 다릅니다 ({d})\n'
                f'  joblib {bundle["features"]}\n  json   {model_json["features"]}')
        return cls(bundle, model_json, rd('uncertainty_v1.json'),
                   rd('questions_v1.json'), d)

    # ─────────────────────────────────────────────────────── 계산
    def proba(self, row):
        X = self.b['encoder'].transform(np.array([row], dtype=float))
        return [float(v) for v in self.b['model'].predict_proba(X)[0]]

    def rarity(self, row):
        """응답 조합이 학습 분포에서 얼마나 드문가. 작을수록(음수로 클수록) 드물다."""
        table = self.unc['freq_table']
        s = 0.0
        for j, f in enumerate(self.features):
            p = table.get(f, {}).get(str(int(row[j])), EPS)
            s += np.log(max(p, EPS))
        return float(s / len(self.features))

    def decide(self, row, tau_conf, tau_dens, decision_weights, contrib_threshold):
        p = self.proba(row)
        rar = self.rarity(row)
        maxp = float(max(p))

        # 두 조건은 OR. 함께 걸리면 sparse 가 우선한다 —
        # 어느 답이 드문지 구체적으로 짚어 줄 수 있어 이용자가 받는 설명이 더 유용하다.
        reason = None
        if rar < tau_dens:
            reason = 'sparse'
        elif maxp < tau_conf:
            reason = 'ambiguous'

        out = {
            'modelVersion': self.model_json['model_version'],
            'questionSetVersion': self.model_json['question_set_version'],
            'proba': p,
            'decided': reason is None,
            'internalLabel': None,
            'maxProba': maxp,
            'rarity': rar,
            'undecidableReason': reason,
            'contributions': None,
        }
        if reason is not None:
            return out          # FR-009a·FR-011c — 구간도 기여 요인도 내지 않는다

        w = np.array(decision_weights, dtype=float)
        idx = int(np.argmax(np.array(p) * w))
        out['internalLabel'] = self.classes[idx]
        out['contributions'] = self._contributions(row, idx, contrib_threshold)
        return out

    def _contributions(self, row, cls_idx, threshold):
        # ★ cls 를 반드시 넘긴다. 생략하면 saabas 가 **아티팩트의 결정 가중치**로 구간을
        #   다시 고르는데, 우리는 설정에서 온 정책 가중치로 골랐다. 두 구간이 다르면
        #   화면에 표시된 구간과 설명이 어긋난다.
        contrib, _base = saabas_contributions(
            self.model_json, [float(v) for v in row], cls_idx)
        ranked = sorted(
            ({'feature': f, 'value': float(row[j]),
              'contrib': round(float(contrib[j]), 6),
              'isMinor': abs(contrib[j]) < threshold}
             for j, f in enumerate(self.features)),
            key=lambda x: -abs(x['contrib']))
        return ranked[:3]
