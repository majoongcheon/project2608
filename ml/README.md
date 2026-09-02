# ml/ — 오프라인 학습 파이프라인

**런타임에는 실행되지 않는다.** 산출물 `models/*.json` 만 배포에 실린다(research.md R-2).

```bash
pip3 install --target ml/.pylibs -r ml/requirements.txt

# 새 파이프라인 (cb_burden 패키지)
export PYTHONPATH=ml/.pylibs:ml
python3 -m cb_burden snapshot --out data/snapshots/cb_dataset_<날짜>.csv.gz
python3 -m cb_burden train --snapshot <path> --model-version <ver> --question-set-version <qs>
python3 -m cb_burden evaluate models/runs/<run_id>     # test 602건 — 여기서 단 한 번만
python3 -m cb_burden verify   models/runs/<run_id>
python3 -m cb_burden promote  models/runs/<run_id> --as <ver>
python3 -m pytest ml/tests

# 추론 서비스
python3 -m cb_burden.serve --release models      # run/cb-inference.sock (포트 안 씀)

# 옛 파이프라인 (이관 중이라 남겨 둠 — 새 것이 안정되면 ml/legacy/ 로 옮긴다)
python3 ml/train.py all
```

## 새 구조에서 달라진 것

- **학습은 DB 를 읽지 않는다.** 고정된 스냅샷 파일만 읽고, 시작할 때 sha256 을 대조한다
- **학습은 `models/runs/<run_id>/` 에만 쓴다.** 배포본은 `promote` 로만 바뀐다
- `evaluate` 를 `train` 에서 분리했다 — test 602건이 매 실행마다 소모되지 않는다
- `pytest ml/tests` 가 DB 없이 전부 돈다

## 파일

| 파일 | 역할 |
|---|---|
| `db.py` | `v_cb_tree_v1` 적재 + 무결성 검증(3,000행·38변수·fold·배제변수 부재) |
| `train.py` | 계열 비교 · 후진 제거 · 임계값 보정 · 내보내기 · test 1회 평가 |
| `saabas.py` | 추론·기여도의 **기준 구현**. `backend/src/inference/*.ts` 와 같은 알고리즘 |
| `questions.py` | 변수 → 자연어 문항 변환(FR-004a)과 기여 요인 문장 템플릿(FR-011) |
| `parity.py` | 패리티 기준값 생성 |

## 지켜야 할 것

- **test 602건은 `evaluate` 에서 단 한 번만 쓴다.** 결과가 나쁘다고 앞 단계로 돌아가면
  test 가 오염되어 SC-004·SC-005 의 최종 근거로 쓸 수 없다.
- 성능이 미달해도 **FR-004b 로 배제한 6개 변수를 되살리지 않는다.**
  문항 조합 재선별 또는 성공 기준 재조정으로 대응한다.
- `cv_fold` 는 DB 에 고정되어 있다. 분할을 새로 만들지 않는다(원칙 IV).
