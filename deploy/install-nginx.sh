#!/usr/bin/env bash
# install-nginx.sh — p3.sumzip.com vhost 설정을 설치하고 nginx 를 무중단 reload 한다.
#
#   sudo bash deploy/install-nginx.sh            설치
#   sudo bash deploy/install-nginx.sh --rollback 직전 백업으로 되돌리기
#
# 이 nginx 는 vhost 82개를 함께 돌리는 공유 서버다.
#   · servers/p03.conf 하나만 건드린다. nginx.conf 와 다른 vhost 는 손대지 않는다.
#   · 설치 전 타임스탬프 백업을 남긴다.
#   · nginx -t 가 실패하면 즉시 백업으로 되돌리고 reload 하지 않는다.
#   · reload 는 SIGHUP 이라 기존 연결이 끊기지 않는다 (다른 vhost 무중단).

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NGX_DIR="/opt/homebrew/etc/nginx"
TARGET="$NGX_DIR/servers/p03.conf"
SOURCE="$ROOT/deploy/nginx-p3.sumzip.com.conf"
BACKUP_DIR="$NGX_DIR/servers"
NGINX_BIN="/opt/homebrew/bin/nginx"

G=$'\033[32m'; R=$'\033[31m'; Y=$'\033[33m'; N=$'\033[0m'
ok()   { printf '  %s✓%s %s\n' "$G" "$N" "$*"; }
bad()  { printf '  %s✗%s %s\n' "$R" "$N" "$*"; }
warn() { printf '  %s!%s %s\n' "$Y" "$N" "$*"; }

if [[ "$(id -u)" -ne 0 ]]; then
  bad "root 권한이 필요합니다:  sudo bash deploy/install-nginx.sh"
  exit 1
fi

latest_backup() {
  ls -1t "$BACKUP_DIR"/p03.conf.bak.* 2>/dev/null | head -1
}

if [[ "${1:-}" == "--rollback" ]]; then
  B="$(latest_backup)"
  [[ -z "$B" ]] && { bad "되돌릴 백업이 없습니다."; exit 1; }
  cp "$B" "$TARGET" && ok "복원: $(basename "$B")"
  "$NGINX_BIN" -t && "$NGINX_BIN" -s reload && ok "nginx reload 완료"
  exit $?
fi

[[ -f "$SOURCE" ]] || { bad "설정 원본이 없습니다: $SOURCE"; exit 1; }

echo "p3.sumzip.com nginx 설정 설치"

# 1. 백업 --------------------------------------------------------------
if [[ -f "$TARGET" ]]; then
  STAMP="$(date +%Y%m%d-%H%M%S)"
  BAK="$TARGET.bak.$STAMP"
  cp "$TARGET" "$BAK" && ok "백업 생성: $(basename "$BAK")"
else
  warn "기존 p03.conf 가 없습니다 (신규 설치)"
  BAK=""
fi

# 2. 설치 --------------------------------------------------------------
cp "$SOURCE" "$TARGET" || { bad "복사 실패"; exit 1; }
chmod 644 "$TARGET"
ok "설치: $TARGET"

# 3. 검증 --------------------------------------------------------------
echo
echo "설정 검증 (nginx -t)"
if TEST_OUT="$("$NGINX_BIN" -t 2>&1)"; then
  echo "$TEST_OUT" | sed 's/^/  /'
  ok "검증 통과"
else
  echo "$TEST_OUT" | sed 's/^/  /'
  bad "검증 실패 — 변경을 되돌립니다"
  if [[ -n "$BAK" ]]; then cp "$BAK" "$TARGET"; ok "원상 복구 완료"; else rm -f "$TARGET"; ok "설치 파일 제거"; fi
  exit 1
fi

# 4. 무중단 reload -----------------------------------------------------
echo
echo "nginx reload (SIGHUP · 기존 연결 유지)"
if "$NGINX_BIN" -s reload 2>&1 | sed 's/^/  /'; then
  ok "reload 완료"
else
  bad "reload 실패 — 되돌립니다"
  [[ -n "$BAK" ]] && cp "$BAK" "$TARGET" && "$NGINX_BIN" -s reload
  exit 1
fi

# 5. 확인 --------------------------------------------------------------
echo
echo "연결 확인"
sleep 2
for u in "https://p3.sumzip.com/api/v1/health" "https://p3.sumzip.com/"; do
  CODE="$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 "$u")"
  if [[ "$CODE" == "200" ]]; then ok "$u → HTTP $CODE"; else bad "$u → HTTP $CODE"; fi
done

echo
ok "완료. 문제가 있으면:  sudo bash deploy/install-nginx.sh --rollback"
