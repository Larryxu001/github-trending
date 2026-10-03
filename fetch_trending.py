#!/usr/bin/env python3
"""Fetch GitHub Trending (daily/weekly/monthly), enrich via GitHub API,
dedupe against pushed.json (30-day window), output items.json with NEW items only."""
import json, re, os, sys, time, urllib.request, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "github-trending-bot/1.0"}

def load_token():
    # 优先环境变量（GitHub Actions secrets），其次 config.json
    env = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if env:
        return env
    try:
        cfg = json.load(open(os.path.join(BASE, "config.json")))
        return cfg.get("github_token") or ""
    except Exception:
        return ""

TOKEN = load_token()

def get(url, api=False):
    headers = dict(UA)
    if api and TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

def last_update_via_atom(path):
    """Fallback: read latest commit date from the repo's atom feed (no API quota)."""
    try:
        xml = get(f"https://github.com/{path}/commits.atom")
        m = re.search(r"<updated>(\d{4}-\d{2}-\d{2})", xml)
        return m.group(1) if m else ""
    except Exception:
        return ""

def parse_trending(since):
    html = get(f"https://github.com/trending?since={since}")
    # repo links appear as <h2 ...><a href="/owner/repo" ...>
    repos = re.findall(r'<h2[^>]*>\s*<a[^>]*href="/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"', html)
    seen, ordered = set(), []
    for p in repos:
        if p not in seen:
            seen.add(p)
            ordered.append(p)
    return ordered

def main():
    lists = {}
    for since in ("daily", "weekly", "monthly"):
        try:
            lists[since] = parse_trending(since)
            print(f"[ok] {since}: {len(lists[since])} repos", file=sys.stderr)
        except Exception as e:
            print(f"[warn] {since} fetch failed: {e}", file=sys.stderr)
            lists[since] = []
        time.sleep(1)

    # merge, keep best (lowest) rank, record which lists
    merged = {}
    for since, repos in lists.items():
        for i, path in enumerate(repos, 1):
            e = merged.setdefault(path, {"lists": [], "best_rank": 99})
            e["lists"].append(since)
            e["best_rank"] = min(e["best_rank"], i)

    # load dedup record, prune >30 days
    pushed_path = os.path.join(BASE, "pushed.json")
    pushed = json.load(open(pushed_path)) if os.path.exists(pushed_path) else {}
    today = datetime.date.today()
    cutoff = today - datetime.timedelta(days=30)
    pushed = {k: v for k, v in pushed.items()
              if datetime.date.fromisoformat(v) > cutoff}
    json.dump(pushed, open(pushed_path, "w"), indent=1)

    new_items = []
    for path, meta in sorted(merged.items(), key=lambda kv: kv[1]["best_rank"]):
        if path in pushed:
            continue
        info = {"repo": path, "lists": meta["lists"], "stars": None,
                "owner": path.split("/")[0], "homepage": "", "description": "",
                "language": "", "topics": [], "updated": ""}
        try:
            d = json.loads(get(f"https://api.github.com/repos/{path}", api=True))
            info["stars"] = d.get("stargazers_count")
            info["homepage"] = d.get("homepage") or ""
            info["description"] = d.get("description") or ""
            info["language"] = d.get("language") or ""
            info["topics"] = d.get("topics") or []
            info["owner"] = d.get("owner", {}).get("login", info["owner"])
            info["updated"] = (d.get("pushed_at") or "")[:10]
        except Exception as e:
            print(f"[warn] api {path}: {e}", file=sys.stderr)
        if not info["updated"]:
            info["updated"] = last_update_via_atom(path)
        new_items.append(info)
        time.sleep(0.5)

    out = os.path.join(BASE, "items.json")
    json.dump({"date": str(today), "items": new_items,
               "skipped_already_pushed": len(merged) - len(new_items)},
              open(out, "w"), ensure_ascii=False, indent=1)
    print(f"[done] new items: {len(new_items)}, skipped (pushed within 30d): {len(merged)-len(new_items)}", file=sys.stderr)
    print(out)

if __name__ == "__main__":
    main()
