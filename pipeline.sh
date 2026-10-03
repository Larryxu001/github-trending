#!/bin/bash
# GitHub Trending Bot — 标准化每日流水线
#
#   pipeline.sh prepare    # 抓榜 + 去重 + 生成骨架/pending.json  (Step 1-2)
#   pipeline.sh finalize   # 合并描述 + 渲染 + 推送 + 归档 + 去重 + 同步GitHub (Step 3-6)
#
# finalize 内部每一步失败都会立即退出并保持状态文件不变（不写 pushed.json / 不归档）。
set -uo pipefail

BASE="$(cd "$(dirname "$0")" && pwd)"
PY="/Users/larryxu/.workbuddy/binaries/python/versions/3.13.12/bin/python3"
TODAY="$(date +%F)"

say() { echo "[pipeline] $*"; }
fail() { echo "[pipeline][FATAL] $*" >&2; exit 1; }

cmd_prepare() {
  say "== prepare: fetch trending =="
  "$PY" "$BASE/fetch_trending.py" || fail "fetch_trending.py failed"
  say "== prepare: build report skeleton from cache =="
  "$PY" "$BASE/prepare_report.py" || fail "prepare_report.py failed"
  local pending
  pending="$("$PY" -c 'import json;print(len(json.load(open("'"$BASE"'/pending.json"))))')"
  say "pending for writing: $pending"
  echo "$pending"
}

cmd_finalize() {
  local total
  total="$("$PY" -c 'import json;r=json.load(open("'"$BASE"'/report.json"));print(sum(len(c["items"]) for c in r["categories"]))')"

  if [ "$total" -eq 0 ]; then
    # 当天没有新项目：只发一句摘要，不渲染站点、不归档、不动 pushed.json
    say "== no new items today — send summary only =="
    "$PY" "$BASE/push.py" || echo "[pipeline][WARN] push failed" >&2
    say "== finalize: done (empty day) =="
    return 0
  fi

  # 3) merge descriptions written by the agent (skipped automatically when none pending)
  if [ -s "$BASE/new_desc.json" ] && [ "$(tr -d '[:space:]' < "$BASE/new_desc.json")" != "{}" ]; then
    say "== finalize: merge new descriptions =="
    "$PY" "$BASE/apply_desc.py" || fail "apply_desc.py failed"
  else
    say "== finalize: no new descriptions (all cached) — skip apply_desc =="
  fi

  # sanity: every item must have a description before rendering
  "$PY" - "$BASE/report.json" <<'EOF' || fail "report.json contains items without desc (dropped?)"
import json, sys
r = json.load(open(sys.argv[1]))
total = sum(len(c["items"]) for c in r["categories"])
missing = [i["repo"] for c in r["categories"] for i in c["items"] if not i.get("desc")]
if missing:
    print("missing desc:", missing); sys.exit(1)
print(f"report ok: {total} items in {len(r['categories'])} categories")
EOF

  say "== finalize: render html + markdown =="
  "$PY" "$BASE/render_html.py" || fail "render_html.py failed"
  "$PY" "$BASE/render_md.py" || fail "render_md.py failed"

  say "== finalize: push to wecom + feishu =="
  "$PY" "$BASE/push.py" || fail "push.py failed — pushed.json NOT updated"

  say "== finalize: archive + dedupe record =="
  cp "$BASE/report.json" "$BASE/archive/report-$TODAY.json" || fail "archive failed"
  "$PY" - "$BASE" "$TODAY" <<'EOF' || fail "pushed.json update failed"
import json, sys, datetime, os
base, today = sys.argv[1], sys.argv[2]
report = json.load(open(os.path.join(base, "report.json")))
pushed_path = os.path.join(base, "pushed.json")
pushed = json.load(open(pushed_path)) if os.path.exists(pushed_path) else {}
cutoff = (datetime.date.fromisoformat(today) - datetime.timedelta(days=30)).isoformat()
# 清理 30 天窗口之外的旧记录，避免文件无限增长
pushed = {k: v for k, v in pushed.items() if v >= cutoff}
for c in report["categories"]:
    for it in c["items"]:
        pushed[it["repo"]] = today
json.dump(pushed, open(pushed_path, "w"), ensure_ascii=False, indent=1)
print(f"pushed.json updated: {len(pushed)} repos tracked")
EOF

  # new_desc.json 用完即清，避免下次运行误并入旧内容
  : > "$BASE/new_desc.json"

  say "== finalize: sync reports to GitHub repo =="
  "$PY" "$BASE/sync_github.py" || echo "[pipeline][WARN] sync_github failed, continuing" >&2

  say "== finalize: done =="
}

case "${1:-}" in
  prepare)  cmd_prepare ;;
  finalize) cmd_finalize ;;
  *)        echo "usage: pipeline.sh {prepare|finalize}" >&2; exit 2 ;;
esac
