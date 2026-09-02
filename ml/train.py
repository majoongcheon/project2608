# -*- coding: utf-8 -*-
"""오프라인 학습 파이프라인 (research.md R-1·R-4·R-5·R-6).

런타임에는 실행되지 않는다. 산출물 models/*.json 만 배포된다.

  python3 ml/train.py all        # baseline → select → calibrate → export
  python3 ml/train.py evaluate   # test 602건 1회 평가 (모든 결정이 끝난 뒤)

★ test 602건은 evaluate 에서 단 한 번만 사용한다. 그 전 단계는 train 2,398건의
  cv_fold 5-fold 만 쓴다. 섞으면 SC-004·SC-005 가 낙관 편향된다.
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'ml' / '.pylibs'))

import numpy as np                                                    # noqa: E402
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier  # noqa: E402
from sklearn.linear_model import LogisticRegression                   # noqa: E402
from sklearn.preprocessing import OneHotEncoder                       # noqa: E402
from sklearn.metrics import f1_score                                  # noqa: E402

from questions import QUESTIONS, SELF_REPORT, build_question          # noqa: E402
import db as dbmod                                                    # noqa: E402

MODELS = ROOT / os.getenv('MODELS_DIR', 'models')
MODELS.mkdir(parents=True, exist_ok=True)

SEED = 20260901
MISSING = -1          # 결측 센티널. 모든 코드값이 0 이상이라 -1 이 안전하게 분리된다
CLASSES = [1, 2, 3, 4, 5]
MODEL_VERSION = os.getenv('MODEL_VERSION', 'v1.0.0')
QSET_VERSION = os.getenv('QSET_VERSION', 'qs-v1.0.0')

# SC-004·SC-005 정지 조건
MAX_F1_LOSS = 0.03
MAX_REC_LOSS = 0.05
MIN_REC_ABS = 0.70
REC_MARGIN = 0.03      # CV 에서 하한 + 마진을 확보해 test 에서의 변동을 흡수한다
F1_MARGIN = 0.01       # 같은 이유. CV 에서 최소 k 를 그대로 고르면 잡음에 선택이 과적합된다

# 문항 수를 규칙 대신 사람이 정할 때 쓴다. 0 이면 기존 규칙(최소 k)을 그대로 따른다.
# 성능 최적점이 아니라 제품 판단이므로 selection json 에 출처를 함께 기록한다.
K_TARGET = int(os.getenv('K_TARGET', '0'))


# ─────────────────────────────────────────────────────────── 지표
def macro_f1(y, p):
    return float(f1_score(y, p, average='macro', labels=CLASSES, zero_division=0))


def high_burden_recall(y, p):
    """실제 고부담(1~2)인 사람 중 시스템도 고부담으로 판정한 비율 (SC-005)."""
    y, p = np.asarray(y), np.asarray(p)
    actual = (y <= 2)
    if actual.sum() == 0:
        return 0.0
    return float(((p <= 2) & actual).sum() / actual.sum())


def decide(proba, weights=None):
    """확률에서 최종 구간을 고른다.

    고부담(1~2)을 놓치는 것이 이 서비스에서 가장 비싼 오류이므로(SC-005),
    단순 argmax 가 아니라 **구간별 결정 가중치**를 곱해 고른다. 가중치는 학습 데이터에서
    도출하며(원칙 I) 모델 아티팩트에 실려 런타임이 동일한 규칙을 쓴다(원칙 IV).
    """
    p = np.asarray(proba, dtype=float)
    if weights is not None:
        p = p * np.asarray(weights, dtype=float)
    return np.asarray(CLASSES)[p.argmax(axis=1)]


def tune_decision_weights(proba, y):
    """고부담 재현율 하한을 만족하는 가중치 중 macro F1 이 가장 높은 것을 고른다."""
    best = (None, -1.0, 0.0)
    for boost in np.arange(1.0, 3.01, 0.05):
        w = [boost, boost, 1.0, 1.0, 1.0]
        pred = decide(proba, w)
        rec = high_burden_recall(y, pred)
        f1 = macro_f1(y, pred)
        if rec >= MIN_REC_ABS + REC_MARGIN and f1 > best[1]:
            best = (w, f1, rec)
    if best[0] is None:                     # 하한을 못 맞추면 재현율이 가장 높은 쪽
        for boost in np.arange(1.0, 4.01, 0.05):
            w = [boost, boost, 1.0, 1.0, 1.0]
            rec = high_burden_recall(y, decide(proba, w))
            if rec > best[2]:
                best = (w, macro_f1(y, decide(proba, w)), rec)
    return list(best[0]), {'macro_f1': best[1], 'high_burden_recall': best[2]}


def make_model(family):
    if family == 'rf':
        return RandomForestClassifier(
            n_estimators=180, max_depth=14, min_samples_leaf=8, max_features='sqrt',
            class_weight=None, random_state=SEED, n_jobs=-1)
    if family == 'et':
        return ExtraTreesClassifier(
            n_estimators=180, max_depth=16, min_samples_leaf=8, max_features='sqrt',
            class_weight=None, random_state=SEED, n_jobs=-1)
    if family == 'logit':
        return 'logit'
    raise ValueError(family)


def cv_scores(X, y, folds, features, family='rf', want_importance=False, want_oof=False, weights=None):
    """cv_fold 로 고정된 5-fold 교차검증. 분할을 새로 만들지 않는다(원칙 IV)."""
    f1s, recs = [], []
    imp = np.zeros(len(features))
    oof_proba = np.zeros((len(y), len(CLASSES)))
    for k in sorted(set(folds)):
        tr, va = folds != k, folds == k
        if family == 'logit':
            enc = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
            Xtr, Xva = enc.fit_transform(X[tr]), enc.transform(X[va])
            m = LogisticRegression(max_iter=2000, random_state=SEED)
            m.fit(Xtr, y[tr])
            proba = m.predict_proba(Xva)
            pred = decide(proba, weights)
            if want_importance:
                # 변수 하나가 차지하는 원-핫 열들의 |계수| 평균을 그 변수의 중요도로 본다
                col = 0
                for j, cats in enumerate(enc.categories_):
                    w_abs = np.abs(m.coef_[:, col:col + len(cats)])
                    imp[j] += float(w_abs.mean())
                    col += len(cats)
        else:
            m = make_model(family)
            m.fit(X[tr], y[tr])
            proba = m.predict_proba(X[va])
            pred = decide(proba, weights)
            if want_importance:
                imp += m.feature_importances_
        f1s.append(macro_f1(y[va], pred))
        recs.append(high_burden_recall(y[va], pred))
        oof_proba[va] = proba
    out = {'macro_f1': float(np.mean(f1s)), 'high_burden_recall': float(np.mean(recs))}
    if want_importance:
        out['importance'] = imp / len(set(folds))
    out['oof_proba'] = oof_proba
    return out


# ─────────────────────────────────────────────────── 희소성 (FR-009a)
def build_freq_table(X, features):
    """변수별 응답 범주 빈도. 개별 행이 아니라 집계값이라 런타임에 두어도 안전하다."""
    table = {}
    n = len(X)
    for j, f in enumerate(features):
        vals, counts = np.unique(X[:, j], return_counts=True)
        table[f] = {str(int(v)): float(c / n) for v, c in zip(vals, counts)}
    return table


def rarity(row, features, table, eps=1e-4):
    """응답 조합이 학습 데이터에서 얼마나 드문가. 작을수록(음수로 클수록) 드물다."""
    s = 0.0
    for j, f in enumerate(features):
        p = table[f].get(str(int(row[j])), eps)
        s += np.log(max(p, eps))
    return float(s / len(features))


# ─────────────────────────────────────────────────────── 단계
def stage_baseline(d):
    print('\n[1/4] 기준 모델 — 38개 설명변수 전체, 계열 비교')
    X, y, folds, feats = d['X'], d['y'], d['folds'], d['features']
    results = {}
    for fam in ['rf', 'et', 'logit']:
        t0 = time.time()
        raw = cv_scores(X, y, folds, feats, family=fam)
        w, tuned = tune_decision_weights(raw['oof_proba'], y)
        results[fam] = {'macro_f1': tuned['macro_f1'], 'high_burden_recall': tuned['high_burden_recall'],
                        'decision_weights': w,
                        'argmax_only': {'macro_f1': raw['macro_f1'],
                                        'high_burden_recall': raw['high_burden_recall']}}
        print(f"   {fam:6s} macro F1 {tuned['macro_f1']:.4f} · 고부담 재현율 "
              f"{tuned['high_burden_recall']:.4f} · 가중치 {w[0]:.2f}  "
              f"(가중치 없이 F1 {raw['macro_f1']:.4f} 재현율 {raw['high_burden_recall']:.4f})  "
              f"({time.time() - t0:.1f}s)")
    # 재현율 하한을 만족하는 계열 중 macro F1 이 가장 높은 것. 하나도 없으면 재현율 우선.
    ok_fams = [f for f, r in results.items() if r['high_burden_recall'] >= MIN_REC_ABS + REC_MARGIN]
    pool = ok_fams or list(results)
    best = max(pool, key=lambda f: results[f]['macro_f1'])
    print(f"   → 채택 계열: {best} · 결정 가중치 {results[best]['decision_weights']}")
    return {'family': best, 'results': results,
            'weights': results[best]['decision_weights'],
            'B_f1': results[best]['macro_f1'], 'B_rec': results[best]['high_burden_recall']}


def stage_select(d, base):
    print('\n[2/4] 문항 선별 — 후진 제거 (FR-004c)')
    X, y, folds = d['X'], d['y'], d['folds']
    fam = base['family']
    cur = list(d['features'])
    idx = {f: i for i, f in enumerate(d['features'])}
    history, dropped = [], []

    while len(cur) > 3:
        cols = [idx[f] for f in cur]
        r = cv_scores(X[:, cols], y, folds, cur, family=fam, want_importance=True)
        w, tuned = tune_decision_weights(r['oof_proba'], y)
        f1_loss = base['B_f1'] - tuned['macro_f1']
        rec_loss = base['B_rec'] - tuned['high_burden_recall']
        okay = (f1_loss <= MAX_F1_LOSS - F1_MARGIN and rec_loss <= MAX_REC_LOSS
                and tuned['high_burden_recall'] >= MIN_REC_ABS + REC_MARGIN)
        history.append({'k': len(cur), 'macro_f1': tuned['macro_f1'],
                        'high_burden_recall': tuned['high_burden_recall'],
                        'decision_weights': w,
                        'f1_loss': f1_loss, 'rec_loss': rec_loss, 'passes': okay})
        print(f"   k={len(cur):2d}  F1 {tuned['macro_f1']:.4f} (손실 {f1_loss:+.4f}) · "
              f"재현율 {tuned['high_burden_recall']:.4f} (손실 {rec_loss:+.4f})  {'OK' if okay else '미달'}")
        if not okay:
            break
        imp = r.get('importance')
        if imp is None:
            break
        worst = cur[int(np.argmin(imp))]
        dropped.append(worst)
        cur = [f for f in cur if f != worst]

    # 마지막으로 조건을 만족한 지점이 최소 집합이다
    passing = [h for h in history if h['passes']]
    rule_k = min(h['k'] for h in passing) if passing else len(d['features'])
    if K_TARGET:
        found = [h for h in history if h['k'] == K_TARGET]
        if not found:
            raise SystemExit(f'K_TARGET={K_TARGET} 가 탐색 경로에 없다: {[h["k"] for h in history]}')
        if not found[0]['passes']:
            raise SystemExit(f'K_TARGET={K_TARGET} 는 SC-004·SC-005 정지 조건을 만족하지 않는다')
        best_k, k_source = K_TARGET, 'K_TARGET (제품 판단)'
        print(f'   ※ 문항 수를 K_TARGET={K_TARGET} 로 지정 — 규칙이 뽑은 최소 k={rule_k} 를 대신한다')
    else:
        best_k, k_source = rule_k, '규칙 (최소 k)'
    chosen = next((h for h in history if h['k'] == best_k), history[0])
    n_drop = len(d['features']) - best_k
    selected = [f for f in d['features'] if f not in dropped[:n_drop]]
    print(f"   → 최소 문항 집합 k={len(selected)} (탈락 {n_drop}개) · "
          f"F1 {chosen['macro_f1']:.4f} · 재현율 {chosen['high_burden_recall']:.4f}")
    return {'selected': selected, 'dropped_order': dropped, 'history': history,
            'weights': chosen['decision_weights'],
            'k_source': k_source, 'rule_k': rule_k,
            'baseline': {'macro_f1': base['B_f1'], 'high_burden_recall': base['B_rec'],
                         'n_features': len(d['features'])}}


def stage_calibrate(d, base, sel):
    print('\n[3/4] 판정 불가 임계값 보정 (FR-009b·SC-016)')
    X, y, folds = d['X'], d['y'], d['folds']
    idx = {f: i for i, f in enumerate(d['features'])}
    cols = [idx[f] for f in sel['selected']]
    Xs = X[:, cols]

    weights = sel['weights']
    r = cv_scores(Xs, y, folds, sel['selected'], family=base['family'], weights=weights)
    proba = r['oof_proba']
    pred = decide(proba, weights)
    maxp = proba.max(axis=1)

    table = build_freq_table(Xs, sel['selected'])
    rar = np.array([rarity(Xs[i], sel['selected'], table) for i in range(len(Xs))])

    wrong = (pred != y)
    best = None
    for tc in np.quantile(maxp, np.arange(0.02, 0.31, 0.01)):
        for td in np.quantile(rar, np.arange(0.01, 0.16, 0.01)):
            und = (maxp < tc) | (rar < td)
            rate = und.mean()
            if rate <= 0 or rate > 0.10 or (~und).sum() == 0:
                continue
            err_u, err_d = wrong[und].mean(), wrong[~und].mean()
            if err_u <= err_d:
                continue                       # SC-016 전반부: 판정 불가 쪽이 더 틀려야 한다
            cand = {'tau_conf': float(tc), 'tau_dens': float(td), 'rate': float(rate),
                    'err_undecidable': float(err_u), 'err_decided': float(err_d)}
            if best is None or cand['rate'] < best['rate']:
                best = cand
    if best is None:
        best = {'tau_conf': float(np.quantile(maxp, 0.03)), 'tau_dens': float(np.quantile(rar, 0.02)),
                'rate': None, 'err_undecidable': None, 'err_decided': None,
                'note': '조건을 만족하는 조합을 찾지 못해 보수적 분위값으로 대체'}
        print('   ! SC-016 조건을 만족하는 조합 없음 — 보수적 기본값 사용')
    else:
        print(f"   τ_conf={best['tau_conf']:.4f} τ_dens={best['tau_dens']:.4f} · "
              f"판정불가 {best['rate']*100:.1f}% · 오분류율 판정불가 {best['err_undecidable']:.3f} "
              f"> 판정 {best['err_decided']:.3f}")
    best['freq_table'] = table
    best['cv'] = {'macro_f1': r['macro_f1'], 'high_burden_recall': r['high_burden_recall']}
    return best


def export_tree(t):
    """sklearn 트리를 런타임이 읽을 최소 구조로 변환한다."""
    tr = t.tree_
    val = tr.value.reshape(tr.node_count, -1)
    tot = val.sum(axis=1, keepdims=True)
    prob = np.divide(val, np.where(tot == 0, 1, tot))
    return {
        'feature': [int(f) for f in tr.feature],
        'threshold': [round(float(v), 6) for v in tr.threshold],
        'left': [int(v) for v in tr.children_left],
        'right': [int(v) for v in tr.children_right],
        'value': [[round(float(x), 6) for x in row] for row in prob],
    }


def stage_export(d, base, sel, cal):
    print('\n[4/4] 아티팩트 내보내기')
    X, y = d['X'], d['y']
    idx = {f: i for i, f in enumerate(d['features'])}
    cols = [idx[f] for f in sel['selected']]
    Xs = X[:, cols]

    family = base['family']
    payload = {
        'model_version': MODEL_VERSION,
        'question_set_version': QSET_VERSION,
        'family': family,
        'features': sel['selected'],
        'classes': CLASSES,
        'decision_weights': sel['weights'],
        'missing_sentinel': MISSING,
        'trained_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
    }

    enc = None                      # logit 이 아니면 인코더가 없다 (아래 joblib 묶음에서 씀)
    if family == 'logit':
        # 다항 로지스틱 — 계수 행렬만 내보내면 런타임이 내적 + softmax 로 재현한다.
        # 기여도가 정확히 분해되어(선형 SHAP) FR-011 설명에 유리하다.
        enc = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
        Xoh = enc.fit_transform(Xs)
        model = LogisticRegression(max_iter=2000, random_state=SEED)
        model.fit(Xoh, y)

        cats = [[float(v) for v in c] for c in enc.categories_]
        # 기준값: 학습 분포에서의 기대 기여. sum(contrib) + base = logit 이 정확히 성립한다.
        col, spans, expect = 0, [], []
        for j, c in enumerate(cats):
            width = len(c)
            spans.append([col, width])
            freq = Xoh[:, col:col + width].mean(axis=0)              # 범주별 관측 비율
            expect.append((model.coef_[:, col:col + width] * freq).sum(axis=1).tolist())
            col += width
        payload.update({
            'categories': cats,
            'spans': spans,
            'coef': [[round(float(v), 6) for v in row] for row in model.coef_],
            'intercept': [round(float(v), 6) for v in model.intercept_],
            'expected_contrib': [[round(float(v), 6) for v in e] for e in expect],
        })
    else:
        model = make_model(family)
        model.fit(Xs, y)
        payload['trees'] = [export_tree(t) for t in model.estimators_]
    (MODELS / 'model_v1.json').write_text(json.dumps(payload), encoding='utf-8')

    (MODELS / 'selection_v1.json').write_text(
        json.dumps({'model_version': MODEL_VERSION, 'k': len(sel['selected']), **sel,
                    'family_comparison': base['results'],
                    'stop_rule': {'max_f1_loss': MAX_F1_LOSS, 'max_rec_loss': MAX_REC_LOSS,
                                  'min_rec_abs': MIN_REC_ABS}},
                   ensure_ascii=False, indent=2), encoding='utf-8')

    (MODELS / 'uncertainty_v1.json').write_text(
        json.dumps({'model_version': MODEL_VERSION, **cal}, ensure_ascii=False), encoding='utf-8')

    questions = [build_question(f, i + 1) for i, f in enumerate(sel['selected'])]
    (MODELS / 'questions_v1.json').write_text(
        json.dumps({'question_set_version': QSET_VERSION, 'model_version': MODEL_VERSION,
                    'questions': questions,
                    'selfReport': {'questionNo': 0, 'feature': None,
                                   'originalItem': SELF_REPORT['item'],
                                   'text': SELF_REPORT['text'], 'inputType': 'choice',
                                   'options': [{'value': v, 'label': l} for v, l in SELF_REPORT['options']],
                                   'hasNotApplicable': False}},
                   ensure_ascii=False, indent=2), encoding='utf-8')

    # 기여도 구분 임계값 (FR-011-1): 학습 데이터 기여도 절댓값 분포의 하위 분위
    from saabas import contributions
    sample = Xs[np.random.RandomState(SEED).choice(len(Xs), size=min(300, len(Xs)), replace=False)]
    mags = []
    for row in sample:
        c, _ = contributions(payload, list(row))
        mags.extend(abs(v) for v in c)
    thr = float(np.quantile(mags, 0.55)) if mags else 0.01
    (MODELS / 'contribution_v1.json').write_text(
        json.dumps({'min_threshold': thr, 'basis': 'train 표본 300건 기여도 절댓값 55분위'},
                   ensure_ascii=False), encoding='utf-8')

    # 분석용 원본 모델 — **배포 대상이 아니다.** 백엔드는 models/*.json 만 읽는다.
    #   JSON 은 추론에 필요한 계수만 담아, 학습된 객체가 필요한 일(다른 방식의 확률 보정,
    #   predict_proba 외의 sklearn 기능, 하이퍼파라미터 확인)은 재학습해야만 가능했다.
    #   객체를 그대로 남겨 그 재학습을 없앤다. 되읽을 때 sklearn 버전이 다르면 경고가 뜬다.
    import joblib
    import sklearn
    joblib.dump({
        'model_version': MODEL_VERSION,
        'question_set_version': QSET_VERSION,
        'family': family,
        'features': sel['selected'],
        'classes': CLASSES,
        'decision_weights': sel['weights'],
        'missing_sentinel': MISSING,
        'model': model,                 # 학습된 추정기 그대로
        'encoder': enc,                 # logit 이면 OneHotEncoder, 아니면 None
        'sklearn_version': sklearn.__version__,
        'trained_at': payload['trained_at'],
        'note': '분석 전용. 런타임은 이 파일을 읽지 않는다.',
    }, MODELS / 'model_v1.joblib')

    size = (MODELS / 'model_v1.json').stat().st_size / 1e6
    shape = (f"트리 {len(payload['trees'])}개" if 'trees' in payload
             else f"계수 {len(payload['coef'])}x{len(payload['coef'][0])}")
    print(f"   model_v1.json         {size:.1f}MB · {payload['family']} · {shape} · 변수 {len(sel['selected'])}개")
    print(f"   selection_v1.json     k={len(sel['selected'])}")
    print(f"   uncertainty_v1.json   τ_conf={cal['tau_conf']:.4f} τ_dens={cal['tau_dens']:.4f}")
    print(f"   questions_v1.json     문항 {len(questions)}개 + 자가보고 1개")
    print(f"   contribution_v1.json  임계값 {thr:.5f}")
    print(f"   model_v1.joblib       분석용 원본 (배포 대상 아님)")
    return payload


def baseline_on_test(d, payload):
    """38개 설명변수 전체 모델을 train 으로 학습해 test 에서 평가한다 (동일 조건 비교)."""
    X, y, Xt, yt = d['X'], d['y'], d['Xtest'], d['ytest']
    w = payload.get('decision_weights')
    if payload['family'] == 'logit':
        enc = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
        m = LogisticRegression(max_iter=2000, random_state=SEED)
        m.fit(enc.fit_transform(X), y)
        proba = m.predict_proba(enc.transform(Xt))
    else:
        m = make_model(payload['family'])
        m.fit(X, y)
        proba = m.predict_proba(Xt)
    pred = decide(proba, w)
    return macro_f1(yt, pred), high_burden_recall(yt, pred)


def stage_evaluate(d, payload):
    print('\n[평가] test 602건 — 단 한 번만 실행 (SC-004·SC-005·SC-016)')
    from saabas import predict_proba
    feats = payload['features']
    idx = {f: i for i, f in enumerate(d['features'])}
    cols = [idx[f] for f in feats]

    Xt, yt = d['Xtest'][:, cols], d['ytest']
    unc = json.loads((MODELS / 'uncertainty_v1.json').read_text(encoding='utf-8'))
    table, tc, td = unc['freq_table'], unc['tau_conf'], unc['tau_dens']

    proba = np.array([predict_proba(payload, list(row)) for row in Xt])
    pred = decide(proba, payload.get('decision_weights'))
    maxp = proba.max(axis=1)
    rar = np.array([rarity(Xt[i], feats, table) for i in range(len(Xt))])
    und = (maxp < tc) | (rar < td)

    f1 = macro_f1(yt, pred)
    rec = high_burden_recall(yt, pred)
    sel = json.loads((MODELS / 'selection_v1.json').read_text(encoding='utf-8'))

    # 기준 모델(38변수)을 같은 test 에서 평가한다. CV 값과 test 값을 섞어 비교하면
    # 추정 방식이 달라 SC-004·SC-005 의 '대비 손실'이 왜곡된다.
    bf1, brec = baseline_on_test(d, payload)
    print(f"   macro F1          {f1:.4f}  (38변수 기준 모델 {bf1:.4f}, 손실 {bf1-f1:+.4f} / 허용 {MAX_F1_LOSS})")
    print(f"   고부담 재현율      {rec:.4f}  (38변수 기준 모델 {brec:.4f}, 손실 {brec-rec:+.4f} / 허용 {MAX_REC_LOSS}, 절대 하한 {MIN_REC_ABS})")
    b = {'macro_f1': bf1, 'high_burden_recall': brec}
    print(f"   판정 불가 비율     {und.mean()*100:.1f}%  (허용 10% 이하)")
    if und.sum() and (~und).sum():
        print(f"   오분류율          판정불가 {(pred[und]!=yt[und]).mean():.3f} vs 판정 {(pred[~und]!=yt[~und]).mean():.3f}")

    verdict = {
        'SC-004 macro F1 손실 <= 0.03': bool(b['macro_f1'] - f1 <= MAX_F1_LOSS),
        'SC-005 재현율 손실 <= 0.05': bool(b['high_burden_recall'] - rec <= MAX_REC_LOSS),
        'SC-005 재현율 >= 0.70': bool(rec >= MIN_REC_ABS),
        'SC-016 판정불가 <= 10%': bool(und.mean() <= 0.10),
    }
    print()
    for k, v in verdict.items():
        print(f"   {'PASS' if v else 'FAIL'}  {k}")

    dbmod.record_model_version(MODEL_VERSION, payload['family'], QSET_VERSION,
                               f1, rec, float(und.mean()),
                               json.dumps(verdict, ensure_ascii=False))
    return {'macro_f1': f1, 'high_burden_recall': rec, 'undecidable_rate': float(und.mean()),
            'verdict': verdict}


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'all'
    d = dbmod.load_dataset(MISSING)
    print(f"데이터: train {len(d['y'])} / test {len(d['ytest'])} · 설명변수 {len(d['features'])}개 · "
          f"fold {sorted(set(d['folds']))}")

    if cmd == 'evaluate':
        payload = json.loads((MODELS / 'model_v1.json').read_text(encoding='utf-8'))
        stage_evaluate(d, payload)
        return

    if cmd in ('all', 'build'):
        base = stage_baseline(d)
        sel = stage_select(d, base)
        cal = stage_calibrate(d, base, sel)
        payload = stage_export(d, base, sel, cal)
        if cmd == 'all':
            stage_evaluate(d, payload)     # test 602건 1회 사용
        else:
            print('\n완료(build). test 602건은 사용하지 않았다.')
        print(f'\n아티팩트: {MODELS}')


if __name__ == '__main__':
    main()
