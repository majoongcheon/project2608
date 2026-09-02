# -*- coding: utf-8 -*-
"""분기(skip logic) 구조를 결측 패턴에서 복원한다.

이 조사의 결측은 무응답이 아니라 분기다. A 문항에 '해당없음'을 답하면 B 블록
전체를 건너뛴다. 그래서 **같은 게이트에 걸린 컬럼은 결측 행 집합이 정확히 같다.**
코드북 없이 데이터만으로 구조가 나오는 이유다.

게이트를 이진 변수 하나로 승격시키는 이유 — 분기 하나가 컬럼 수십 개를 동시에
비우므로, 그대로 거리를 재면 "취업 경험 없음"이라는 사실 하나가 수십 표를 갖는다.
"""
import collections


def _blank(v):
    return v is None or str(v).strip() == ''


def find_gates(rows, columns, min_columns=2):
    """결측 패턴이 같은 컬럼을 묶어 게이트 목록을 만든다.

    돌려주는 각 항목:
      columns    이 게이트에 걸린 컬럼 이름들
      values     행마다 1(응답함) / 0(건너뜀)
      n_answered 응답한 행 수
    """
    by_pattern = collections.defaultdict(list)
    for c in columns:
        mask = tuple(_blank(r.get(c)) for r in rows)
        if any(mask):
            by_pattern[mask].append(c)

    found = []
    for mask, cols in by_pattern.items():
        if len(cols) < min_columns:
            continue
        values = [0 if m else 1 for m in mask]
        found.append({'columns': sorted(cols),
                      'values': values,
                      'n_answered': sum(values)})
    found.sort(key=lambda g: (-len(g['columns']), g['columns'][0]))
    return found


def gate_matrix(found):
    """게이트 값들을 (행, 게이트) 형태의 리스트로 바꾼다."""
    if not found:
        return []
    n = len(found[0]['values'])
    return [[g['values'][i] for g in found] for i in range(n)]
