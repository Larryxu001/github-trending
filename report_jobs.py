#!/usr/bin/env python3
"""Collect without AI; prepare immutable reports; publish one Feishu message per issue."""
import calendar
import datetime
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
from html.parser import HTMLParser

from report_state import BASE, now, load, write
from sync_saved import build_report
from render_html import render
from run_daily import build_web_index


def sh(*args):
    return subprocess.check_output(args, cwd=BASE, text=True).strip()


def checkpoint(message):
    # saved.json belongs to the collection Worker; never stage it here.
    paths = [p for p in ("collected.json", "deliveries.json", "pushed.json", "desc_cache.json",
                         "last_push.json", "reports", "reports_web", "data", "archive",
                         "weekly", "monthly") if (BASE / p).exists()]
    sh("git", "add", "--", *paths)
    if not sh("git", "diff", "--cached", "--name-only"):
        return
    sh("git", "commit", "-m", message)
    for attempt in range(3):
        sh("git", "pull", "--rebase", "origin", "main")
        try:
            sh("git", "push", "origin", "HEAD:main")
            return
        except subprocess.CalledProcessError:
            if attempt == 2:
                raise


def daily_items(catalog, pushed, today, deliveries=None):
    pushed = dict(pushed)
    # An accepted message followed by a failed receipt commit must not reappear tomorrow.
    # Uncertain messages also require manual resolution instead of blind resending.
    for key, delivery in (deliveries or {}).items():
        if key.startswith("daily:") and delivery["status"] in ("sent", "sending", "unknown"):
            for cat in delivery["report"]["categories"]:
                for it in cat["items"]:
                    pushed[it["repo"]] = max(pushed.get(it["repo"], ""), delivery["report"]["date"])
    cutoff = (today - datetime.timedelta(days=30)).isoformat()
    items = [dict(it) for repo, it in catalog["items"].items()
             if it["last_seen"][:10] > cutoff and pushed.get(repo, "") <= cutoff]
    return {"date": today.isoformat(), "items": items,
            "skipped_already_pushed": len(catalog["items"]) - len(items)}


def weekly_report(saved, monday):
    start = monday - datetime.timedelta(days=7)
    items = [it for it in saved["items"]
             if start.isoformat() <= (it.get("saved_at") or "")[:10] < monday.isoformat()]
    report = build_report(items)
    report.update(date=monday.isoformat(), kind="weekly",
                  period_start=start.isoformat(), period_end=monday.isoformat())
    return report


def monthly_report(weekly_reports, month):
    selected = sorted((r for r in weekly_reports if r["date"][:7] <= month),
                      key=lambda r: r["date"])[-4:]
    merged = {}
    for report in selected:
        for cat in report["categories"]:
            for it in cat["items"]:
                merged[it["repo"]] = dict(it, category=cat["name"], emoji=cat["emoji"])
    cats = {}
    for it in merged.values():
        cat, emoji = it.pop("category"), it.pop("emoji")
        cats.setdefault(cat, {"name": cat, "emoji": emoji, "items": []})["items"].append(it)
    report = {"new_count": len(merged), "skipped": 0, "categories": list(cats.values())}
    report.update(date=month, kind="monthly", source_weeks=[r["date"] for r in selected])
    return report


def prepare(kind, today):
    if kind == "daily":
        # Also collect at delivery time, so the first deployment has data immediately.
        catalog = load(BASE / "collected.json", {})
        collected_at = catalog.get("last_collected")
        if not collected_at or now() - datetime.datetime.fromisoformat(collected_at) > datetime.timedelta(hours=3):
            sh(sys.executable, "fetch_trending.py", "--collect")
            catalog = load(BASE / "collected.json", {})
        items = daily_items(catalog,
                            load(BASE / "pushed.json", {}), today, load(BASE / "deliveries.json", {}))
        write(BASE / "items.json", items)
        sh(sys.executable, "prepare_report.py")
        if load(BASE / "pending.json", []):
            sh(sys.executable, "desc_auto.py")
        else:
            write(BASE / "new_desc.json", {})
        sh(sys.executable, "apply_desc.py")
        report = load(BASE / "report.json", {})
        report["kind"] = "daily"
    elif kind == "weekly":
        monday = today - datetime.timedelta(days=today.weekday())
        report = weekly_report(load(BASE / "saved.json", None), monday)
    else:
        state = load(BASE / "deliveries.json", {})
        reports = [load(p, {}) for p in (BASE / "weekly").glob("*.json")
                   if state.get(f"weekly:{p.stem}", {}).get("status") == "sent"]
        report = monthly_report(reports, today.strftime("%Y-%m"))
    archive_report(report)
    return report


