"""승격 — 배포본을 바꾸는 유일한 경로. 하나라도 어긋나면 아무것도 바꾸지 않는다."""
import json
import pytest
from cb_burden.artifacts import release


def _run(tmp_path, sc=None, golden=True):
    d = tmp_path / 'runs' / 'r1'
    d.mkdir(parents=True)
    (d / 'model_v1.json').write_text('{}', encoding='utf-8')
    if golden:
        (d / 'golden_v1.json').write_text('{}', encoding='utf-8')
    (d / 'run.json').write_text(json.dumps({
        'run_id': 'r1',
        'success_criteria': sc if sc is not None else {
            'SC-004': True, 'SC-005': True, 'SC-016': True}}), encoding='utf-8')
    return d


def test_정상이면_릴리스와_current_가_만들어진다(tmp_path):
    d = _run(tmp_path)
    release.promote(d, tmp_path, 'v1.0.1', validator=lambda _: True)
    assert (tmp_path / 'v1.0.1' / 'model_v1.json').exists()
    cur = json.loads((tmp_path / 'current.json').read_text(encoding='utf-8'))
    assert cur['release'] == 'v1.0.1'
    assert cur['run_id'] == 'r1'


def test_골든이_없으면_거부한다(tmp_path):
    d = _run(tmp_path, golden=False)
    with pytest.raises(ValueError, match='golden'):
        release.promote(d, tmp_path, 'v1.0.1', validator=lambda _: True)
    assert not (tmp_path / 'v1.0.1').exists()


def test_평가를_안_했으면_거부한다(tmp_path):
    d = _run(tmp_path, sc={})
    with pytest.raises(ValueError, match='평가'):
        release.promote(d, tmp_path, 'v1.0.1', validator=lambda _: True)


def test_성공기준_미달이면_거부한다(tmp_path):
    d = _run(tmp_path, sc={'SC-004': True, 'SC-005': False, 'SC-016': True})
    with pytest.raises(ValueError, match='SC-005'):
        release.promote(d, tmp_path, 'v1.0.1', validator=lambda _: True)
    assert not (tmp_path / 'v1.0.1').exists()


def test_이미_있는_릴리스는_거부한다(tmp_path):
    d = _run(tmp_path)
    (tmp_path / 'v1.0.1').mkdir()
    with pytest.raises(ValueError, match='이미'):
        release.promote(d, tmp_path, 'v1.0.1', validator=lambda _: True)


def test_검증_실패면_아무것도_바꾸지_않는다(tmp_path):
    d = _run(tmp_path)

    def bad(_):
        raise ValueError('스키마 오류')

    with pytest.raises(ValueError, match='스키마'):
        release.promote(d, tmp_path, 'v1.0.1', validator=bad)
    assert not (tmp_path / 'v1.0.1').exists()
    assert not (tmp_path / 'current.json').exists()


def test_현재_릴리스를_읽을_수_있다(tmp_path):
    d = _run(tmp_path)
    release.promote(d, tmp_path, 'v1.0.1', validator=lambda _: True)
    assert release.current(tmp_path) == 'v1.0.1'
    assert release.current(tmp_path / 'nowhere') is None
