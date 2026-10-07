#!/usr/bin/env python3
"""Build selected-project data; compatibility entry point for the weekly job."""

def build_report(items):
    """把扁平收藏列表整理成 {date, new_count, skipped, categories} 结构。"""
    cats = {}
    for it in items:
        cat = it.get("category") or "其他"
        emoji = it.get("emoji") or "📦"
        c = cats.setdefault(cat, {"name": cat, "emoji": emoji, "items": []})
        c["items"].append({
            "repo": it["repo"],
            "url": it.get("url") or f"https://github.com/{it['repo']}",
            "owner": it.get("owner") or it["repo"].split("/")[0],
            "stars": it.get("stars"),
            "updated": (it.get("saved_at") or "")[:10] or "—",
            "lists": [],
            "desc": it.get("desc") or "",
            "site": it.get("site") or "无",
            "note": it.get("note") or "",
            "tags": it.get("tags") or [],
        })
    for c in cats.values():
        c["items"].sort(key=lambda x: -(x["stars"] or 0))
    categories = sorted(cats.values(), key=lambda c: -sum(i["stars"] or 0 for i in c["items"]))
    return {"date": "精选", "new_count": len(items), "skipped": 0, "categories": categories}



def main():
    from report_jobs import run
    run("weekly")


if __name__ == "__main__":
    main()
