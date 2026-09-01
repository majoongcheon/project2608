# ml/ — 오프라인 학습 파이프라인

**런타임에는 실행되지 않는다.** 산출물 `models/*.json` 만 배포에 실린다(research.md R-2).

```bash
pip3 install --target ml/.pylibs -r ml/requirements.txt
python3 ml/train.py all        # baseline → select → calibrate → export → evaluate
python3 ml/parity.py           # TS 추론기 대조용 기준값 3,000건 생성
cd backend && npx vitest run tests/parity   # 릴리스 게이트
```

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
