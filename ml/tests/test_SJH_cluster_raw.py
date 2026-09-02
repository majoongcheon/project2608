# -*- coding: utf-8 -*-
"""원본 507컬럼 군집화 실험 단위 테스트.

DB 와 3,000행 CSV 없이 돌아야 한다. 모든 입력은 이 파일 안에서 만든다.
"""
import numpy as np
import pytest

from SJH_cluster_raw import load


def test_join_by_value_tuple_붙인다():
    """값 튜플이 유일하면 split 이 정확히 붙는다."""
    raw = [
        {'ID': '1', 'A1': '1', 'G6': '3', 'I13': '2'},
        {'ID': '2', 'A1': '2', 'G6': '4', 'I13': '5'},
    ]
    db = [
        {'relation_to_person': 2, 'help_needed_hours': 4, 'care_burden': 5,
         'split': 'test', 'cv_fold': None},
        {'relation_to_person': 1, 'help_needed_hours': 3, 'care_burden': 2,
         'split': 'train', 'cv_fold': 3},
    ]
    mapping = {'relation_to_person': 'A1', 'help_needed_hours': 'G6'}

    out = load.join_split(raw, db, mapping)

    # raw[0] 은 (A1=1, G6=3, I13=2) → db[1] 과 일치
    assert out[0]['__split'] == 'train'
    assert out[0]['__cv_fold'] == 3
    assert out[1]['__split'] == 'test'


def test_join_중복_튜플이면_예외():
    """같은 값 조합이 둘 이상이면 조인이 모호하므로 멈춘다."""
    raw = [{'ID': '1', 'A1': '1', 'I13': '2'}, {'ID': '2', 'A1': '1', 'I13': '2'}]
    db = [{'relation_to_person': 1, 'care_burden': 2, 'split': 'train', 'cv_fold': 1},
          {'relation_to_person': 1, 'care_burden': 2, 'split': 'test', 'cv_fold': None}]

    with pytest.raises(load.JoinError, match='중복'):
        load.join_split(raw, db, {'relation_to_person': 'A1'})


def test_join_매칭_실패하면_예외():
    raw = [{'ID': '1', 'A1': '9', 'I13': '2'}]
    db = [{'relation_to_person': 1, 'care_burden': 2, 'split': 'train', 'cv_fold': 1}]

    with pytest.raises(load.JoinError, match='매칭'):
        load.join_split(raw, db, {'relation_to_person': 'A1'})


def test_join_DB에_없는_컬럼이_매핑에_있으면_예외():
    """컬럼정의서와 DB 스키마가 어긋나면 조용히 넘기지 않는다."""
    raw = [{'ID': '1', 'A1': '1', 'I13': '2'}]
    db = [{'relation_to_person': 1, 'care_burden': 2, 'split': 'train', 'cv_fold': 1}]

    with pytest.raises(load.JoinError, match='DB 에 없는 컬럼'):
        load.join_split(raw, db, {'없는컬럼': 'A1'})


def test_join_무응답코드는_NULL_로_통일된다():
    """원본의 999(나이 무응답)를 DB 는 NULL 로 저장했다. 같은 것으로 봐야 조인된다."""
    raw = [{'ID': '1', 'A6': '999', 'I13': '2'}]
    db = [{'age_disability_suspected': None, 'care_burden': 2,
           'split': 'train', 'cv_fold': 1}]

    out = load.join_split(raw, db, {'age_disability_suspected': 'A6'})
    assert out[0]['__split'] == 'train'


def test_join_유효한_9는_NULL_이_아니다():
    """secondary_caregiver_type 의 9 는 "9. 없음"이라는 유효한 보기다(518건)."""
    raw = [{'ID': '1', 'I8_2': '9', 'I13': '2'}]
    db = [{'secondary_caregiver_type': 9, 'care_burden': 2, 'split': 'test', 'cv_fold': None}]

    out = load.join_split(raw, db, {'secondary_caregiver_type': 'I8_2'})
    assert out[0]['__split'] == 'test'


from SJH_cluster_raw import clean


def test_drop_전부결측_상수_식별자():
    rows = [
        {'ID': '1', 'ADDCODE': '11', 'WT': '1.0', 'I13': '2', 'ALLNA': '', 'CONST': '7', 'OK': '1'},
        {'ID': '2', 'ADDCODE': '12', 'WT': '2.0', 'I13': '3', 'ALLNA': '', 'CONST': '7', 'OK': '2'},
    ]
    keep, reasons = clean.select_columns(rows, min_respondents=1)

    assert keep == ['OK']
    assert reasons['ALLNA'] == '전부결측'
    assert reasons['CONST'] == '상수'
    assert reasons['ID'] == '식별자'
    assert reasons['ADDCODE'] == '식별자'
    assert reasons['WT'] == '조사가중치'
    assert reasons['I13'] == 'target'


