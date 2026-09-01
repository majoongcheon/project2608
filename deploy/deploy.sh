#!/usr/bin/env bash
# deploy.sh — sudo 를 직접 붙이지 말고 이 스크립트를 그냥 실행하세요.
#
#   bash deploy/deploy.sh              설치
#   bash deploy/deploy.sh --rollback   되돌리기
#
# TTY 가 없는 환경(Claude Code 의 ! 실행 등)에서도 동작하도록
# SUDO_ASKPASS 를 걸어 macOS 비밀번호 창을 띄운다.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$(id -u)" -eq 0 ]]; then
  exec bash "$HERE/install-nginx.sh" "$@"          # 이미 root 면 바로 실행
fi

if sudo -n true 2>/dev/null; then
  exec sudo bash "$HERE/install-nginx.sh" "$@"     # 비밀번호 없이 가능하면 그대로
fi

if [[ -t 0 ]]; then
  exec sudo bash "$HERE/install-nginx.sh" "$@"     # 터미널이 있으면 평소처럼 물어본다
fi

# 터미널이 없으면 GUI 비밀번호 창으로 받는다
if ! command -v osascript >/dev/null; then
  echo "터미널도 osascript 도 없어 비밀번호를 받을 수 없습니다." >&2
  echo "Terminal.app 에서 실행하세요:  sudo bash deploy/install-nginx.sh" >&2
  exit 1
fi
echo "비밀번호 입력 창을 띄웁니다. 화면을 확인해 주세요."
export SUDO_ASKPASS="$HERE/askpass.sh"
exec sudo -A bash "$HERE/install-nginx.sh" "$@"
