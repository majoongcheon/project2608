"""배포 대상 v1.0.0 의 모델·데이터 전수 분석 (읽기 전용).

문서 `docs/HG_모델-데이터-분석-v1.0.0.md` 의 모든 수치를 여기서 만든다. 문서에 손으로
숫자를 옮겨 적지 않으려면 이 파일을 다시 돌리면 된다(원칙 IV).

    PYTHONPATH=ml/.pylibs python3 ml/HG_analyze_v1.py

test 602건은 `train.py --stage evaluate` 에서 한 번 쓰였다. 여기서 다시 계산하는 것은
**모든 결정이 끝난 뒤 배포 판단을 위한 보고**이므로 ml/README.md 의 규칙에 어긋나지 않는다.
새 결정을 내리는 데 쓰지 않는다.
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'ml' / '.pylibs'))
sys.path.insert(0, str(ROOT / 'ml'))

import joblib                                    # noqa: E402
import numpy as np                               # noqa: E402
from db import load_dataset                      # noqa: E402

MODELS = ROOT / 'models'
EPS = 1e-4
CLASSES = [1, 2, 3, 4, 5]
NAMES = {1: '최고부담군', 2: '고부담군', 3: '중간부담군', 4: '저부담군', 5: '부담 없음'}


def rarity(features, freq_table, row):
    s = 0.0
    for j, f in enumerate(features):
        p = freq_table.get(f, {}).get(str(int(row[j])), EPS)
        s += np.log(max(p, EPS))
    return s / len(features)


def prf(cm, i):
    """혼동행렬에서 클래스 i 의 정밀도·재현율·F1"""
    tp = cm[i, i]
    p = tp / cm[:, i].sum() if cm[:, i].sum() else 0.0
    r = tp / cm[i, :].sum() if cm[i, :].sum() else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f


def section(t):
    print('\n' + '=' * 78)
    print(t)
    print('=' * 78)


def main():
    bundle = joblib.load(MODELS / 'model_v1.joblib')
    payload = json.loads((MODELS / 'model_v1.json').read_text(encoding='utf-8'))
    unc = json.loads((MODELS / 'uncertainty_v1.json').read_text(encoding='utf-8'))
    sel = json.loads((MODELS / 'selection_v1.json').read_text(encoding='utf-8'))
    qs = json.loads((MODELS / 'questions_v1.json').read_text(encoding='utf-8'))
    contrib = json.loads((MODELS / 'contribution_v1.json').read_text(encoding='utf-8'))

    feats = bundle['features']
    enc, clf, weights = bundle['encoder'], bundle['model'], bundle['decision_weights']
    tau_conf, tau_dens = unc['tau_conf'], unc['tau_dens']

    d = load_dataset()
    all_feats = d['features']
    # db.py 는 train/test 를 따로 준다. 한 배열로 합치고 split 표시를 만든다.
    X = np.vstack([d['X'], d['Xtest']])
    y = np.concatenate([d['y'], d['ytest']])
    split = np.array(['train'] * len(d['y']) + ['test'] * len(d['ytest']))
    fold = np.concatenate([d['folds'], np.zeros(len(d['ytest']), int)])
    cols = [all_feats.index(f) for f in feats]
    Xs = X[:, cols]

    section('1. 데이터')
    print(f'총 {len(y)}행 · 설명변수 {len(all_feats)}개 → 선택 {len(feats)}개')
    for s in ('train', 'test'):
        m = split == s
        print(f'  {s:5s} {m.sum():5d}행')
    print('  cv_fold:', dict(sorted(Counter(fold[split == "train"]).items())))

    print('\ntarget(care_burden) 분포 — 1이 최고부담인 역방향 척도')
    for s in ('전체', 'train', 'test'):
        m = np.ones(len(y), bool) if s == '전체' else (split == ('train' if s == 'train' else 'test'))
        c = Counter(y[m])
        hi = (c[1] + c[2]) / m.sum() * 100
        print(f'  {s:5s} ' + ' '.join(f'{k}:{c[k]:5d}({c[k]/m.sum()*100:4.1f}%)' for k in CLASSES)
              + f'  고부담 {hi:.1f}%')

    section('2. 선택된 7문항')
    qmap = {q['feature']: q for q in qs['questions']}
    print(f'{"문항":<32} {"결측":>6} {"범주":>4}  최빈 응답')
    for j, f in enumerate(feats):
        col = Xs[:, j]
        miss = (col == payload['missing_sentinel']).mean() * 100
        cats = payload['categories'][j]
        top = Counter(col).most_common(1)[0]
        q = qmap[f]
        lab = next((o['label'] for o in q['options'] if o['value'] == top[0]), f'값 {int(top[0])}')
        print(f'{f:<32} {miss:5.1f}% {len(cats):4d}  {lab} ({top[1]/len(col)*100:.1f}%)')

    section('3. 모델 구조')
    print(f"계열 {payload['family']} · 계수 {clf.coef_.shape[0]}x{clf.coef_.shape[1]} "
          f"· 원-핫 {clf.coef_.shape[1]}열 · 결정 가중치 {weights}")
    print(f"기여 요인 강약 임계값 {contrib['min_threshold']:.5f} ({contrib['basis']})")
    print('\n문항별 영향력 — 계수 절댓값의 최대(고부담 1·2 쪽으로 미는 힘)')
    for j, f in enumerate(feats):
        a, w = payload['spans'][j]
        blk = np.array(payload['coef'])[:, a:a + w]
        hi = blk[0:2, :].sum(axis=0)                       # 라벨 1·2 계수 합
        print(f'  {f:<32} |coef|max {np.abs(blk).max():6.3f}   고부담쪽 최대 {hi.max():+6.3f}')

    section('4. 성능')
    Xoh = enc.transform(Xs.astype(float))
    proba = clf.predict_proba(Xoh)
    rar = np.array([rarity(feats, unc['freq_table'], r) for r in Xs])
    amb, sp = proba.max(axis=1) < tau_conf, rar < tau_dens
    und = amb | sp
    wt = np.array(weights)
    pred = np.array(CLASSES)[np.argmax(proba * wt, axis=1)]

    for s in ('train', 'test'):
        m = split == s
        n = m.sum()
        print(f'\n--- {s} {n}행 ---')
        print(f'판정 불가 {und[m].sum()}건 ({und[m].mean()*100:.2f}%) '
              f'= 희소성 {(sp[m]).sum()} + 확신부족 {(amb[m] & ~sp[m]).sum()}')
        dec = m & ~und
        cm = np.zeros((5, 5), int)
        for t, p in zip(y[dec], pred[dec]):
            cm[t - 1, p - 1] += 1
        print(f'혼동행렬 (판정된 {dec.sum()}건) — 행=실제, 열=예측')
        print('      ' + ''.join(f'{c:>7}' for c in CLASSES) + '     실제계')
        for i, c in enumerate(CLASSES):
            print(f'  {c:>3} ' + ''.join(f'{v:>7}' for v in cm[i]) + f'{cm[i].sum():>10}')
        print('  예측계' + ''.join(f'{v:>7}' for v in cm.sum(axis=0)))
        f1s = []
        print('\n  클래스별  정밀도  재현율    F1')
        for i, c in enumerate(CLASSES):
            p, r, f1 = prf(cm, i)
            f1s.append(f1)
            print(f'  {c} {NAMES[c]:<8} {p:6.3f} {r:7.3f} {f1:6.3f}')
        print(f'  macro F1 {np.mean(f1s):.4f} · 정확도 {np.trace(cm)/cm.sum():.4f}')
        hi_t, hi_p = y[dec] <= 2, pred[dec] <= 2
        tp = (hi_t & hi_p).sum()
        print(f'  고부담(1~2) 이진 — 재현율 {tp/hi_t.sum():.4f} · 정밀도 {tp/hi_p.sum():.4f} '
              f'· 정확도 {(hi_t == hi_p).mean():.4f}')
        # SC-016: 판정 불가군의 오분류율이 더 높아야 한다
        eu = (pred[m & und] != y[m & und]).mean() if (m & und).sum() else float('nan')
        ed = (pred[dec] != y[dec]).mean()
        print(f'  SC-016 오분류율 — 판정불가군 {eu:.4f} vs 판정군 {ed:.4f} '
              f'→ {"PASS" if eu > ed else "FAIL"}')

    section('5. 판정 불가 임계값 근거')
    print(f"확신도 tau_conf {tau_conf:.6f} · 희소성 tau_dens {tau_dens:.6f}")
    print(f"학습 시 기록 — 발생률 {unc['rate']*100:.2f}% · "
          f"판정불가 오분류 {unc['err_undecidable']:.4f} · 판정 오분류 {unc['err_decided']:.4f}")
    print(f"전체 3,000건 재계산 — 판정불가 {und.sum()}건 ({und.mean()*100:.2f}%) "
          f"= 희소성만 {(sp & ~amb).sum()} · 확신부족만 {(amb & ~sp).sum()} · 둘 다 {(sp & amb).sum()}")

    section('6. 확률 보정 (ECE)')
    # 모델이 "60% 확신"이라 말할 때 실제로 60% 맞는가. 10구간으로 나눠 차이를 가중 평균한다.
    for s_ in ('train', 'test'):
        m = split == s_
        # ECE 는 모델 자신의 최대확률 예측을 기준으로 본다 — 결정 가중치를 뺀 순수 argmax.
        raw = np.array(CLASSES)[proba[m].argmax(axis=1)]
        conf, ok = proba[m].max(axis=1), (raw == y[m]).astype(float)
        edges = np.linspace(0, 1, 11)
        e = 0.0
        for i in range(10):
            b_ = (conf > edges[i]) & (conf <= edges[i + 1])
            if b_.sum():
                e += b_.sum() / m.sum() * abs(ok[b_].mean() - conf[b_].mean())
        print(f'  {s_:5s} ECE {e:.4f} · 평균 확신도 {conf.mean():.4f} vs 실제 정확도 {ok.mean():.4f}')

    section('7. 대안 비교 (학습 시 기록)')
    fc = sel['family_comparison']
    print(f'{"계열":<6}{"macro F1":>10}{"고부담 재현율":>14}')
    for k, v in fc.items():
        print(f'{k:<6}{v["macro_f1"]:>10.4f}{v["high_burden_recall"]:>14.4f}')
    h = sel['history']
    print(f'\n후진 제거 {len(h)}단계 — 38개에서 시작해 {sel["k"]}개에서 멈춤')
    print(f'  중단 규칙 {json.dumps(sel["stop_rule"], ensure_ascii=False)}')
    print(f'  38개 시작 macro F1 {h[0]["macro_f1"]:.4f} · 재현율 {h[0]["high_burden_recall"]:.4f}')
    last = [x for x in h if x['k'] == sel['k']]
    if last:
        print(f'  {sel["k"]}개 도달 macro F1 {last[-1]["macro_f1"]:.4f} '
              f'· 재현율 {last[-1]["high_burden_recall"]:.4f}')
    print(f'  제거 순서(앞 10개) {sel["dropped_order"][:10]}')


if __name__ == '__main__':
    main()