def test_drop_주관식_텍스트():
    rows = [{'X_op': '기타 사유입니다', 'N': '1'}, {'X_op': '', 'N': '2'}]
    keep, reasons = clean.select_columns(rows, min_respondents=1)
    assert keep == ['N']
    assert reasons['X_op'] == '주관식'


def test_drop_응답자_적은_블록():
    rows = [{'RARE': '1' if i == 0 else '', 'OK': str(i)} for i in range(10)]
    keep, reasons = clean.select_columns(rows, min_respondents=5)
    assert 'RARE' not in keep
    assert reasons['RARE'] == '응답자 1명 < 5'
    assert 'OK' in keep


from SJH_cluster_raw import gates


def _gate_rows():
    """행 1,2 는 E 블록에 응답, 행 0,3 은 미응답."""
    return [
        {'E1': '',  'E2': '',  'A1': '1'},
        {'E1': '5', 'E2': '3', 'A1': '2'},
        {'E1': '4', 'E2': '2', 'A1': '1'},
        {'E1': '',  'E2': '',  'A1': '2'},
    ]


def test_같은_결측패턴_컬럼은_게이트_하나로():
    found = gates.find_gates(_gate_rows(), ['E1', 'E2', 'A1'], min_columns=2)

    assert len(found) == 1
    g = found[0]
    assert sorted(g['columns']) == ['E1', 'E2']
    assert g['values'] == [0, 1, 1, 0]
    assert g['n_answered'] == 2


def test_결측이_없으면_게이트가_없다():
    rows = [{'A1': '1'}, {'A1': '2'}]
    assert gates.find_gates(rows, ['A1'], min_columns=2) == []


def test_혼자인_결측패턴은_게이트가_아니다():
    """min_columns 미만이면 분기가 아니라 개별 무응답으로 본다."""
    rows = [{'A1': '', 'B1': '1'}, {'A1': '2', 'B1': '2'}]
    assert gates.find_gates(rows, ['A1', 'B1'], min_columns=2) == []


def test_게이트_행렬은_행마다_게이트값():
    found = gates.find_gates(_gate_rows(), ['E1', 'E2', 'A1'], min_columns=2)
    assert gates.gate_matrix(found) == [[0], [1], [1], [0]]


from SJH_cluster_raw import scales


def test_이진은_binary():
    assert scales.judge('A2', ['1', '2', '1', '2']) == 'binary'


def test_연속형은_continuous():
    vals = [str(v) for v in range(20, 90)]      # 고유값 70개
    assert scales.judge('I9_2', vals) == 'continuous'


def test_작은_정수_연속범위는_ordinal():
    assert scales.judge('G6', ['1', '2', '3', '4', '5', '3', '2']) == 'ordinal'


def test_구멍이_있으면_nominal():
    """1,2,3,9 처럼 코드가 띄엄띄엄하면 순서 척도로 보지 않는다."""
    assert scales.judge('I8_2', ['1', '2', '3', '9']) == 'nominal'


def test_숫자가_아니면_nominal():
    assert scales.judge('D13', ['가', '나', '다']) == 'nominal'


def test_판정표를_한번에():
    rows = [{'A2': '1', 'G6': '1'}, {'A2': '2', 'G6': '2'}, {'A2': '1', 'G6': '3'}]
    assert scales.judge_all(rows, ['A2', 'G6']) == {'A2': 'binary', 'G6': 'ordinal'}


from SJH_cluster_raw import gower


def test_같은_행은_거리0():
    D = gower.distance(np.array([[1.0, 3.0], [1.0, 3.0]]), ['binary', 'ordinal'])
    assert D.shape == (2, 2)
    assert D[0, 1] == pytest.approx(0.0)
    assert D[0, 0] == pytest.approx(0.0)


def test_대칭이다():
    X = np.array([[1.0, 3.0], [2.0, 5.0], [1.0, 1.0]])
    D = gower.distance(X, ['nominal', 'ordinal'])
    assert np.allclose(D, D.T)


def test_이진은_일치_불일치():
    D = gower.distance(np.array([[1.0], [2.0]]), ['binary'])
    assert D[0, 1] == pytest.approx(1.0)


def test_순서형은_범위로_정규화():
    """1~5 척도에서 1 과 3 의 거리는 (3-1)/(5-1) = 0.5."""
    D = gower.distance(np.array([[1.0], [3.0], [5.0]]), ['ordinal'])
    assert D[0, 1] == pytest.approx(0.5)
    assert D[0, 2] == pytest.approx(1.0)


