#!/usr/bin/env bash
# check_project.sh — 돌봄부담 진단 서비스 기동/중지/재시작/상태 점검
#
#   ./check_project.sh start      백엔드(9523) + 프론트엔드(9503) 기동
#   ./check_project.sh stop       두 서비스 중지
#   ./check_project.sh restart    중지 후 재기동
#   ./check_project.sh status     포트·PID·헬스체크
#   ./check_project.sh check      전체 점검 (DB·모델·API·데이터 정합)
#   ./check_project.sh logs [be|fe]  로그 따라가기
#   ./check_project.sh setup      의존성 설치 + 마이그레이션 + 시드
#
# Docker 를 쓰지 않는다 (Constitution 원칙 V). 프로세스로 직접 띄우고 PID 파일로 관리한다.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

RUN_DIR="$ROOT/run"
LOG_DIR="$ROOT/logs"
mkdir -p "$RUN_DIR" "$LOG_DIR"

BE_PID="$RUN_DIR/backend.pid"
FE_PID="$RUN_DIR/frontend.pid"
BE_LOG="$LOG_DIR/backend.log"
FE_LOG="$LOG_DIR/frontend.log"

# ── .env 에서 포트·도메인을 읽는다 (없으면 기본값) ──────────────────
load_env() {
  if [[ -f "$ROOT/.env" ]]; then
    set -a; . "$ROOT/.env"; set +a
  fi
  BACKEND_PORT="${BACKEND_PORT:-9523}"
  FRONTEND_PORT="${FRONTEND_PORT:-9503}"
  PUBLIC_DOMAIN="${PUBLIC_DOMAIN:-p3.sumzip.com}"
  PUBLIC_ORIGIN="${PUBLIC_ORIGIN:-https://$PUBLIC_DOMAIN}"
}
load_env

# ── 출력 ────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  R=$'\033[31m'; G=$'\033[32m'; Y=$'\033[33m'; B=$'\033[36m'; D=$'\033[2m'; N=$'\033[0m'
else
  R=""; G=""; Y=""; B=""; D=""; N=""
fi
ok()   { printf '  %s✓%s %s\n' "$G" "$N" "$*"; }
bad()  { printf '  %s✗%s %s\n' "$R" "$N" "$*"; }
warn() { printf '  %s!%s %s\n' "$Y" "$N" "$*"; }
info() { printf '  %s·%s %s\n' "$D" "$N" "$*"; }
head_() { printf '\n%s%s%s\n' "$B" "$*" "$N"; }

# ── 프로세스 도우미 ─────────────────────────────────────────────────
pid_alive() { [[ -n "${1:-}" ]] && kill -0 "$1" 2>/dev/null; }

read_pid() { [[ -f "$1" ]] && cat "$1" 2>/dev/null || true; }

port_pid() { lsof -ti tcp:"$1" -sTCP:LISTEN 2>/dev/null | head -1; }

wait_for_port() {   # wait_for_port <port> <seconds>
  local port="$1" limit="${2:-30}" i=0
  while (( i < limit )); do
    if [[ -n "$(port_pid "$port")" ]]; then return 0; fi
    sleep 1; i=$((i+1))
  done
  return 1
}

wait_for_health() { # wait_for_health <url> <seconds>
  local url="$1" limit="${2:-30}" i=0
  while (( i < limit )); do
    if curl -fsS --max-time 2 "$url" >/dev/null 2>&1; then return 0; fi
    sleep 1; i=$((i+1))
  done
  return 1
}

stop_one() {        # stop_one <name> <pidfile> <port>
  local name="$1" file="$2" port="$3"
  local pid; pid="$(read_pid "$file")"
  local killed=0

  if pid_alive "$pid"; then
    kill "$pid" 2>/dev/null
    for _ in 1 2 3 4 5 6 7 8 9 10; do
      pid_alive "$pid" || break
      sleep 0.5
    done
    pid_alive "$pid" && kill -9 "$pid" 2>/dev/null
    killed=1
  fi
  rm -f "$file"

  # PID 파일이 없거나 어긋난 경우에도 포트를 물고 있으면 정리한다
  local ppid; ppid="$(port_pid "$port")"
  if [[ -n "$ppid" ]]; then
    kill "$ppid" 2>/dev/null
    sleep 1
    ppid="$(port_pid "$port")"
    [[ -n "$ppid" ]] && kill -9 "$ppid" 2>/dev/null
    killed=1
  fi

  if (( killed )); then ok "$name 중지 (포트 $port)"; else info "$name 은 실행 중이 아니었습니다"; fi
}

