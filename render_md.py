#!/usr/bin/env python3
"""Render report.json into a pretty local markdown file report-<date>.md for reading/archiving.
Usage: render_md.py [report_json]"""
import json, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
L = {"daily": "日", "weekly": "周", "monthly": "月"}

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "report.json")
    r = json.load(open(path))
    kind = "月报" if len(r["date"]) == 7 else "日报"
    out = [f"# 📊 GitHub Trending {kind} · {r['date']}",
           f"> 今日新项目 **{r['new_count']}** 个 ｜ 30 天去重跳过 {r['skipped']} 个", ""]
    for c in r["categories"]:
        out.append(f"## {c['emoji']} {c['name']}（{len(c['items'])}）")
        out.append("")
        for i, it in enumerate(c["items"], 1):
            s = f"{it['stars']:,}" if isinstance(it["stars"], int) else "暂未获取"
            site = it["site"] if it["site"] == "无" else f"[官网]({it['site']})"
            lists = "/".join(L[x] for x in it["lists"]) + "榜"
            out.append(f"**{i}. [{it['repo']}]({it['url']})**　⭐ {s}")
            out.append(f"> {it['desc']}")
            out.append(f"`📅 更新 {it['updated']}` `👤 {it['owner']}` `🏷 {lists}` `🔗 {site}`")
            out.append("")
    dest = os.path.join(BASE, f"report-{r['date']}.md")
    open(dest, "w").write("\n".join(out))
    print(dest)

if __name__ == "__main__":
    main()
