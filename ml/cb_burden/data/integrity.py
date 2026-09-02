"""스냅샷 무결성. ml/db.py 의 assert 를 옮겨 예외로 바꾼 것이다.

assert 는 python -O 에서 사라진다. 판정 근거가 걸린 검사라 예외로 둔다.
"""
from cb_burden import config


def check(snap):
    feats = list(snap['features'])
    split = snap['split']
    n_train = int((split == 'train').sum())
    n_test = int((split == 'test').sum())

    if n_train != config.EXPECTED_TRAIN:
        raise ValueError(f'train 이 {config.EXPECTED_TRAIN} 이 아닙니다: {n_train}')
    if n_test != config.EXPECTED_TEST:
        raise ValueError(f'test 가 {config.EXPECTED_TEST} 가 아닙니다: {n_test}')
    if len(feats) != config.EXPECTED_FEATURES:
        raise ValueError(f'설명변수가 {config.EXPECTED_FEATURES}개가 아닙니다: {len(feats)}')

    folds = sorted({int(v) for v in snap['cv_fold'][split == 'train']})
    if folds != config.EXPECTED_FOLDS:
        raise ValueError(f'cv_fold 가 {config.EXPECTED_FOLDS} 가 아닙니다: {folds}')

    leaked = config.EXCLUDED_FEATURES & set(feats)
    if leaked:
        raise ValueError(f'FR-004b 로 배제된 변수가 입력에 있습니다: {sorted(leaked)}')
    return True
