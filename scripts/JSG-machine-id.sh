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
    printf '| (공용) | %s | `%s` | %s |\n' "$name" "$id" "$(date '+%Y-%m-%d')" >> "$TABLE"
    member="(이름 대기)"
  fi
fi

sid=""
if [ "${1:-}" = "--hook" ]; then
  hook_input=$(cat)
  sid_full=$(printf '%s' "$hook_input" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("session_id",""))
except Exception: print("")' 2>/dev/null)
  [ -z "$sid_full" ] && sid_full="${CLAUDE_SESSION_ID:-${CLAUDE_CODE_SESSION_ID:-}}"
  sid=$(printf '%s' "$hook_input" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("session_id","")[:8])
except Exception: print("")' 2>/dev/null)
  [ -z "$sid" ] && sid=$(printf '%s' "$hook_input" | grep -o '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/' | cut -c1-8)
fi

if [ "${1:-}" = "--hook" ]; then
  author=$(bash "$ROOT/scripts/JSG-session-author.sh" get "$sid_full" 2>/dev/null)
  if [ -n "$author" ]; then
    ctx="이 세션의 작성자는 ${author} 다 (세션 ${sid} 장부에 기록됨). 작업 기록은 docs/작업기록/${author}.md 에 HH:MM(KST) 시간 태그와 함께 남기고, 커밋은 git -c user.name='${author}' commit 으로 찍는다."
  else
    ctx="이 세션의 작성자가 아직 확정되지 않았다 (세션 ${sid}). 팀이 pioneer3 계정·장비·폴더·기억 저장소를 모두 공유하므로 이전 세션에서 확인된 이름이나 기억을 근거로 사용자를 추측하면 안 된다. 귀속이 필요한 일(작업기록 기록·커밋·산출물 접두어)을 하기 전에 사용자에게 누구인지 짧게 묻고, 답을 들으면 bash scripts/JSG-session-author.sh set <이름> 으로 장부에 기록한 뒤 진행한다."
  fi
  ctx="$ctx 참고 — 기기 $id($name)는 팀 공용이라 사람을 가르지 못한다. 같은 폴더를 여러 세션이 동시에 고치므로 파일은 덮어쓰지 말고 이어 붙인다."
  python3 -c 'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":sys.argv[1]}},ensure_ascii=False))' "$ctx"
else
  author=$(bash "$ROOT/scripts/JSG-session-author.sh" get 2>/dev/null)
  printf '기기 ID   : %s\n기기 이름 : %s\n이 세션 작성자 : %s\n장부      : .claude/session-authors.local.json\n' "$id" "$name" "${author:-(미확정)}"
fi
