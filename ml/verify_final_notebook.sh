#!/usr/bin/env bash
# 최종 노트북이 클린 런타임에서 무오류로 도는지 검증한다.
#
#   bash ml/verify_final_notebook.sh [venv경로]
#
# 세 가지 경로를 모두 돌린다.
#   ① 채점자 환경   DB 없음 · 추론 서비스 없음   ← 제일 중요
#   ② 서비스만 있음 DB 없음 · 소켓 있음
#   ③ 평소 환경     DB 있음 · 소켓 있음
#
# 노트북은 models/runs/ 에 실행 폴더를 남긴다. 끝에서 이번에 생긴 것만 지운다.
set -euo pipefail
cd "$(dirname "$0")/.."
NB='deliverables/최종-전체과정.ipynb'
VENV="${1:-}"
OUT="$(mktemp -d)"

if [ -n "$VENV" ]; then PY="$VENV/bin/python"; else PY="$(command -v python3)"; fi
"$PY" -c 'import nbconvert' 2>/dev/null || {
  echo "nbconvert 가 없습니다. 검증용 환경을 먼저 만드세요:"
  echo "  python3 -m venv /tmp/nbcheck"
  echo "  /tmp/nbcheck/bin/pip install -U pip"
  echo "  /tmp/nbcheck/bin/pip install numpy==2.0.2 scipy==1.13.1 scikit-learn==1.6.1 \\"
  echo "      joblib==1.5.3 pymysql nbformat nbconvert ipykernel"
  echo "  bash ml/verify_final_notebook.sh /tmp/nbcheck"
  exit 1; }

BEFORE=$(ls models/runs 2>/dev/null | sort || true)
FAIL=0
run() {                       # $1=이름  $2..=환경변수
  local name="$1"; shift
  echo "── $name"
  if env "$@" "$PY" -m nbconvert --execute --to notebook \
        --ExecutePreprocessor.timeout=900 \
        --output "$OUT/$name.ipynb" "$NB" >"$OUT/$name.log" 2>&1; then
    echo "   통과"
  else
    echo "   ★실패 — $OUT/$name.log"; tail -15 "$OUT/$name.log"; FAIL=1
  fi
}

run grader   CB_NO_DB=1 CB_NO_SERVICE=1
run offline  CB_NO_DB=1
run full     CB_VERIFY=1

AFTER=$(ls models/runs 2>/dev/null | sort || true)
for d in $(comm -13 <(echo "$BEFORE") <(echo "$AFTER")); do
  rm -rf "models/runs/$d"; echo "정리 models/runs/$d"
done

echo
[ "$FAIL" = 0 ] && echo "세 경로 모두 무오류" || { echo "실패한 경로가 있습니다"; exit 1; }
