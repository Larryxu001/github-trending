#!/usr/bin/env python3
"""Build monthly report from archived daily report.json files.
Usage: build_monthly.py [YYYY-MM]   (default: current month)
Reads archive/report-YYYY-MM-DD.json, merges unique repos (latest desc wins),
refreshes star counts via GitHub API (token from config.json),
writes monthly-YYYY-MM.json in report.json schema (date="YYYY-MM")."""
import json, os, sys, glob, time, datetime, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "github-trending-bot/1.0"}


def refresh_stars(repos, token):
    stars = {}
    for r in repos:
        try:
            req = urllib.request.Request(f"https://api.github.com/repos/{r}",
                                         headers={**UA, "Authorization": f"Bearer {token}"})
            d = json.loads(urllib.request.urlopen(req, timeout=20).read())
            stars[r] = d.get("stargazers_count")
        except Exception as e:
            print(f"[warn] {r}: {e}", file=sys.stderr)
        time.sleep(0.2)
    return stars


def main():
    month = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().strftime("%Y-%m")
    files = sorted(glob.glob(os.path.join(BASE, "archive", f"report-{month}-*.json")))
    if not files:
        print(f"[error] no archived reports for {month}", file=sys.stderr)
        sys.exit(1)

    merged = {}  # repo -> item (with category/emoji)
    for f in files:
        rep = json.load(open(f))
        for cat in rep["categories"]:
            for it in cat["items"]:
                it2 = dict(it)
                it2["_cat"] = cat["name"]
                it2["_emoji"] = cat["emoji"]
                merged[it["repo"]] = it2  # later days overwrite -> latest desc/stars

    cfg = json.load(open(os.path.join(BASE, "config.json")))
    # token 优先取环境变量（GitHub Actions secrets），其次取 config.json
    token = (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
             or cfg.get("github_token") or "")
    if token:
        stars = refresh_stars(sorted(merged), token)
        for r, s in stars.items():
            if isinstance(s, int):
                merged[r]["stars"] = s

    cats = {}
    for it in merged.values():
        c = cats.setdefault(it["_cat"], {"name": it["_cat"], "emoji": it["_emoji"], "items": []})
        it = {k: v for k, v in it.items() if not k.startswith("_")}
        c["items"].append(it)
    for c in cats.values():
        c["items"].sort(key=lambda x: -(x["stars"] or 0))
    categories = sorted(cats.values(), key=lambda c: -sum(i["stars"] or 0 for i in c["items"]))

    out = {"date": month, "new_count": len(merged), "skipped": 0, "categories": categories}
    dest = os.path.join(BASE, f"monthly-{month}.json")
    json.dump(out, open(dest, "w"), ensure_ascii=False, indent=1)
    print(f"[done] {month}: {len(merged)} projects, {len(categories)} categories -> {dest}")


if __name__ == "__main__":
    main()
