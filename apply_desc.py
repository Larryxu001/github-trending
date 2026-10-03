#!/usr/bin/env python3
"""
Step B: merge newly written descriptions into report.json and grow desc_cache.json.

Input is new_desc.json:
  {
    "owner/repo": {"cat": "分类名", "emoji": "🚀", "desc": "中文说明", "site": "https://..."},
    ...
  }

- items are moved out of "未分类" into their real category
- categories are sorted by star count desc (and by CAT_ORDER for the header order)
- desc_cache.json is updated so future runs reuse these descriptions for free

Usage:
  python3 apply_desc.py            # reads new_desc.json
  python3 apply_desc.py --check    # only print omissions
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
P = lambda n: os.path.join(BASE, n)

CAT_ORDER = ["Agent 技能与插件", "Agent 基础设施与框架", "Agent 效率优化",
             "AI / 大模型", "AI 应用与内容生成", "开发工具与框架",
             "数据 / 数据库", "移动 / 桌面应用", "安全", "学习资源",
             "区块链", "其他"]


def load(name, default):
    try:
        return json.load(open(P(name), encoding="utf-8"))
    except Exception:
        return default


def main():
    report = load("report.json", {"categories": []})
    new = load("new_desc.json", {})
    cache = load("desc_cache.json", {})

    flat = {}
    for cat in report["categories"]:
        for it in cat["items"]:
            flat[it["repo"]] = it

    missing = [r for r in flat if not flat[r].get("desc")]
    not_found = [r for r in new if r not in flat]
    if not_found:
        print(f"[warn] unknown repos ignored: {not_found}", file=sys.stderr)

    for repo, info in new.items():
        it = flat.get(repo)
        if not it:
            continue
        it["desc"] = info.get("desc") or it.get("desc") or ""
        if info.get("site"):
            it["site"] = info["site"]
        cat = info.get("cat") or cache.get(repo, {}).get("cat") or "其他"
        emoji = info.get("emoji") or cache.get(repo, {}).get("emoji") or "📦"
        cache[repo] = {"cat": cat, "emoji": emoji,
                       "desc": it["desc"], "site": it.get("site", "无")}
        it["_cat"] = cat
        it["_emoji"] = emoji

    still = [r for r in flat if not flat[r].get("desc")]
    if sys.argv[1:] == ["--check"]:
        print(f"missing descriptions: {len(still)} -> {still}")
        return

    cats = {}
    for repo, it in flat.items():
        if not it.get("desc"):
            continue
        name = it.get("_cat") or "其他"
        emoji = it.get("_emoji") or "📦"
        c = cats.setdefault(name, {"name": name, "emoji": emoji, "items": []})
        c["emoji"] = c["emoji"] or emoji
        it.pop("_cat", None)
        it.pop("_emoji", None)
        c["items"].append(it)

    order = [c for c in CAT_ORDER if c in cats] + [c for c in cats if c not in CAT_ORDER]
    report["categories"] = []
    for k in order:
        cats[k]["items"].sort(key=lambda x: -(x["stars"] or 0))
        report["categories"].append(cats[k])

    json.dump(report, open(P("report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(cache, open(P("desc_cache.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"merged {len(new)} descriptions | still missing {len(still)} | "
          f"cache now {len(cache)} repos")
    if still:
        print("[warn] items without desc were dropped from report.json", file=sys.stderr)


if __name__ == "__main__":
    main()
