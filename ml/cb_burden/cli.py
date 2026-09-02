"""cb_burden 명령.

    python -m cb_burden snapshot --out data/snapshots/cb_dataset_2026-09-01.csv.gz
    python -m cb_burden train    --snapshot <path> --model-version v1.0.1
    python -m cb_burden evaluate models/runs/<run_id>
    python -m cb_burden golden   models/runs/<run_id>
    python -m cb_burden verify   <run_dir 또는 릴리스>
    python -m cb_burden promote  models/runs/<run_id> --as v1.0.1
    python -m cb_burden record   --release v1.0.1 --model-version v1.0.1

★ train 은 승격하지 않는다. 배포본을 바꾸는 것은 promote 뿐이다.
★ evaluate 는 test 602건을 쓴다. 모든 결정이 끝난 뒤 한 번만 실행한다.
"""
import argparse
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cb_burden.artifacts import golden as golden_mod
from cb_burden.artifacts import manifest, release, validate
from cb_burden.data import integrity, snapshot
from cb_burden.stages import baseline, calibrate, evaluate as evaluate_stage, export, select

ROOT = Path(__file__).resolve().parent.parent.parent
KST = timezone(timedelta(hours=9))
ARTIFACT_NAMES = ('model', 'selection', 'uncertainty', 'questions', 'contribution')


def _models_dir():
    return ROOT / os.getenv('CB_MODELS_DIR', 'models')


def _run_id():
    try:
        sha = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'],
                             capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        sha = ''
    stamp = datetime.now(KST).strftime('%Y-%m-%dT%H-%M')
    return f'{stamp}_{sha or "nogit"}'


def _snapshot_path(run):
    """run.json 에 상대 경로로 적힌 스냅샷을 어디서 실행하든 찾는다.

    train 을 프로젝트 루트에서 돌리고 evaluate 를 다른 디렉터리에서 돌리면 상대 경로가
    깨진다. 있는 그대로 먼저 보고, 없으면 저장소 루트 기준으로 다시 찾는다.
    """
    p = Path(run['snapshot']['path'])
    if p.exists():
        return p
    alt = ROOT / p
    if alt.exists():
        return alt
    raise SystemExit(f'스냅샷을 찾을 수 없습니다: {p}\n  run.json 의 경로를 확인하세요')


def _load_bundle(d):
    d = Path(d)
    return {k: json.loads((d / f'{k}_v1.json').read_text(encoding='utf-8'))
            for k in ARTIFACT_NAMES}


# ─────────────────────────────────────────────────────────── 명령
def cmd_snapshot(a):
    from cb_burden.data import source_db
    out = Path(a.out)
    features, rows, info = source_db.fetch()
    meta = snapshot.write(out, features, rows, source_view=info['source_view'],
                          db_info=info['db'])
    print(f"스냅샷 생성 {out}")
    print(f"  rows {meta['rows']} · features {meta['features']} · "
          f"split {meta['split']} · sha256 {meta['sha256'][:16]}…")


def cmd_train(a):
    snap = snapshot.read(a.snapshot)
    integrity.check(snap)

    run_dir = _models_dir() / 'runs' / _run_id()
    run_dir.mkdir(parents=True, exist_ok=True)
    run = manifest.start(run_dir, snap['meta'], a.snapshot,
                         a.model_version, a.question_set_version)

    print(f"\n실행 {run['run_id']} → {run_dir}")
    print('\n[1/4] 기준 모델 — 설명변수 전체, 계열 비교')
    base = baseline.run(snap)
    run['stages'].append({'name': 'baseline', 'metrics': base['results']})

    print('\n[2/4] 문항 선별 — 후진 제거 (FR-004c)')
    sel = select.run(snap, base, k_target=a.k_target)
    run['stages'].append({'name': 'select', 'metrics': {'k': len(sel['selected'])}})

    print('\n[3/4] 판정 불가 임계값 보정 (FR-009b·SC-016)')
    cal = calibrate.run(snap, base, sel)
    run['stages'].append({'name': 'calibrate',
                          'metrics': {k: cal[k] for k in
                                      ('tau_conf', 'tau_dens', 'rate') if k in cal}})

    print('\n[4/4] 아티팩트 내보내기')
    payload = export.run(snap, base, sel, cal, run_dir,
                         a.model_version, a.question_set_version)
    run['stages'].append({'name': 'export', 'metrics': {'family': payload['family']}})

    golden_mod.build(payload, snap, run_dir)
    manifest.finish(run, run_dir)
    print(f"\n완료 — {run_dir}")
    print(f"  다음: python -m cb_burden evaluate {run_dir}")


