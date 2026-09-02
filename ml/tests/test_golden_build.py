"""골든 케이스 — 재학습 뒤에도 같은 답을 내는지 확인할 기준값을 만든다."""
import json
from pathlib import Path

from cb_burden.artifacts import golden
from cb_burden.data import snapshot

FIX = Path(__file__).parent / 'fixtures' / 'mini_snapshot.csv.gz'


def test_모든_행의_확률이_기록된다(tmp_path, monkeypatch):
    snap = snapshot.read(FIX)
    payload = {'model_version': 'vtest', 'features': snap['features'][:2],
               'family': 'logit', 'classes': [1, 2, 3, 4, 5]}
    monkeypatch.setattr(golden, 'predict_proba', lambda _p, _r: [0.2] * 5)

    out = golden.build(payload, snap, tmp_path)
    got = json.loads(out.read_text(encoding='utf-8'))
    assert out.name == 'golden_v1.json'
    assert got['model_version'] == 'vtest'
    assert got['n'] == len(snap['y'])
    assert len(got['cases']) == len(snap['y'])
    assert len(got['cases'][0]['proba']) == 5
    assert len(got['cases'][0]['input']) == 2
