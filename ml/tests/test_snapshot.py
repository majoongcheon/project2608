"""스냅샷 — 학습 입력을 파일로 고정한다. 해시가 다르면 학습을 시작하지 않는다."""
import json
import pytest
from cb_burden.data import snapshot


def _rows():
    return [
        {'split': 'train', 'cv_fold': 1, 'care_burden': 2, 'a': 1.0, 'b': -1.0},
        {'split': 'test', 'cv_fold': 0, 'care_burden': 3, 'a': 2.0, 'b': 5.0},
    ]


def _meta(p):
    return json.loads(snapshot.meta_path(p).read_text(encoding='utf-8'))


def test_쓰고_읽으면_같은_값이_나온다(tmp_path):
    p = tmp_path / 'snap.csv.gz'
    snapshot.write(p, ['a', 'b'], _rows(), source_view='v_test')
    got = snapshot.read(p)
    assert got['features'] == ['a', 'b']
    assert got['y'].tolist() == [2, 3]
    assert got['split'].tolist() == ['train', 'test']
    assert got['X'][0].tolist() == [1.0, -1.0]
    assert got['cv_fold'].tolist() == [1, 0]


def test_메타에_해시와_행수가_남는다(tmp_path):
    p = tmp_path / 'snap.csv.gz'
    snapshot.write(p, ['a', 'b'], _rows(), source_view='v_test')
    meta = _meta(p)
    assert meta['rows'] == 2
    assert meta['features'] == 2
    assert meta['source_view'] == 'v_test'
    assert meta['split'] == {'train': 1, 'test': 1}
    assert len(meta['sha256']) == 64


def test_비밀번호는_메타에_남기지_않는다(tmp_path):
    # 원칙 III — 저장 금지 항목은 남기지 않는다
    p = tmp_path / 'snap.csv.gz'
    snapshot.write(p, ['a', 'b'], _rows(), source_view='v_test',
                   db_info={'host': 'h', 'database': 'd'})
    raw = snapshot.meta_path(p).read_text(encoding='utf-8').lower()
    assert 'password' not in raw
    assert 'passwd' not in raw


def test_파일이_변조되면_읽기가_거부된다(tmp_path):
    p = tmp_path / 'snap.csv.gz'
    snapshot.write(p, ['a', 'b'], _rows(), source_view='v_test')
    p.write_bytes(p.read_bytes() + b'\x00')
    with pytest.raises(ValueError, match='해시'):
        snapshot.read(p)


def test_이미_있는_스냅샷은_덮어쓰지_않는다(tmp_path):
    p = tmp_path / 'snap.csv.gz'
    snapshot.write(p, ['a', 'b'], _rows(), source_view='v_test')
    with pytest.raises(ValueError, match='이미'):
        snapshot.write(p, ['a', 'b'], _rows(), source_view='v_test')