def test_결측은_쌍에서_제외된다():
    """두 변수 중 하나가 결측이면 나머지 하나로만 잰다."""
    D = gower.distance(np.array([[1.0, 1.0], [1.0, np.nan]]), ['binary', 'binary'])
    assert D[0, 1] == pytest.approx(0.0)


def test_모두_결측이면_거리1():
    """비교할 변수가 하나도 없으면 최대 거리로 둔다 — 임의로 가깝다고 하지 않는다."""
    D = gower.distance(np.array([[np.nan], [np.nan]]), ['binary'])
    assert D[0, 1] == pytest.approx(1.0)


def test_가중치가_반영된다():
    Y = np.array([[1.0, 1.0], [1.0, 2.0]])      # 두 번째 변수만 불일치
    assert gower.distance(Y, ['binary', 'binary'], [1.0, 1.0])[0, 1] == pytest.approx(0.5)
    assert gower.distance(Y, ['binary', 'binary'], [1.0, 3.0])[0, 1] == pytest.approx(0.75)


def test_블록_가중치는_문항수로_나눈다():
    """같은 게이트에 딸린 문항 3개는 각각 1/3 의 표를 갖는다."""
    w = gower.block_weights(['A', 'B', 'C', 'D'], {'A': 'g1', 'B': 'g1', 'C': 'g1'})
    assert w == pytest.approx([1 / 3, 1 / 3, 1 / 3, 1.0])


from SJH_cluster_raw import cluster


def _two_blobs():
    """0,1 은 서로 가깝고 2,3 도 서로 가깝다. 두 덩어리 사이는 멀다."""
    return np.array([
        [0.0, 0.1, 0.9, 0.9],
        [0.1, 0.0, 0.9, 0.9],
        [0.9, 0.9, 0.0, 0.1],
        [0.9, 0.9, 0.1, 0.0],
    ])


def test_pam_두덩어리를_찾는다():
    labels = cluster.pam(_two_blobs(), k=2, seed=1)
    assert labels[0] == labels[1]
    assert labels[2] == labels[3]
    assert labels[0] != labels[2]


def test_pam_같은_시드는_같은_결과():
    D = _two_blobs()
    assert np.array_equal(cluster.pam(D, k=2, seed=7), cluster.pam(D, k=2, seed=7))


def test_pam_라벨은_0부터_k미만():
    assert set(cluster.pam(_two_blobs(), k=2, seed=1).tolist()) == {0, 1}


def test_계층군집도_두덩어리를_찾는다():
    labels = cluster.hierarchical(_two_blobs(), k=2)
    assert labels[0] == labels[1]
    assert labels[2] == labels[3]
    assert labels[0] != labels[2]


from SJH_cluster_raw import score


def test_고부담_리프트():
    """군집 0 은 전원 고부담(1,2), 군집 1 은 전원 저부담."""
    y = np.array([1, 2, 1, 4, 5, 3])
    labels = np.array([0, 0, 0, 1, 1, 1])
    lift = score.high_burden_lift(labels, y)

    assert lift[0]['n'] == 3
    assert lift[0]['high_ratio'] == pytest.approx(1.0)
    assert lift[0]['lift'] == pytest.approx(2.0)      # 전체 고부담 비율 0.5
    assert lift[1]['high_ratio'] == pytest.approx(0.0)


def test_교차표():
    """군집 × 부담구간 교차표. 스펙 §6 이 ARI 와 함께 보라고 한 것."""
    y = np.array([1, 2, 3, 1, 5])
    labels = np.array([0, 0, 0, 1, 1])
    ct = score.crosstab(labels, y)
    assert ct[0] == {1: 1, 2: 1, 3: 1, 4: 0, 5: 0}
    assert ct[1] == {1: 1, 2: 0, 3: 0, 4: 0, 5: 1}


def test_게이트_오염도_완전일치면_1():
    labels = np.array([0, 0, 1, 1])
    gate_rows = [[1, 0], [1, 0], [0, 1], [0, 1]]
    assert score.gate_contamination(labels, gate_rows) == pytest.approx(1.0)


def test_게이트_오염도_게이트가_상수면_0():
    labels = np.array([0, 1, 0, 1])
    gate_rows = [[1], [1], [1], [1]]
    assert score.gate_contamination(labels, gate_rows) == pytest.approx(0.0)


def test_널판정_상위5퍼센트_밖이면_구조있음():
    verdict = score.null_verdict(observed=0.30, null_scores=[0.10] * 20)
    assert verdict['structured'] is True
    assert verdict['p_value'] == pytest.approx(0.0)


def test_널판정_널분포와_겹치면_구조없음():
    verdict = score.null_verdict(observed=0.11, null_scores=[0.10, 0.12, 0.11, 0.13])
    assert verdict['structured'] is False