def archive_report(report):
    date, kind = report["date"], report["kind"]
    actual = sum(len(c["items"]) for c in report["categories"])
    if actual != report["new_count"]:
        raise RuntimeError("Report count does not match its contents")
    stem = date + ("-weekly" if kind == "weekly" else "")
    write(BASE / "data" / f"{stem}.json", report)
    if kind == "daily":
        write(BASE / "archive" / f"report-{date}.json", report)
    else:
        write(BASE / kind / f"{date}.json", report)
    cfg = load(BASE / "config.json", {})
    root = cfg["report_url"].rstrip("/")
    api = load(BASE / "save_config.json", {}).get("save_api", "")
    web = BASE / "reports_web" / date[:4] / stem / "index.html"
    web.parent.mkdir(parents=True, exist_ok=True)
    web.write_text(render(report, api, root + "/saved.html", root + "/index.html"), encoding="utf-8")
    write(BASE / "report.json", report)
    sh(sys.executable, "render_md.py", str(BASE / "report.json"))
    md = BASE / f"report-{date}.md"
    dest = BASE / "reports" / date[:4] / f"{date}.md" if kind == "daily" else BASE / kind / f"{date}.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(md.read_text(encoding="utf-8"), encoding="utf-8")
    build_web_index()


def deploy_pages():
    requested_at = now() - datetime.timedelta(seconds=2)
    dispatched = sh("gh", "workflow", "run", "pages.yml", "--ref", "main")
    match = re.search(r"/actions/runs/(\d+)", dispatched)
    for _ in range(80):
        if match:
            matches = [json.loads(sh("gh", "run", "view", match[1], "--json", "status,conclusion"))]
        else:
            # Older gh versions return no run URL. A concurrent collection commit
            # can change main between dispatch and checkout, so do not filter by SHA.
            runs = json.loads(sh("gh", "run", "list", "--workflow", "pages.yml", "--event", "workflow_dispatch",
                                 "--limit", "5", "--json", "status,conclusion,createdAt"))
            matches = [r for r in runs if datetime.datetime.fromisoformat(r["createdAt"].replace("Z", "+00:00")) >= requested_at]
        if matches and matches[0]["status"] == "completed":
            if matches[0]["conclusion"] != "success":
                raise RuntimeError("Pages deployment failed; no message sent")
            return
        time.sleep(10)
    raise RuntimeError("Pages deployment timed out; no message sent")


def payload(report):
    kind, date = report["kind"], report["date"]
    label = {"daily": "日报", "weekly": "精选周报", "monthly": "精选月报"}[kind]
    stem = date + ("-weekly" if kind == "weekly" else "")
    root = load(BASE / "config.json", {})["report_url"].rstrip("/")
    lines = [f"{date} ｜ 共 **{report['new_count']}** 个项目"]
    if kind == "monthly":
        lines.append(f"合并最近 {len(report['source_weeks'])} 期精选周报，项目去重。")
        lines.append("来源：" + ("、".join(report["source_weeks"]) or "暂无已发送周报"))
    elif kind == "weekly":
        lines.append(f"收藏范围：{report['period_start']} 至 {report['period_end']}（不含结束日）")
    lines.extend(f"{c['emoji']} {c['name']}：{len(c['items'])} 个" for c in report["categories"])
    if not report["new_count"]:
        lines.append("本期没有新增项目。")
    return {"msg_type": "interactive", "card": {
        "config": {"wide_screen_mode": True},
        "header": {"template": "indigo", "title": {"tag": "plain_text", "content": f"GitHub Trending · {label}"}},
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(lines)}},
            {"tag": "action", "actions": [{"tag": "button", "type": "primary",
                "text": {"tag": "plain_text", "content": "查看完整报告"},
                "url": f"{root}/{date[:4]}/{stem}/index.html"}]}]}}


