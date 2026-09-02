"""run manifest — 어떤 데이터에 어떤 코드로 무엇을 만들었는지 남긴다."""
import json
from cb_burden.artifacts import manifest


def test_실행_정보가_모두_담긴다(tmp_path):
    run = manifest.start(run_dir=tmp_path, snapshot_meta={'sha256': 'abc', 'rows': 3000},
                         snapshot_path='data/snapshots/x.csv.gz',
                         model_version='v1.0.1', question_set_version='qs-v1.0.1')
    run['stages'].append({'name': 'baseline', 'duration_s': 1.0, 'metrics': {}})
    manifest.finish(run, tmp_path)

    got = json.loads((tmp_path / 'run.json').read_text(encoding='utf-8'))
    assert got['snapshot']['sha256'] == 'abc'
    assert got['snapshot']['rows'] == 3000
    assert got['model_version'] == 'v1.0.1'
    assert got['question_set_version'] == 'qs-v1.0.1'
    assert got['seed'] == 20260901      # config.SEED — 원본 train.py 와 같아야 한다
    assert 'python' in got['versions'] and 'sklearn' in got['versions']
    assert 'sha' in got['git'] and 'dirty' in got['git']
    assert got['stages'][0]['name'] == 'baseline'
    assert got['finished_at']


def test_산출물_해시가_기록된다(tmp_path):
    (tmp_path / 'model_v1.json').write_text('{}', encoding='utf-8')
    run = manifest.start(run_dir=tmp_path, snapshot_meta={'sha256': 'abc', 'rows': 1},
                         snapshot_path='x', model_version='v1', question_set_version='q')
    manifest.finish(run, tmp_path)
    got = json.loads((tmp_path / 'run.json').read_text(encoding='utf-8'))
    assert got['artifacts']['model_v1.json'].startswith('sha256:')
    assert 'run.json' not in got['artifacts']       # 자기 자신은 넣지 않는다


def test_run_id_는_디렉터리_이름이다(tmp_path):
    d = tmp_path / '2026-09-02T10-30_abc123'
    d.mkdir()
    run = manifest.start(run_dir=d, snapshot_meta={}, snapshot_path='x',
                         model_version='v1', question_set_version='q')
    assert run['run_id'] == '2026-09-02T10-30_abc123'
