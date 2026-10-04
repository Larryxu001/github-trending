#!/usr/bin/env python3
"""
GitHub Actions 版每日流水线（完全离线、无 LLM 依赖）。

等价于本机 pipeline.sh 的 prepare + finalize，但「写描述」这一步用 desc_auto.py
（内置表 + 启发式模板）替代人工/模型撰写。

产出（全部写入仓库工作区，由 workflow 提交）：
  - reports/YYYY/YYYY-MM-DD.md        日报 Markdown
  - reports_web/YYYY/YYYY-MM-DD/index.html 网页版（含往期归档站 index）
  - data/YYYY-MM-DD.json               结构化数据
  - pushed.json / desc_cache.json      状态文件（随仓库版本演进）
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
P = lambda n: os.path.join(BASE, n)

SITE_DIR = os.path.join(BASE, "site")          # 每日网页版源
OUT_SITE = os.path.join(BASE, "reports_web")   # 仓库内网页版归档根
ARCHIVE = os.path.join(BASE, "archive")


def sh(*args):
    import subprocess
    # 透传子进程 stdout/stderr，便于在 Actions 日志里排查；失败时抛出带输出的异常
    r = subprocess.run(args)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} failed with exit code {r.returncode}")
    return ""


def main():
    # 1) 抓榜 + 去重 + 骨架
    sh(sys.executable, P("fetch_trending.py"))
    sh(sys.executable, P("prepare_report.py"))

    # 2) 自动写描述（无需模型）
    if os.path.exists(P("pending.json")) and json.load(open(P("pending.json"), encoding="utf-8")):
        sh(sys.executable, P("desc_auto.py"))
    else:
        open(P("new_desc.json"), "w", encoding="utf-8").write("{}")

    # 3) 合并描述 -> report.json
    sh(sys.executable, P("apply_desc.py"))

    report = json.load(open(P("report.json"), encoding="utf-8"))
    date = report["date"]
    total = sum(len(c["items"]) for c in report["categories"])

    # 无新项目：不推送、不归档，直接结束（根目录状态文件由 workflow 提交）
    if total == 0:
        print(f"[done] {date}: no new items (all within 30-day window), nothing to push")
        return

    # 4) 渲染 Markdown + HTML
    sh(sys.executable, P("render_md.py"), P("report.json"))
    sh(sys.executable, P("render_html.py"), P("report.json"))
    sh(sys.executable, P("render_saved.py"))   # 「我的精选」页（读 saved.json）

    # 5) 推送飞书
    sh(sys.executable, P("push.py"), P("report.json"))

    # 6) 归档 + 更新去重记录（推送已成功，才会走到这里）
    os.makedirs(ARCHIVE, exist_ok=True)
    sh("cp", P("report.json"), os.path.join(ARCHIVE, f"report-{date}.json"))
    today = date
    pushed_path = P("pushed.json")
    pushed = json.load(open(pushed_path)) if os.path.exists(pushed_path) else {}
    import datetime
    cutoff = (datetime.date.fromisoformat(today) - datetime.timedelta(days=30)).isoformat()
    pushed = {k: v for k, v in pushed.items() if v >= cutoff}
    for c in report["categories"]:
        for it in c["items"]:
            pushed[it["repo"]] = today
    json.dump(pushed, open(pushed_path, "w"), ensure_ascii=False, indent=1)

    # 7) 布置到仓库工作区（workflow 负责 git add/commit/push）
    os.makedirs(OUT_SITE, exist_ok=True)
    # 日报 md
    md_src = P(f"report-{date}.md")
    ymd_dir = os.path.join(BASE, "reports", date[:4])
    os.makedirs(ymd_dir, exist_ok=True)
    if os.path.exists(md_src):
        open(os.path.join(ymd_dir, f"{date}.md"), "w", encoding="utf-8").write(
            open(md_src, encoding="utf-8").read())
    # 数据 json
    os.makedirs(os.path.join(BASE, "data"), exist_ok=True)
    open(os.path.join(BASE, "data", f"{date}.json"), "w", encoding="utf-8").write(
        json.dumps(report, ensure_ascii=False, indent=1))
    # 网页版归档
    web_dir = os.path.join(OUT_SITE, date[:4], date)
    os.makedirs(web_dir, exist_ok=True)
    idx = os.path.join(SITE_DIR, "index.html")
    if os.path.exists(idx):
        open(os.path.join(web_dir, "index.html"), "w", encoding="utf-8").write(
            open(idx, encoding="utf-8").read())
    # 「我的精选」页放到 reports_web 根（全局唯一入口）
    saved_src = os.path.join(SITE_DIR, "saved.html")
    if os.path.exists(saved_src):
        open(os.path.join(OUT_SITE, "saved.html"), "w", encoding="utf-8").write(
            open(saved_src, encoding="utf-8").read())

    # 8) 重建网页版归档索引 reports_web/index.html
    build_web_index()

    print(f"[done] daily run {date}: {total} items in {len(report['categories'])} categories")


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
            label = d[5:] + ("（月报）" if len(d) == 7 else "")
            items.append(f'<a class="day" href="{y}/{d}/index.html">{label}</a>')
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
 .months {{ display:flex; flex-wrap:wrap; gap:8px; }}
 .day {{ display:inline-block; padding:8px 14px; border:1px solid #E6DDC6; border-radius:4px;
        color:#2B2419; text-decoration:none; font-size:15px; background:#fff; }}
 .day:hover {{ color:#C02B1F; border-color:#C02B1F; }}
 .empty {{ color:#8a7f66; font-style:italic; padding:40px 0; }}
</style></head><body><div class="wrap">
<div class="topline"><span>GITHUB TRENDING ARCHIVE</span><span>往期归档</span></div>
<h1>Github开源趋势日报</h1>
<div class="sub">往期归档 · 由 GitHub Actions 每日自动生成</div>
<div class="nav"><a href="saved.html">★ 我的精选</a></div>
{''.join(items) if items else '<div class="empty">暂无归档，敬请期待</div>'}
</div></body></html>"""
    open(os.path.join(root, "index.html"), "w", encoding="utf-8").write(html)


if __name__ == "__main__":
    main()