# ── 명령 ────────────────────────────────────────────────────────────
cmd_setup() {
  head_ "의존성 설치"
  for d in db backend frontend; do
    if [[ -d "$ROOT/$d" ]]; then
      ( cd "$ROOT/$d" && npm install --silent --no-audit --no-fund ) && ok "$d" || bad "$d 설치 실패"
    fi
  done

  head_ "데이터베이스 마이그레이션 · 시드"
  ( cd "$ROOT/db" && node scripts/migrate.js ) || { bad "마이그레이션 실패"; return 1; }
  for s in regions facilities config reference; do
    ( cd "$ROOT/db" && node "seeds/$s.js" >/dev/null ) && ok "seed:$s" || bad "seed:$s 실패"
  done

  if [[ -f "$ROOT/models/questions_v1.json" ]]; then
    ( cd "$ROOT/db" && node seeds/questions.js >/dev/null ) && ok "seed:questions" || bad "seed:questions 실패"
  else
    warn "models/questions_v1.json 이 없습니다 — 'python3 ml/train.py all' 을 먼저 실행하세요"
  fi
}

cmd_start() {
  head_ "기동"

  if [[ ! -f "$ROOT/models/model_v1.json" ]]; then
    bad "models/model_v1.json 이 없습니다."
    info "먼저 'python3 ml/train.py all' 로 모델을 학습하세요."
    return 1
  fi

  # 백엔드 -------------------------------------------------------
  local pid; pid="$(port_pid "$BACKEND_PORT")"
  if [[ -n "$pid" ]]; then
    warn "포트 $BACKEND_PORT 를 이미 사용 중입니다 (PID $pid). 재시작하려면 stop 후 start 하세요."
  else
    ( cd "$ROOT/backend" \
      && CB_BOOTSTRAP=1 nohup npx tsx src/server.ts >"$BE_LOG" 2>&1 </dev/null & \
      echo $! >"$BE_PID"; disown ) >/dev/null 2>&1
    if wait_for_health "http://127.0.0.1:$BACKEND_PORT/api/v1/health" 40; then
      ok "백엔드  http://127.0.0.1:$BACKEND_PORT/api/v1  (PID $(read_pid "$BE_PID"))"
    else
      bad "백엔드 기동 실패 — 로그를 확인하세요: $BE_LOG"
      tail -20 "$BE_LOG" | sed 's/^/      /'
      return 1
    fi
  fi

  # 프론트엔드 ---------------------------------------------------
  pid="$(port_pid "$FRONTEND_PORT")"
  if [[ -n "$pid" ]]; then
    warn "포트 $FRONTEND_PORT 를 이미 사용 중입니다 (PID $pid)."
  else
    local mode="dev"
    if [[ -d "$ROOT/frontend/dist" && "${CB_SERVE_BUILD:-0}" == "1" ]]; then mode="preview"; fi
    ( cd "$ROOT/frontend" \
      && nohup npx vite "$mode" --port "$FRONTEND_PORT" --host >"$FE_LOG" 2>&1 </dev/null & \
      echo $! >"$FE_PID"; disown ) >/dev/null 2>&1
    if wait_for_port "$FRONTEND_PORT" 40; then
      ok "프론트  http://127.0.0.1:$FRONTEND_PORT  ($mode 모드, PID $(read_pid "$FE_PID"))"
    else
      bad "프론트엔드 기동 실패 — 로그를 확인하세요: $FE_LOG"
      tail -20 "$FE_LOG" | sed 's/^/      /'
      return 1
    fi
  fi

  head_ "접속 주소"
  info "로컬     http://127.0.0.1:$FRONTEND_PORT"
  info "공개     $PUBLIC_ORIGIN  (Nginx 가 $FRONTEND_PORT / $BACKEND_PORT 로 프록시)"
  info "Nginx 설정 예시: deploy/nginx-$PUBLIC_DOMAIN.conf"
}

cmd_stop() {
  head_ "중지"
  stop_one "프론트엔드" "$FE_PID" "$FRONTEND_PORT"
  stop_one "백엔드"     "$BE_PID" "$BACKEND_PORT"
}

cmd_restart() { cmd_stop; sleep 1; cmd_start; }

