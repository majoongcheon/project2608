#!/usr/bin/env bash
# 세션별 작성자 장부 — session_id 로 칸이 나뉘므로 세션끼리 서로 덮어쓰지 않는다.
#
#   bash scripts/JSG-session-author.sh get            이 세션의 작성자 (없으면 빈 줄)
#   bash scripts/JSG-session-author.sh set 조성기      이 세션의 작성자를 기록
#   bash scripts/JSG-session-author.sh list           전체 장부
#
# 왜 필요한가 — 팀이 pioneer3 계정을 공유해 기억 저장소까지 공유된다. 기억에 "이 노트북
# 사용자는 X" 라고 적으면 다른 세션이 덮어써서 다음 사람을 오인하게 된다. 세션 id 를
# 열쇠로 삼으면 그 일이 생기지 않는다.
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
LEDGER="$ROOT/.claude/session-authors.local.json"
SID="${CLAUDE_SESSION_ID:-${CLAUDE_CODE_SESSION_ID:-}}"

usage() { sed -n '2,8p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 1; }

case "${1:-}" in
  get)
    [ -f "$LEDGER" ] || exit 0
    SID="${2:-$SID}"; [ -n "$SID" ] || exit 0
    python3 - "$LEDGER" "$SID" <<'PY'
import json,sys
try: d=json.load(open(sys.argv[1],encoding='utf-8'))
except Exception: sys.exit(0)
e=d.get(sys.argv[2][:8]) or {}
print(e.get('name','') if isinstance(e,dict) else e)
PY
    ;;
  set)
    name="${2:-}"; [ -n "$name" ] || usage
    [ -n "$SID" ] || { echo "세션 id 를 못 읽었다 (CLAUDE_SESSION_ID 없음)" >&2; exit 1; }
    mkdir -p "$(dirname "$LEDGER")"
    python3 - "$LEDGER" "$SID" "$name" <<'PY'
import json,sys,os,datetime
path,sid,name=sys.argv[1],sys.argv[2][:8],sys.argv[3]
d={}
if os.path.exists(path):
    try: d=json.load(open(path,encoding='utf-8'))
    except Exception: d={}
d[sid]={'name':name,'declared':datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
json.dump(d,open(path,'w',encoding='utf-8'),ensure_ascii=False,indent=2,sort_keys=True)
print(f'{sid} → {name} 기록됨')
PY
    ;;
  list)
    [ -f "$LEDGER" ] && cat "$LEDGER" || echo "{}"
    ;;
  *) usage ;;
esac
