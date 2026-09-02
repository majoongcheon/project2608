"""sklearn 버전 대조 — joblib 은 만든 버전과 읽는 버전이 같아야 한다.

다르면 sklearn 이 InconsistentVersionWarning 을 내며 "결과가 잘못될 수 있다"고 알린다.
경고만으로 두면 **조용히 틀린 판정**이 나갈 수 있으므로 기동을 막는다.
2026-09-02 실제로 conda 파이썬(sklearn 1.9.0)으로 열었을 때 이 경고가 나왔다.
"""
import joblib
import pytest
import sklearn

from cb_burden.serve import engine

RELEASE = 'models'


def _bundle_with(tmp_path, version):
    """sklearn_version 만 바꾼 릴리스 사본을 만든다."""
    import shutil
    from pathlib import Path
    d = tmp_path / 'rel'
    d.mkdir()
    src = Path(RELEASE)
    for name in ('model_v1.json', 'uncertainty_v1.json', 'questions_v1.json'):
        shutil.copy(src / name, d / name)
    b = joblib.load(src / 'model_v1.joblib')
    b['sklearn_version'] = version
    joblib.dump(b, d / 'model_v1.joblib')
    return d


def test_버전이_같으면_로드된다(tmp_path):
    d = _bundle_with(tmp_path, sklearn.__version__)
    assert engine.Engine.load(d) is not None


def test_버전이_다르면_기동을_막는다(tmp_path):
    d = _bundle_with(tmp_path, '1.9.0')
    with pytest.raises(ValueError, match='sklearn'):
        engine.Engine.load(d)


def test_오류_메시지가_두_버전과_해결법을_알려준다(tmp_path):
    d = _bundle_with(tmp_path, '1.9.0')
    with pytest.raises(ValueError) as e:
        engine.Engine.load(d)
    msg = str(e.value)
    assert '1.9.0' in msg and sklearn.__version__ in msg
    assert 'requirements.txt' in msg


def test_환경변수로_무시할_수_있다(tmp_path, monkeypatch):
    # 운영 중 급할 때의 탈출구. 다만 기본은 막는 쪽이다.
    monkeypatch.setenv('CB_ALLOW_SKLEARN_MISMATCH', '1')
    d = _bundle_with(tmp_path, '1.9.0')
    assert engine.Engine.load(d) is not None


def test_기록이_없는_옛_파일은_통과시킨다(tmp_path):
    # sklearn_version 을 안 넣던 시절의 파일까지 막을 이유는 없다
    d = _bundle_with(tmp_path, None)
    import joblib as jl
    b = jl.load(d / 'model_v1.joblib')
    del b['sklearn_version']
    jl.dump(b, d / 'model_v1.joblib')
    assert engine.Engine.load(d) is not None
