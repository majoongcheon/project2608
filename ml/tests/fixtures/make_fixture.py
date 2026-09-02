"""테스트용 합성 스냅샷. 실제 데이터가 아니다(원칙 III).

분포만 흉내 낸다. 이 픽스처로 만든 결과는 성능 판단에 쓰지 않는다 —
단계가 끝까지 도는지, 규약을 지킨 산출물이 나오는지만 본다.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'ml' / '.pylibs'))
from cb_burden.questions import QUESTIONS                      # noqa: E402
from cb_burden.data import snapshot                            # noqa: E402

N_TRAIN, N_TEST = 240, 60
rng = np.random.RandomState(0)

# 실제 문항 정의에 있는 선택형 변수만 쓴다 — export 가 build_question 을 호출하기 때문이다.
# 수치형(type: number)은 원-핫 범주가 커져 합성 데이터에 맞지 않아 제외한다.
features = sorted(f for f, q in QUESTIONS.items() if 'options' in q)[:8]
rows = []
for i in range(N_TRAIN + N_TEST):
    train = i < N_TRAIN
    r = {'split': 'train' if train else 'test',
         'cv_fold': (i % 5) + 1 if train else 0,
         'care_burden': int(rng.choice([1, 2, 3, 4, 5], p=[.15, .39, .30, .13, .03]))}
    for f in features:
        opts = [v for v, _ in QUESTIONS[f]['options']]
        r[f] = float(rng.choice(opts))
    rows.append(r)

out = Path(__file__).parent / 'mini_snapshot.csv.gz'
if out.exists():
    out.unlink()
    snapshot.meta_path(out).unlink(missing_ok=True)
snapshot.write(out, features, rows, source_view='synthetic')
print(f'생성 {out.name} · {len(rows)}행 · 변수 {len(features)}개')
