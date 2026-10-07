#!/usr/bin/env python3
"""
Step A: build report.json skeleton from items.json, reusing cached descriptions.

Cached repos (already described in a previous run) are filled in automatically and
cost zero LLM work. Uncached repos go into the "未分类 / 📦" group with an empty
desc, and are also dumped into pending.json for the agent to write.

Usage:
  python3 prepare_report.py
"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
P = lambda n: os.path.join(BASE, n)

CAT_ORDER = ["Agent 技能与插件", "Agent 基础设施与框架", "Agent 效率优化",
             "AI / 大模型", "AI 应用与内容生成", "开发工具与框架",
             "数据 / 数据库", "移动 / 桌面应用", "安全", "学习资源",
             "区块链", "其他"]


def load(name, default):
    try:
        return json.load(open(P(name), encoding="utf-8"))
    except FileNotFoundError:
        return default


def main():
    data = load("items.json", {"date": "", "items": [], "skipped_already_pushed": 0})
    cache = load("desc_cache.json", {})

    cats, pending = {}, []
    for it in data["items"]:
        repo = it["repo"]
        c = cache.get(repo)
        base = {
            "repo": repo,
            "url": f"https://github.com/{repo}",
            "owner": it.get("owner") or repo.split("/")[0],
            "stars": it.get("stars"),
            "updated": it.get("updated") or "未知",
            "lists": it.get("lists", []),
        }
        if c and c.get("desc"):
            name = c.get("cat") or "其他"
            emoji = c.get("emoji") or "📦"
            base["desc"] = c["desc"]
            base["site"] = c.get("site") or (it.get("homepage") or "无")
            base["_cat"] = name
            base["_emoji"] = emoji
            cats.setdefault(name, {"name": name, "emoji": emoji, "items": []})
            cats[name]["items"].append(base)
        else:
            name = "未分类"
            base["desc"] = ""
            base["site"] = it.get("homepage") or "无"
            base["_cat"] = name
            base["_emoji"] = "📦"
            cats.setdefault(name, {"name": name, "emoji": "📦", "items": []})
            cats[name]["items"].append(base)
            pending.append({
                "repo": repo,
                "owner": base["owner"],
                "stars": it.get("stars"),
                "updated": base["updated"],
                "lists": it.get("lists", []),
                "homepage": it.get("homepage") or "",
                "language": it.get("language") or "",
                "topics": (it.get("topics") or [])[:12],
                "readme_hint": it.get("description") or "",
            })

    order = [c for c in CAT_ORDER if c in cats] + [c for c in cats if c not in CAT_ORDER]
    cats = {k: cats[k] for k in order}
    for c in cats.values():
        c["items"].sort(key=lambda x: -(x["stars"] or 0))

    report = {
        "date": data.get("date"),
        "new_count": len(data["items"]),
        "skipped": data.get("skipped_already_pushed", 0),
        "categories": [cats[k] for k in order],
    }
    json.dump(report, open(P("report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(pending, open(P("pending.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    total = len(data["items"])
    print(f"report.json built: {total} items, "
          f"{total - len(pending)} from cache, {len(pending)} pending.")
    if pending:
        print("pending.json written — describe these repos into new_desc.json")
    else:
        print("nothing to write, all descriptions cached.")


if __name__ == "__main__":
    main()
