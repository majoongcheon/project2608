# -*- coding: utf-8 -*-
"""원본 507컬럼 군집화 실험 단위 테스트.

DB 와 3,000행 CSV 없이 돌아야 한다. 모든 입력은 이 파일 안에서 만든다.
"""
import numpy as np
import pytest

from sjh_cluster import load


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


from sjh_cluster import clean


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
