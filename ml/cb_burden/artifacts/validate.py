"""산출물 검증.

백엔드 modelLoader 가 기동 때 하던 정합 검사(①features 순서 ②문항 순서)를 그대로 갖고,
스키마·척도 방향·임계값 범위·버전 일치를 더한다. 어긋나면 승격하지 않는다.

DB 활성 문항 대조(백엔드의 세 번째 검사)는 여기서 하지 않는다 — 학습은 DB 를 보지 않는다.
그 검사는 배포 시점에 백엔드가 수행한다.
"""
from cb_burden import config

REQUIRED = {
    'model': ['model_version', 'question_set_version', 'family', 'features', 'classes',
              'decision_weights', 'missing_sentinel'],
    'selection': ['model_version', 'selected'],
    'uncertainty': ['model_version', 'tau_conf', 'tau_dens', 'freq_table'],
    'questions': ['question_set_version', 'questions'],
    'contribution': ['min_threshold'],
}


def check(bundle):
    for name, keys in REQUIRED.items():
        if name not in bundle:
            raise ValueError(f'{name} 아티팩트가 없습니다')
        for k in keys:
            if k not in bundle[name]:
                raise ValueError(f'{name} 에 필수 키 {k} 가 없습니다')

    model, sel = bundle['model'], bundle['selection']
    q, unc = bundle['questions'], bundle['uncertainty']

    # ① 모델 features 순서 = 선별 결과 (백엔드 기동 검사와 동일)
    if list(model['features']) != list(sel['selected']):
        raise ValueError(
            f'model.features 가 selection.selected 와 다릅니다\n'
            f'  model  {model["features"]}\n  select {sel["selected"]}')

    # ② 문항 순서 = 모델 (백엔드 기동 검사와 동일)
    qf = [x['feature'] for x in q['questions']]
    if qf != list(model['features']):
        raise ValueError(f'questions 의 feature 순서가 모델과 다릅니다\n'
                         f'  model     {model["features"]}\n  questions {qf}')

    # ③ 척도 방향 — 1 이 최고부담인 역방향. 뒤집히면 이용자가 정반대로 이해한다.
    if list(model['classes']) != config.CLASSES:
        raise ValueError(f'척도가 {config.CLASSES} 가 아닙니다: {model["classes"]}')

    # ④ 임계값 범위
    if not 0.0 < float(unc['tau_conf']) < 1.0:
        raise ValueError(f'tau_conf 가 (0,1) 밖입니다: {unc["tau_conf"]}')
    if not float(unc['tau_dens']) < 0.0:
        raise ValueError(f'tau_dens 는 로그 평균이라 음수여야 합니다: {unc["tau_dens"]}')

    # ⑤ 계열과 가중치
    if model['family'] not in ('logit', 'rf', 'et'):
        raise ValueError(f'지원하지 않는 계열입니다: {model["family"]}')
    if len(model['decision_weights']) != len(config.CLASSES):
        raise ValueError(
            f'decision_weights 길이가 클래스 수와 다릅니다: {model["decision_weights"]}')

    # ⑥ 버전 일치 — 한 번에 만들어진 산출물끼리 섞이면 안 된다
    for name in ('selection', 'uncertainty'):
        if bundle[name]['model_version'] != model['model_version']:
            raise ValueError(
                f'{name} 의 모델 버전이 다릅니다: '
                f'{bundle[name]["model_version"]} != {model["model_version"]}')
    if q['question_set_version'] != model['question_set_version']:
        raise ValueError(
            f'questions 의 문항 집합 버전이 다릅니다: '
            f'{q["question_set_version"]} != {model["question_set_version"]}')
    return True
