"""화면 보기 라벨이 원 조사표와 어긋나지 않게 못을 박는다.

왜 있는가 — 2026-09-03 에 5번 문항(E4)의 보기 15개 중 14개가 원 조사표와
다른 이름을 달고 있었다(`docs/JSG-결함-E4선택지-라벨불일치.md`). 코드값은
모델이 학습한 값이라, 이용자가 "계약 종료"를 고르면 값 1 이 전송되고 모델은
그것을 "낮은 임금 수준"으로 학습한 계수에 넣었다. **조용히 틀린 판정**이다.

`ml/cb_burden/questions.py` 머리말은 "절대 재정렬하지 않는다"고 경고하고
있었지만, 대조할 상대가 없어 지켜지지 않았다. 그 상대를 여기 둔다.

대조표(`fixtures/codebook_labels.json`)는 이름이 아니라 **빈도**로 맞췄다.
코드북은 코드별 빈도를 함께 싣고, 그 숫자가 `cb_dataset_v1` 과 7문항 전수
일치한다. 그러므로 코드→뜻 대응에는 의심의 여지가 없다.

이 테스트가 깨지면 둘 중 하나다.
  ① 라벨을 고쳤는데 대조표를 함께 고치지 않았다 → 대조표를 갱신하고 사람이 본다.
  ② 라벨이 잘못 바뀌었다 → 되돌린다.
어느 쪽이든 **사람이 한 번은 보게 된다.** 그게 이 테스트의 목적이다.
"""
import json
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / 'fixtures' / 'codebook_labels.json'
RELEASE = Path(__file__).resolve().parents[2] / 'models' / 'questions_v1.json'


def _table():
    d = json.loads(FIXTURE.read_text(encoding='utf-8'))
    d.pop('__meta__', None)
    return d


def _deployed():
    d = json.loads(RELEASE.read_text(encoding='utf-8'))
    return {q['feature']: q for q in d['questions']}


def _codes(q):
    """원 조사표의 코드만 남긴다.

    값이 없는 보기 하나는 우리가 덧붙인 "해당사항 없음"이다 — 분기 문항에서
    이용자가 빠져나갈 칸이 필요해서 둔 것이고, 원 조사표의 코드가 아니라
    결측(NULL)으로 전송된다. 대조 대상이 아니다.
    """
    return {str(o['value']): o['label'] for o in q['options'] if o['value'] is not None}


def test_대조표가_배포본_7문항을_모두_덮는다():
    assert set(_table()) == set(_deployed())


@pytest.mark.parametrize('feature', sorted(_table()))
def test_배포_라벨이_검토된_대조표와_같다(feature):
    """검토를 거치지 않은 라벨 변경을 막는다."""
    expected = _table()[feature]['options']
    actual = _codes(_deployed()[feature])
    assert actual == {c: v['service'] for c, v in expected.items()}, (
        f'{feature} 의 보기 라벨이 대조표와 다릅니다. 원 조사표를 다시 보고 '
        f'fixtures/codebook_labels.json 을 함께 고치세요.'
    )


@pytest.mark.parametrize('feature', sorted(_table()))
def test_코드값은_원_조사표_그대로다(feature):
    """라벨은 다듬어도 되지만 코드값은 모델이 학습한 값이라 건드릴 수 없다."""
    expected = sorted(int(c) for c in _table()[feature]['options'])
    actual = sorted(int(c) for c in _codes(_deployed()[feature]))
    assert actual == expected


def test_해당사항_없음_은_코드가_아니라_결측으로_간다():
    """분기 문항의 빠져나갈 칸은 원 조사표에 없는 값이므로 코드를 주면 안 된다.

    코드를 주면 모델이 그 숫자를 유효한 보기로 학습한 계수에 넣는다.
    E4 는 결측 88.1% 인 분기 문항이라 이 칸을 대부분의 이용자가 지나간다.
    """
    for feature, q in _deployed().items():
        extra = [o for o in q['options'] if o['value'] is None]
        if q.get('hasNotApplicable'):
            assert len(extra) == 1, f'{feature}: 해당사항 없음 칸이 {len(extra)}개'
        else:
            assert not extra, f'{feature}: 값 없는 보기가 있으면 안 된다'


def test_알려진_뜻_차이_다섯_건에서_늘어나지_않았다():
    """뜻이 달라진 라벨은 이용자가 다른 칸을 고르게 만든다 — E4 결함과 같은 종류다.

    지금 남아 있는 다섯 건은 기록해 두고 고칠지 함께 정하기로 한 것이다.
    여기서 더 늘어나면 새로 생긴 것이므로 막는다.
    """
    known = {
        ('help_needed_hours', '2'), ('help_needed_hours', '3'), ('help_needed_hours', '4'),
        ('understands_work_meaning', '3'), ('relation_to_person', '7'),
    }
    found = {
        (f, c) for f, v in _table().items()
        for c, o in v['options'].items() if o['verdict'] == 'MEANING_DRIFT'
    }
    assert found == known, f'새로 생긴 뜻 차이: {found - known} · 해소된 것: {known - found}'