def cmd_evaluate(a):
    run_dir = Path(a.run_dir)
    run = json.loads((run_dir / 'run.json').read_text(encoding='utf-8'))
    if run.get('success_criteria') and not a.force:
        raise SystemExit(
            ' 이미 평가한 실행입니다. test 602건은 한 번만 씁니다.\n'
            '  다시 평가하려면 --force 를 주세요')

    snap = snapshot.read(_snapshot_path(run))
    payload = json.loads((run_dir / 'model_v1.json').read_text(encoding='utf-8'))
    unc = json.loads((run_dir / 'uncertainty_v1.json').read_text(encoding='utf-8'))

    print('\n[평가] test 602건 — 단 한 번만 실행 (SC-004·SC-005·SC-016)')
    res = evaluate_stage.run(snap, payload, unc)
    run['success_criteria'] = res['verdict']
    run['evaluation'] = {k: res[k] for k in
                         ('macro_f1', 'high_burden_recall', 'undecidable_rate', 'baseline')}
    manifest.finish(run, run_dir)


def cmd_golden(a):
    run_dir = Path(a.run_dir)
    run = json.loads((run_dir / 'run.json').read_text(encoding='utf-8'))
    snap = snapshot.read(_snapshot_path(run))
    payload = json.loads((run_dir / 'model_v1.json').read_text(encoding='utf-8'))
    out = golden_mod.build(payload, snap, run_dir)
    print(f'골든 생성 {out}')


def cmd_verify(a):
    validate.check(_load_bundle(a.target))
    print(f'검증 통과 {a.target}')


def cmd_promote(a):
    target = release.promote(a.run_dir, _models_dir(), a.as_release,
                             validator=lambda d: validate.check(_load_bundle(d)))
    print(f'승격 완료 {target}')
    print(f"  current → {release.current(_models_dir())}")


def cmd_record(a):
    from cb_burden.data import record, source_db
    rel = _models_dir() / a.release
    run = json.loads((rel / 'run.json').read_text(encoding='utf-8'))
    ev, payload = run.get('evaluation'), _load_bundle(rel)['model']
    if not ev:
        raise SystemExit('평가 기록이 없습니다. evaluate 를 먼저 실행하세요')
    conn = source_db.connect()
    record.write(conn, model_version=a.model_version, family=payload['family'],
                 qset=payload['question_set_version'],
                 f1=ev['macro_f1'], rec=ev['high_burden_recall'],
                 und=ev['undecidable_rate'],
                 notes=json.dumps(run['success_criteria'], ensure_ascii=False),
                 force=a.force)
    conn.close()
    print(f'기록 완료 {a.model_version}')


def main(argv=None):
    ap = argparse.ArgumentParser(prog='cb_burden', description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('snapshot', help='DB 에서 학습 입력을 내려 파일로 고정한다')
    p.add_argument('--out', required=True)
    p.set_defaults(fn=cmd_snapshot)

    p = sub.add_parser('train', help='baseline→select→calibrate→export (test 안 씀)')
    p.add_argument('--snapshot', required=True)
    p.add_argument('--model-version', required=True)
    p.add_argument('--question-set-version', required=True)
    p.add_argument('--k-target', type=int, default=0,
                   help='문항 수를 사람이 지정한다. 0 이면 규칙(최소 k)을 따른다')
    p.set_defaults(fn=cmd_train)

    p = sub.add_parser('evaluate', help='test 602건 1회 평가')
    p.add_argument('run_dir')
    p.add_argument('--force', action='store_true')
    p.set_defaults(fn=cmd_evaluate)

    p = sub.add_parser('golden', help='골든 케이스 생성')
    p.add_argument('run_dir')
    p.set_defaults(fn=cmd_golden)

    p = sub.add_parser('verify', help='아티팩트 스키마·정합 검증')
    p.add_argument('target')
    p.set_defaults(fn=cmd_verify)

    p = sub.add_parser('promote', help='검증을 통과하면 릴리스로 승격한다')
    p.add_argument('run_dir')
    p.add_argument('--as', dest='as_release', required=True)
    p.set_defaults(fn=cmd_promote)

    p = sub.add_parser('record', help='성능을 cb_model_version_v1 에 기록한다')
    p.add_argument('--release', required=True)
    p.add_argument('--model-version', required=True)
    p.add_argument('--force', action='store_true')
    p.set_defaults(fn=cmd_record)

    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == '__main__':
    main()
