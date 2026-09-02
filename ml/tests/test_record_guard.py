"""DB 기록 — 2026-09-01 에 v1.0.0 성능 기록이 14문항 결과로 덮인 사고를 막는다."""
import pytest
from cb_burden.data import record


class FakeCursor:
    def __init__(self, existing):
        self.existing, self.calls = existing, []

    def execute(self, sql, args=None):
        self.calls.append((sql, args))

    def fetchone(self):
        return (1,) if self.existing else (0,)


class FakeConn:
    def __init__(self, existing=False):
        self.cur = FakeCursor(existing)
        self.committed = False

    def cursor(self):
        return self.cur

    def commit(self):
        self.committed = True


def test_모델_버전이_없으면_거부한다():
    with pytest.raises(ValueError, match='model_version'):
        record.write(FakeConn(), model_version='', family='logit', qset='q',
                     f1=0.3, rec=0.8, und=0.02, notes='{}')


def test_이미_있는_행은_force_없이_거부한다():
    c = FakeConn(existing=True)
    with pytest.raises(ValueError, match='이미'):
        record.write(c, model_version='v1.0.0', family='logit', qset='q',
                     f1=0.3, rec=0.8, und=0.02, notes='{}')
    assert not c.committed          # 아무것도 쓰지 않았다


def test_force_면_덮어쓴다():
    c = FakeConn(existing=True)
    record.write(c, model_version='v1.0.0', family='logit', qset='q',
                 f1=0.3, rec=0.8, und=0.02, notes='{}', force=True)
    assert any('INSERT' in sql for sql, _ in c.cur.calls)
    assert c.committed


def test_새_행은_그냥_기록된다():
    c = FakeConn(existing=False)
    record.write(c, model_version='v1.0.1', family='logit', qset='q',
                 f1=0.3, rec=0.8, und=0.02, notes='{}')
    assert any('INSERT' in sql for sql, _ in c.cur.calls)


def test_값이_반올림되어_들어간다():
    c = FakeConn(existing=False)
    record.write(c, model_version='v1.0.1', family='logit', qset='q',
                 f1=0.34164321, rec=0.77298, und=0.024916, notes='{}')
    args = [a for sql, a in c.cur.calls if 'INSERT' in sql][0]
    assert args[3] == 0.3416 and args[4] == 0.773 and args[5] == 0.0249