cmd_status() {
  head_ "상태"
  local bp fp
  bp="$(port_pid "$BACKEND_PORT")"; fp="$(port_pid "$FRONTEND_PORT")"

  if [[ -n "$bp" ]]; then ok "백엔드  실행 중 · 포트 $BACKEND_PORT · PID $bp"
  else bad "백엔드  중지 · 포트 $BACKEND_PORT"; fi

  if [[ -n "$fp" ]]; then ok "프론트  실행 중 · 포트 $FRONTEND_PORT · PID $fp"
  else bad "프론트  중지 · 포트 $FRONTEND_PORT"; fi

  if [[ -n "$bp" ]]; then
    local h; h="$(curl -fsS --max-time 3 "http://127.0.0.1:$BACKEND_PORT/api/v1/health" 2>/dev/null)"
    if [[ -n "$h" ]]; then ok "헬스체크 $h"; else warn "헬스체크 응답 없음"; fi
  fi
}

cmd_check() {
  local fail=0

  head_ "1. 환경"
  command -v node >/dev/null && ok "node $(node -v)" || { bad "node 없음"; fail=1; }
  command -v npm  >/dev/null && ok "npm  $(npm -v)"  || { bad "npm 없음"; fail=1; }
  [[ -f "$ROOT/.env" ]] && ok ".env 존재" || { bad ".env 없음 (.env.example 참고)"; fail=1; }
  info "포트: 프론트 $FRONTEND_PORT · 백엔드 $BACKEND_PORT · 도메인 $PUBLIC_DOMAIN"

  head_ "2. 모델 아티팩트"
  local missing=0
  for f in model_v1.json selection_v1.json uncertainty_v1.json questions_v1.json contribution_v1.json parity_v1.json; do
    if [[ -f "$ROOT/models/$f" ]]; then ok "models/$f"; else bad "models/$f 없음"; missing=1; fi
  done
  (( missing )) && { warn "'python3 ml/train.py all' 로 생성하세요"; fail=1; }

  head_ "3. 데이터베이스"
  if node "$ROOT/db/scripts/verify.js" 2>/dev/null; then :; else bad "DB 점검 실패"; fail=1; fi

  head_ "4. 서비스"
  if [[ -z "$(port_pid "$BACKEND_PORT")" ]]; then
    warn "백엔드가 실행 중이 아닙니다 — API 점검을 건너뜁니다 ('./check_project.sh start')"
  else
    local base="http://127.0.0.1:$BACKEND_PORT/api/v1"
    for ep in health questions regions config model; do
      if curl -fsS --max-time 5 "$base/$ep" >/dev/null 2>&1; then ok "GET /$ep"; else bad "GET /$ep 실패"; fail=1; fi
    done
    if curl -fsS --max-time 5 "$base/facilities?lat=37.5665&lng=126.978&radiusKm=10" >/dev/null 2>&1; then
      ok "GET /facilities"
    else bad "GET /facilities 실패"; fail=1; fi
  fi
  if [[ -n "$(port_pid "$FRONTEND_PORT")" ]]; then
    curl -fsS --max-time 5 "http://127.0.0.1:$FRONTEND_PORT/" >/dev/null 2>&1 \
      && ok "프론트엔드 응답" || { bad "프론트엔드 응답 없음"; fail=1; }
  else
    warn "프론트엔드가 실행 중이 아닙니다"
  fi

  head_ "결과"
  if (( fail )); then bad "점검에서 문제가 발견되었습니다"; return 1
  else ok "모든 점검을 통과했습니다"; fi
}

cmd_logs() {
  local which="${1:-be}"
  case "$which" in
    be|backend)  tail -f "$BE_LOG" ;;
    fe|frontend) tail -f "$FE_LOG" ;;
    *) echo "사용법: $0 logs [be|fe]"; return 1 ;;
  esac
}

usage() {
  cat <<EOF
사용법: ./check_project.sh <명령>

  start      백엔드($BACKEND_PORT) + 프론트엔드($FRONTEND_PORT) 기동
  stop       두 서비스 중지
  restart    중지 후 재기동
  status     포트 · PID · 헬스체크
  check      전체 점검 (환경 · 모델 · DB · API)
  setup      의존성 설치 + 마이그레이션 + 시드
  logs [be|fe]  로그 따라가기

공개 도메인: $PUBLIC_ORIGIN
EOF
}

case "${1:-}" in
  start)   cmd_start ;;
  stop)    cmd_stop ;;
  restart) cmd_restart ;;
  status)  cmd_status ;;
  check)   cmd_check ;;
  setup)   cmd_setup ;;
  logs)    shift; cmd_logs "${1:-be}" ;;
  ""|-h|--help|help) usage ;;
  *) echo "알 수 없는 명령: $1"; usage; exit 1 ;;
esac
