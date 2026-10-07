#!/usr/bin/env python3
"""Compatibility entry point for the daily job; also builds the archive index."""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_SITE = os.path.join(BASE, "reports_web")   # 仓库内网页版归档根


def main():
    from report_jobs import run
    run("daily")


def build_web_index():
    """在 reports_web/index.html 生成往期归档目录（按年月分组，链接到各期 index.html）。"""
    root = OUT_SITE
    years = sorted([d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))
                    and d.isdigit()], reverse=True)
    groups = []  # [(year, [date, ...])]
    for y in years:
        ydir = os.path.join(root, y)
        dates = [d for d in sorted(os.listdir(ydir), reverse=True)
                 if os.path.isdir(os.path.join(ydir, d))]
        if dates:
            groups.append((y, dates))
    items = []
    for y, dates in groups:
        items.append(f'<div class="year">{y}</div>')
        items.append('<div class="months">')
        for d in dates:
            # d 形如 YYYY-MM-DD（日报）或 YYYY-MM（月报）
            if len(d) == 7:
                label, tail = f"{int(d[5:7])} 月", "月报"
            else:
                label, tail = f"{int(d[5:7])} 月 {int(d[8:10])} 日", "精选周报" if d.endswith("-weekly") else "日报"
            items.append(f'<a class="day" href="{y}/{d}/index.html">{label}<span class="tail">{tail}</span></a>')
        items.append('</div>')
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Github开源趋势日报 · 往期归档</title>
<style>
 body {{ margin:0; background:#FBF7EC; color:#2B2419;
        font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif; }}
 .wrap {{ max-width:760px; margin:0 auto; padding:48px 24px 72px; }}
 .topline {{ font-size:11px; letter-spacing:.22em; color:#7A7263;
            display:flex; justify-content:space-between; padding-bottom:12px;
            border-bottom:1px solid #2B2419; }}
 h1 {{ font-family:Georgia,"Songti SC",serif; font-size:34px; margin:24px 0 4px; }}
 .sub {{ color:#8a7f66; font-size:14px; margin-bottom:8px; font-style:italic; }}
 .nav {{ margin:16px 0 8px; font-size:13px; }}
 .nav a {{ color:#C02B1F; text-decoration:none; }}
 .nav a:hover {{ text-decoration:underline; }}
 .year {{ font-family:Georgia,"Songti SC",serif; font-size:20px; font-weight:700;
         margin:28px 0 6px; padding-bottom:4px; border-bottom:3px double #2B2419; }}
 .months {{ display:block; }}
 .day {{ display:flex; align-items:baseline; padding:11px 2px;
        border-bottom:1px dashed #E6DDC6; color:#2B2419; text-decoration:none;
        font-size:16px; background:transparent; font-family:Georgia,"Songti SC",serif; }}
 .day .tail {{ margin-left:auto; font-family:-apple-system,"PingFang SC",sans-serif;
               font-size:11px; color:#8a7f66; letter-spacing:.08em; }}
 .day:hover {{ color:#C02B1F; border-bottom-color:#C02B1F; }}
 .day:hover .tail {{ color:#C02B1F; }}
 .empty {{ color:#8a7f66; font-style:italic; padding:40px 0; }}
</style></head><body><div class="wrap">
<div class="topline"><span>GITHUB TRENDING ARCHIVE</span><span>往期归档</span></div>
<h1>Github开源趋势日报</h1>
<div class="sub">往期归档 · 由 GitHub Actions 每日自动生成</div>
<div class="nav"><a href="saved.html">★ 我的精选</a></div>
{''.join(items) if items else '<div class="empty">暂无归档，敬请期待</div>'}
</div></body></html>"""
    with open(os.path.join(root, "index.html"), "w", encoding="utf-8") as out:
        out.write(html)


if __name__ == "__main__":
    main()