def verify_public_report(report):
    url = payload(report)["card"]["elements"][-1]["actions"][0]["url"]
    expected = sorted(it["repo"] for cat in report["categories"] for it in cat["items"])
    class Projects(HTMLParser):
        def __init__(self):
            super().__init__()
            self.repos = []
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "button" and attrs.get("class") == "save-btn":
                self.repos.append(json.loads(attrs["data-meta"])["repo"])
    for attempt in range(12):
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                page = response.read().decode("utf-8")
            parser = Projects()
            parser.feed(page)
            if report["date"] not in page or sorted(parser.repos) != expected:
                raise RuntimeError("Published report does not match archived projects")
            return
        except Exception:
            if attempt == 11:
                raise
            time.sleep(10)


def send_once(message):
    url = os.environ.get("FEISHU_WEBHOOK") or load(BASE / "config.json", {}).get("feishu_webhook")
    if not url:
        raise RuntimeError("FEISHU_WEBHOOK is missing")
    req = urllib.request.Request(url, data=json.dumps(message).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    # A timeout may occur after receipt. Never automatically resend an ambiguous request.
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.loads(response.read())
    code = result.get("code", result.get("StatusCode"))
    if type(code) is not int or code != 0:
        raise RuntimeError(f"Feishu did not confirm delivery: {result}")


def deliver(key, report, state, persist, send):
    if state.get(key, {}).get("status") in ("sending", "unknown", "sent"):
        raise RuntimeError(f"{key}: already sent or delivery requires manual verification; will not resend")
    state[key] = {"status": "sending", "report": report}
    persist()
    try:
        send(payload(report))
    except Exception:
        state[key]["status"] = "unknown"
        persist()
        raise
    state[key]["status"] = "sent"
    if report["kind"] == "daily":
        pushed = load(BASE / "pushed.json", {})
        for cat in report["categories"]:
            for it in cat["items"]:
                pushed[it["repo"]] = report["date"]
        write(BASE / "pushed.json", pushed)
        write(BASE / "last_push.json", {"date": report["date"]})
    persist()


def run(kind):
    current = now()
    today = current.date()
    if kind == "scheduled":
        # A single schedule prevents daily/weekly/monthly jobs from replacing each
        # other in GitHub's one-pending-run concurrency queue at the same hour.
        kinds = ["collect"]
        if current.hour >= 9:
            kinds.append("daily")
            if today.weekday() == 0:
                kinds.append("weekly")
            if today.day == calendar.monthrange(today.year, today.month)[1]:
                kinds.append("monthly")
        failed = []
        for job in kinds:
            try:
                run(job)
            except Exception as error:
                print(f"[error] {job}: {error}", file=sys.stderr)
                failed.append(job)
        if failed:
            raise RuntimeError("Scheduled jobs failed: " + ", ".join(failed))
        return
    if kind == "collect":
        sh(sys.executable, "fetch_trending.py", "--collect")
        checkpoint("采集 GitHub Trending · " + current.isoformat())
        return
    if current.hour < 9:
        print("[skip] report delivery starts at 09:00 Beijing time")
        return
    if kind == "monthly" and today.day != calendar.monthrange(today.year, today.month)[1]:
        print("[skip] not month end")
        return
    period = today.isoformat() if kind == "daily" else (
        (today - datetime.timedelta(days=today.weekday())).isoformat() if kind == "weekly"
        else today.strftime("%Y-%m"))
    key = f"{kind}:{period}"
    state = load(BASE / "deliveries.json", {})
    if state.get(key, {}).get("status") == "sent" or (
        kind == "daily" and load(BASE / "last_push.json", {}).get("date") == period):
        print(f"[skip] {key}: already delivered")
        return
    if state.get(key, {}).get("status") in ("sending", "unknown"):
        raise RuntimeError(f"{key}: delivery uncertain; check Feishu before any retry")
    report = state.get(key, {}).get("report") or prepare(kind, today)
    state[key] = {"status": "prepared", "report": report}
    def persist():
        write(BASE / "deliveries.json", state)
        checkpoint(f"{key} · {state[key]['status']}")
    persist()
    deploy_pages()
    verify_public_report(report)
    deliver(key, report, state, persist, send_once)


if __name__ == "__main__":
    run(sys.argv[1])
