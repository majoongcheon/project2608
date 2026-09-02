"""단계 스모크 — 합성 300행으로 baseline→select→calibrate→export 가 끝까지 도는가.

성능을 보지 않는다. **끝까지 돌고 규약을 지킨 산출물이 나오는지**만 본다.
"""
import json
from pathlib import Path

import pytest
from cb_burden.artifacts import validate
from cb_burden.data import snapshot
from cb_burden.stages import baseline, calibrate, export, select

FIX = Path(__file__).parent / 'fixtures' / 'mini_snapshot.csv.gz'


@pytest.fixture(scope='module')
def snap():
    return snapshot.read(FIX)


@pytest.fixture(scope='module')
def pipeline(snap):
    base = baseline.run(snap, families=('logit',), verbose=False)
    sel = select.run(snap, base, min_k=6, verbose=False)
    cal = calibrate.run(snap, base, sel, verbose=False)
    return base, sel, cal


def test_기준_모델이_계열을_고른다(pipeline):
    base = pipeline[0]
    assert base['family'] in ('logit', 'rf', 'et')
    assert len(base['weights']) == 5
    # 고부담(1·2)에만 가산점이 붙고 나머지는 1.0 이다
    assert base['weights'][2:] == [1.0, 1.0, 1.0]


def test_선별이_문항을_줄인다(pipeline, snap):
    sel = pipeline[1]
    assert 1 <= len(sel['selected']) <= len(snap['features'])
    assert len(sel['weights']) == 5
    assert sel['k_source']


def test_임계값이_규약_범위_안에_있다(pipeline):
    cal = pipeline[2]
    assert 0.0 < cal['tau_conf'] < 1.0
    assert cal['tau_dens'] < 0.0
    assert 'freq_table' in cal


def test_산출물이_전부_나오고_검증을_통과한다(pipeline, snap, tmp_path):
    base, sel, cal = pipeline
    export.run(snap, base, sel, cal, out_dir=tmp_path,
               model_version='vtest', question_set_version='qs-test', verbose=False)

    names = {p.name for p in tmp_path.iterdir()}
    assert {'model_v1.json', 'selection_v1.json', 'uncertainty_v1.json',
            'questions_v1.json', 'contribution_v1.json', 'model_v1.joblib'} <= names

    b = {k: json.loads((tmp_path / f'{k}_v1.json').read_text(encoding='utf-8'))
         for k in ('model', 'selection', 'uncertainty', 'questions', 'contribution')}
    assert validate.check(b) is True


def test_export_는_배포본을_건드리지_않는다(pipeline, snap, tmp_path):
    # 2026-09-01 사고 — 학습이 최상위 models/ 를 덮었다. 이제 out_dir 밖에 쓰지 않는다.
    before = {p.name: p.stat().st_mtime for p in Path('models').glob('*.json')}
    base, sel, cal = pipeline
    export.run(snap, base, sel, cal, out_dir=tmp_path / 'run2',
               model_version='vtest', question_set_version='qs-test', verbose=False)
    after = {p.name: p.stat().st_mtime for p in Path('models').glob('*.json')}
    assert before == after
