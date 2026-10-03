#!/usr/bin/env python3
"""
Sync generated reports into the GitHub archive repo.

Repo layout (Larryxu001/github-trending):
  README.md                      自动生成的索引
  reports/YYYY/YYYY-MM-DD.md     日报（Markdown 存档）
  monthly/YYYY-MM.md             月报（Markdown 存档）
  data/YYYY-MM-DD.json           日报原始数据
站点每日 page:
  index.html                     由 render_html 生成

Usage: python3 sync_github.py [report_json]
"""
import json
import os
import re
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.join(BASE, "repo")
REPO = json.load(open(os.path.join(BASE, "config.json"))).get("github_repo", "")
if not REPO:
    REPO = "Larryxu001/github-trending"


def sh(cmd, cwd=None, check=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed:\n{r.stderr or r.stdout}")
    return r.stdout.strip()


def ensure_clone():
    if os.path.isdir(os.path.join(REPO_DIR, ".git")):
        sh(["git", "pull", "--rebase", "--quiet"], cwd=REPO_DIR)
        return
    if os.path.exists(REPO_DIR):
        raise RuntimeError(f"{REPO_DIR} exists but is not a git repo")
    sh(["gh", "repo", "clone", REPO, REPO_DIR, "--", "--quiet"], check=False)
    if not os.path.isdir(os.path.join(REPO_DIR, ".git")):
        sh(["git", "clone", f"https://github.com/{REPO}.git", REPO_DIR, "--quiet"])


def write(path, content):
    full = os.path.join(REPO_DIR, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf-8").write(content)


def readme_line(path, title, meta):
    return f"- [{title}]({path})　{meta}"


def rebuild_readme():
    rows = []
    months = sorted([d for d in os.listdir(os.path.join(REPO_DIR, "monthly"))
                     if d.endswith(".md")], reverse=True) \
        if os.path.isdir(os.path.join(REPO_DIR, "monthly")) else []
    if months:
        rows.append("## 月报\n")
        for f in months:
            rows.append(readme_line(f"monthly/{f}", f.replace(".md", "") + " 月报", "当月上榜项目全景"))
        rows.append("")
    root = os.path.join(REPO_DIR, "reports")
    if os.path.isdir(root):
        rows.append("## 日报\n")
        years = sorted([d for d in os.listdir(root) if re.fullmatch(r"\d{4}", d)], reverse=True)
        for y in years:
            days = sorted(os.listdir(os.path.join(root, y)), reverse=True)
            for d in days:
                date = d.replace(".md", "")
                meta = ""
                j = os.path.join(REPO_DIR, "data", f"{date}.json")
                if os.path.exists(j):
                    try:
                        r = json.load(open(j, encoding="utf-8"))
                        meta = f"新收录 {r['new_count']} 个项目 · {len(r['categories'])} 个分类"
                    except Exception:
                        pass
                rows.append(readme_line(f"reports/{y}/{d}", date, meta))
        rows.append("")
    head = ("# github-trending\n\nGitHub Trending 日 / 周 / 月三榜每日自动解读："
            "项目用途、开发者、星标、官网、更新日期与分类归档。\n\n"
            "> 由自动化任务每日 09:00 生成并推送，每月最后一天生成月报。\n")
    write("README.md", head + "\n".join(rows) + "\n")


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "report.json")
    report = json.load(open(src, encoding="utf-8"))
    date = report["date"]
    monthly = len(date) == 7

    ensure_clone()

    md_path = os.path.join(BASE, f"report-{date}.md")
    if monthly:
        if os.path.exists(md_path):
            write(f"monthly/{date}.md", open(md_path, encoding="utf-8").read())
        write(f"data/monthly-{date}.json", json.dumps(report, ensure_ascii=False, indent=1))
    else:
        write(f"reports/{date[:4]}/{date}.md",
              open(md_path, encoding="utf-8").read() if os.path.exists(md_path)
              else "# 当天无新上榜项目\n")
        write(f"data/{date}.json", json.dumps(report, ensure_ascii=False, indent=1))

    rebuild_readme()

    msg = f"{'月报' if monthly else '日报'} {date} · 收录 {report['new_count']} 个项目"
    sh(["git", "add", "-A"], cwd=REPO_DIR)
    if sh(["git", "status", "--porcelain"], cwd=REPO_DIR):
        sh(["git", "commit", "-m", msg, "--quiet"], cwd=REPO_DIR)
        sh(["git", "push", "--quiet"], cwd=REPO_DIR)
        print(f"synced {date} to {REPO}")
    else:
        print("nothing to commit")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[sync_github][error] {e}", file=sys.stderr)
        sys.exit(1)
