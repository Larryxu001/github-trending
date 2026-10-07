#!/usr/bin/env python3
"""Collect without AI; prepare immutable reports; publish one Feishu card batch per issue."""
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
import urllib.error
from html.parser import HTMLParser
from html import escape

from report_state import BASE, now, load, write
from sync_saved import build_report
from render_html import render
from run_daily import build_web_index
from push import feishu_cover, feishu_cat_card


def sh(*args):
    return subprocess.check_output(args, cwd=BASE, text=True).strip()


def checkpoint(message):
    # saved.json belongs to the collection Worker; never stage it here.
    paths = [p for p in ("collected.json", "deliveries.json", "pushed.json", "desc_cache.json",
                         "last_push.json", "reports", "reports_web", "data", "archive",
                         "weekly", "monthly", "health_state.json") if (BASE / p).exists()]
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
        if key.startswith("daily:") and (delivery["status"] in ("sent", "sending", "unknown") or
                any(c["status"] in ("sent", "sending", "unknown") for c in delivery.get("cards", []))):
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


def report_url(report):
    date = report["date"]
    stem = date + ("-weekly" if report["kind"] == "weekly" else "")
    return load(BASE / "config.json", {})["report_url"].rstrip("/") + f"/{date[:4]}/{stem}/index.html"


def payloads(report):
    """Original colored cover + separate category cards, split without dropping items."""
    category_cards = []
    for cat in report["categories"]:
        chunk = []
        for it in cat["items"]:
            trial = feishu_cat_card(dict(cat, items=chunk + [it]))
            size = len(json.dumps({"msg_type": "interactive", "card": trial}, ensure_ascii=False).encode())
            if chunk and (len(trial["elements"]) > 45 or size > 18000):
                category_cards.append(feishu_cat_card(dict(cat, items=chunk)))
                chunk = []
            chunk.append(it)
        if chunk:
            category_cards.append(feishu_cat_card(dict(cat, items=chunk)))
    cover = feishu_cover(report, report_url(report), len(category_cards))
    label = {"daily": "日报", "weekly": "精选周报", "monthly": "精选月报"}[report["kind"]]
    cover["header"]["title"]["content"] = f"📊 GitHub Trending {label}"
    if report["kind"] == "weekly":
        cover["elements"][0]["text"]["content"] = f"{report['date']} ｜ 精选 {report['new_count']} 个项目 ｜ 收藏范围 {report['period_start']} 至 {report['period_end']}（不含结束日）"
    elif report["kind"] == "monthly":
        cover["elements"][0]["text"]["content"] = f"{report['date']} ｜ 精选 {report['new_count']} 个项目 ｜ 最近 {len(report['source_weeks'])} 期周报：" + "、".join(report['source_weeks'])
    cover["elements"][-1]["elements"][0]["content"] = f"共 {1 + len(category_cards)} 张卡片，按分类浏览"
    messages = [{"msg_type": "interactive", "card": card} for card in [cover] + category_cards]
    for message in messages:
        if len(json.dumps(message, ensure_ascii=False).encode()) > 20000:
            raise RuntimeError("A single project's card exceeds Feishu size limits; nothing truncated")
    return messages


def verify_public_report(report):
    url = report_url(report)
    expected = sorted(it["repo"] for cat in report["categories"] for it in cat["items"])
    fields = ("repo", "url", "owner", "stars", "desc", "site")
    expected_meta = {it["repo"]: {key: it[key] for key in fields}
                     for cat in report["categories"] for it in cat["items"]}
    class Projects(HTMLParser):
        def __init__(self):
            super().__init__()
            self.repos = []
            self.metadata = {}
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "button" and attrs.get("class") == "save-btn":
                meta = json.loads(attrs["data-meta"])
                self.repos.append(meta["repo"])
                self.metadata[meta["repo"]] = {key: meta[key] for key in fields}
    for attempt in range(12):
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                page = response.read().decode("utf-8")
            parser = Projects()
            parser.feed(page)
            if report["date"] not in page or sorted(parser.repos) != expected or parser.metadata != expected_meta:
                raise RuntimeError("Published report does not match archived projects")
            for cat in report["categories"]:
                for it in cat["items"]:
                    if it.get("note") and escape(it["note"]) not in page:
                        raise RuntimeError("Published report is missing selected-project notes")
            return
        except Exception:
            if attempt == 11:
                raise
            time.sleep(10)


class DeliveryRejected(RuntimeError):
    """The server explicitly rejected the message, so retry is safe."""


def send_once(message, url=None):
    url = url or os.environ.get("FEISHU_WEBHOOK") or load(BASE / "config.json", {}).get("feishu_webhook")
    if not url:
        raise RuntimeError("FEISHU_WEBHOOK is missing")
    req = urllib.request.Request(url, data=json.dumps(message, ensure_ascii=False).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    # A timeout may occur after receipt. Never automatically resend an ambiguous request.
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read())
    except urllib.error.HTTPError as error:
        if 400 <= error.code < 500 and error.code != 408:
            raise DeliveryRejected(f"Feishu HTTP {error.code}") from None
        raise RuntimeError(f"Feishu HTTP {error.code}; delivery uncertain") from None
    code = result.get("code", result.get("StatusCode"))
    if type(code) is not int:
        raise RuntimeError("Feishu returned no valid receipt")
    if code != 0:
        raise DeliveryRejected(f"Feishu rejected message, code={code}")
    return {"code": code, "confirmed_at": now().isoformat()}


def deliver(key, report, state, persist, send):
    if state.get(key, {}).get("status") in ("sending", "unknown", "sent"):
        raise RuntimeError(f"{key}: already sent or delivery requires manual verification; will not resend")
    entry = state.setdefault(key, {"status": "prepared", "report": report})
    if "cards" not in entry:
        entry["cards"] = [{"message": message, "status": "pending"} for message in payloads(report)]
    for index, card in enumerate(entry["cards"]):
        if card["status"] == "sent":
            continue
        if card["status"] in ("sending", "unknown"):
            raise RuntimeError("Card delivery uncertain; manual verification required")
        card["status"] = entry["status"] = "sending"
        persist()
        try:
            receipt = send(card["message"])
        except Exception as error:
            rejected = isinstance(error, DeliveryRejected)
            card["status"] = "pending" if rejected else "unknown"
            entry["status"] = "prepared" if rejected else "unknown"
            persist()
            raise
        card["status"] = "sent"
        card["receipt"] = receipt
        entry["status"] = "prepared"
        persist()
        print(f"[sent] {key}: card {index + 1}/{len(entry['cards'])}")
        time.sleep(1)
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
    state.setdefault(key, {"status": "prepared", "report": report})
    def persist():
        write(BASE / "deliveries.json", state)
        checkpoint(f"{key} · {state[key]['status']}")
    persist()
    deploy_pages()
    verify_public_report(report)
    deliver(key, report, state, persist, send_once)


if __name__ == "__main__":
    run(sys.argv[1])
