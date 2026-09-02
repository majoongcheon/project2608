"""무결성 — 기존 db.py 의 단언을 옮긴 것. 어긋나면 학습을 시작하지 않는다."""
import numpy as np
import pytest
from cb_burden.data import integrity


def _snap(features=None, n_train=2398, n_test=602, folds=None):
    features = features if features is not None else [f'f{i}' for i in range(38)]
    n = n_train + n_test
    fold = folds if folds is not None else [(i % 5) + 1 for i in range(n_train)]
    return {
        'features': features,
        'X': np.zeros((n, len(features))),
        'y': np.ones(n, dtype=int),
        'split': np.array(['train'] * n_train + ['test'] * n_test),
        'cv_fold': np.array(list(fold) + [0] * n_test),
    }


def test_정상_스냅샷은_통과한다():
    integrity.check(_snap())


def test_train_행수가_다르면_거부한다():
    with pytest.raises(ValueError, match='train'):
        integrity.check(_snap(n_train=2000, folds=[(i % 5) + 1 for i in range(2000)]))


def test_test_행수가_다르면_거부한다():
    with pytest.raises(ValueError, match='test'):
        integrity.check(_snap(n_test=500))


def test_변수가_38개가_아니면_거부한다():
    with pytest.raises(ValueError, match='설명변수'):
        integrity.check(_snap(features=['a', 'b']))


def test_fold가_1_5가_아니면_거부한다():
    with pytest.raises(ValueError, match='cv_fold'):
        integrity.check(_snap(folds=[1] * 2398))


def test_배제변수가_섞여_있으면_거부한다():
    feats = [f'f{i}' for i in range(37)] + ['work_care_gap_hours']
    with pytest.raises(ValueError, match='FR-004b'):
        integrity.check(_snap(features=feats))
