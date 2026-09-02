#!/usr/bin/env bash
# 기기 식별 — sha256(MAC) 앞 8자로 노트북을 구분한다. 원본 MAC 은 어디에도 저장하지 않는다.
#
#   bash scripts/JSG-machine-id.sh          내 기기 ID 를 사람이 볼 형태로 출력
#   bash scripts/JSG-machine-id.sh --hook   SessionStart 훅용 JSON 출력 (stdin 으로 훅 입력 JSON)
#
# 주의 — 한 기기에서 여러 세션이 동시에 돌면 기기 ID 는 같다.
# 그때 세션을 가르는 것은 session_id 이고, 사람을 가르는 것은 본인이 밝힌 이름뿐이다.
#
# 대조표: docs/작업기록/기기-대조표.md — 처음 보는 기기면 "(이름 대기)" 행을 자동으로 덧붙인다.
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
TABLE="$ROOT/docs/작업기록/기기-대조표.md"

mac=$(ifconfig en0 2>/dev/null | awk '/ether/{print $2; exit}')
[ -z "$mac" ] && mac=$(networksetup -listallhardwareports 2>/dev/null | awk '/Ethernet Address:/{print $3; exit}')
[ -z "$mac" ] && mac="no-mac:$(hostname)"   # MAC 을 못 읽는 환경이면 기기 이름으로 대체

id=$(printf '%s' "$mac" | shasum -a 256 | cut -c1-8)
name=$(scutil --get ComputerName 2>/dev/null || hostname)
name=${name//\"/}

member=""
if [ -f "$TABLE" ]; then
  row=$(grep -F "$id" "$TABLE" | head -1)
  [ -n "$row" ] && member=$(printf '%s' "$row" | awk -F'|' '{gsub(/^[ \t]+|[ \t]+$/,"",$2); print $2}')
  if [ -z "$member" ]; then
    printf '| (이름 대기) | %s | `%s` | %s |\n' "$name" "$id" "$(date '+%Y-%m-%d')" >> "$TABLE"
    member="(이름 대기)"
  fi
fi

sid=""
if [ "${1:-}" = "--hook" ]; then
  hook_input=$(cat)
  sid=$(printf '%s' "$hook_input" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("session_id","")[:8])
except Exception: print("")' 2>/dev/null)
  [ -z "$sid" ] && sid=$(printf '%s' "$hook_input" | grep -o '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/' | cut -c1-8)
fi

if [ "${1:-}" = "--hook" ]; then
  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"기기 ID %s (%s) · 세션 %s. docs/작업기록/기기-대조표.md 기준 이 기기의 팀원은 %s. 다만 이 저장소는 한 기기에서 여러 세션이 동시에 도는 일이 있어 기기 ID 만으로는 팀원이 갈리지 않는다 — 최종 귀속은 반드시 사용자가 이 세션에서 밝힌 이름을 따르고, 밝히기 전에는 단정하지 않는다. 작업 기록은 그 팀원의 docs/작업기록/<이름>.md 에 HH:MM(KST) 시간 태그와 함께 남긴다. 같은 파일을 다른 세션이 동시에 고칠 수 있으니 덮어쓰지 말고 이어 붙인다."}}\n' "$id" "$name" "$sid" "$member"
else
  printf '기기 ID   : %s\n기기 이름 : %s\n팀원      : %s\n대조표    : %s\n' "$id" "$name" "$member" "$TABLE"
fi
