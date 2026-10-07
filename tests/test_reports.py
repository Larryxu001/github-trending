import copy
import datetime
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import contextlib

import fetch_trending
import report_jobs as jobs
import report_state
import render_html
import apply_desc


def item(repo, saved_at="2026-10-06", **extra):
    return dict(repo=repo, saved_at=saved_at, owner="owner", stars=10,
                url=f"https://github.com/{repo}", desc="项目说明", site="无",
                updated="2026-10-06", lists=["daily"], note="我的备注", tags=["工具"], **extra)


class ReportsTest(unittest.TestCase):
    def test_collection_preserves_repos_that_leave_the_board_and_never_sends(self):
        with tempfile.TemporaryDirectory() as td:
            fixed = datetime.datetime(2026, 10, 7, 12, tzinfo=report_state.BJ)
            with patch.object(fetch_trending, "BASE", td), patch.object(fetch_trending, "now", return_value=fixed), \
                 patch.object(fetch_trending, "parse_trending", return_value=["a/one"]), \
                 patch.object(fetch_trending, "get", return_value=json.dumps({"stargazers_count": 10, "description": "test", "pushed_at": "2026-10-07"})), \
                 patch.object(fetch_trending.time, "sleep"), patch("sys.argv", ["fetch_trending.py", "--collect"]):
                fetch_trending.main()
                with patch.object(fetch_trending, "parse_trending", return_value=["b/two"]):
                    fetch_trending.main()
            data = report_state.load(Path(td) / "collected.json", {})
            self.assertEqual(set(data["items"]), {"a/one", "b/two"})
            self.assertFalse((Path(td) / "pushed.json").exists())
            self.assertFalse((Path(td) / "items.json").exists())

    def test_failed_collection_does_not_replace_last_good_catalog(self):
        for result in ([], OSError("offline")):
            with tempfile.TemporaryDirectory() as td:
                p = Path(td) / "collected.json"
                p.write_text('{"original":true}')
                kwargs = {"side_effect": result} if isinstance(result, Exception) else {"return_value": result}
                with patch.object(fetch_trending, "BASE", td), patch.object(fetch_trending, "parse_trending", **kwargs):
                    with self.assertRaises(RuntimeError):
                        fetch_trending.main()
                self.assertEqual(p.read_text(), '{"original":true}')

    def test_daily_uses_accumulated_items_and_30_day_dedup(self):
        today = datetime.date(2026, 10, 7)
        catalog = {"items": {r: dict(item(r), last_seen="2026-10-07T06:00:00+08:00")
                             for r in ["a/new", "b/recent", "c/old"]}}
        data = jobs.daily_items(catalog, {"b/recent": "2026-10-06", "c/old": "2026-09-07"}, today)
        self.assertEqual({it["repo"] for it in data["items"]}, {"a/new", "c/old"})

    def test_uncertain_daily_items_do_not_repeat_next_day(self):
        catalog = {"items": {"a/project": dict(item("a/project"), last_seen="2026-10-07")}}
        deliveries = {"daily:2026-10-07": {"status": "sending", "report": {
            "date": "2026-10-07", "categories": [{"items": [item("a/project")]}]}}}
        report = jobs.daily_items(catalog, {}, datetime.date(2026, 10, 8), deliveries)
        self.assertEqual(report["items"], [])

    def test_legacy_success_and_before_nine_guard_do_not_prepare_or_send(self):
        for hour in (8, 9):
            with patch.object(jobs, "now", return_value=datetime.datetime(2026, 10, 7, hour, tzinfo=report_state.BJ)), \
                 patch.object(jobs, "load", side_effect=lambda p, d: {"date": "2026-10-07"} if p.name == "last_push.json" else d), \
                 patch.object(jobs, "prepare", side_effect=AssertionError("unexpected prepare")):
                jobs.run("daily")

    def test_scheduler_orders_weekly_before_monthly_and_no_early_delivery(self):
        original = jobs.run
        for hour, expected in ((6, ["collect"]), (9, ["collect", "daily", "weekly", "monthly"])):
            calls = []
            with patch.object(jobs, "now", return_value=datetime.datetime(2026, 8, 31, hour, tzinfo=report_state.BJ)), \
                 patch.object(jobs, "run", side_effect=lambda kind: calls.append(kind)):
                original("scheduled")
            self.assertEqual(calls, expected)

    def test_scheduler_report_failure_does_not_skip_other_due_reports(self):
        original = jobs.run
        calls = []
        def invoke(kind):
            calls.append(kind)
            if kind == "daily":
                raise RuntimeError("failed daily")
        with patch.object(jobs, "now", return_value=datetime.datetime(2026, 8, 31, 9, tzinfo=report_state.BJ)), \
             patch.object(jobs, "run", side_effect=invoke):
            with self.assertRaises(RuntimeError):
                original("scheduled")
        self.assertEqual(calls, ["collect", "daily", "weekly", "monthly"])

    def test_weekly_periods_do_not_overlap_and_keep_notes(self):
        saved = {"items": [item("a/previous", "2026-09-28"), item("b/current", "2026-10-05"), item("c/next", "2026-10-12")]}
        first = jobs.weekly_report(saved, datetime.date(2026, 10, 5))
        second = jobs.weekly_report(saved, datetime.date(2026, 10, 12))
        self.assertEqual(first["new_count"], 1)
        self.assertEqual(second["new_count"], 1)
        it = second["categories"][0]["items"][0]
        self.assertEqual(it["repo"], "b/current")
        self.assertEqual(it["note"], "我的备注")
        self.assertEqual(it["tags"], ["工具"])

    def test_monthly_unions_latest_four_weeks_and_deduplicates(self):
        reports = [dict(date=date, categories=[{"name": "其他", "emoji": "📦", "items": [item("a/same"), item(f"week/{i}")]}])
                   for i, date in enumerate(["2026-09-28", "2026-10-05", "2026-10-12", "2026-10-19", "2026-10-26", "2026-11-02"])]
        report = jobs.monthly_report(reports, "2026-10")
        self.assertEqual(report["source_weeks"], ["2026-10-05", "2026-10-12", "2026-10-19", "2026-10-26"])
        self.assertEqual(report["new_count"], 5)
        self.assertEqual(report["categories"][0]["items"][0]["note"], "我的备注")
        self.assertEqual(jobs.monthly_report([], "2026-10")["new_count"], 0)

    def test_delivery_persists_reservation_before_single_send_and_blocks_retry(self):
        report = jobs.weekly_report({"items": [item("a/project")]}, datetime.date(2026, 10, 12))
        state, snapshots, messages = {}, [], []
        def persist():
            snapshots.append(copy.deepcopy(state))
        def send(message):
            self.assertEqual(snapshots[-1]["weekly:2026-10-12"]["status"], "sending")
            messages.append(message)
        jobs.deliver("weekly:2026-10-12", report, state, persist, send)
        self.assertEqual(len(messages), 1)
        self.assertEqual(state["weekly:2026-10-12"]["status"], "sent")
        with self.assertRaises(RuntimeError):
            jobs.deliver("weekly:2026-10-12", report, state, persist, send)
        self.assertEqual(len(messages), 1)

    def test_timeout_is_not_automatically_resent(self):
        report = jobs.weekly_report({"items": []}, datetime.date(2026, 10, 12))
        state = {}
        with self.assertRaises(TimeoutError):
            jobs.deliver("weekly:2026-10-12", report, state, lambda: None,
                         lambda _: (_ for _ in ()).throw(TimeoutError("ambiguous")))
        self.assertEqual(state["weekly:2026-10-12"]["status"], "unknown")
        with self.assertRaises(RuntimeError):
            jobs.deliver("weekly:2026-10-12", report, state, lambda: None, lambda _: self.fail("resent"))

    def test_checkpoint_failure_prevents_sending(self):
        report = jobs.weekly_report({"items": []}, datetime.date(2026, 10, 12))
        with self.assertRaises(OSError):
            jobs.deliver("weekly:test", report, {}, lambda: (_ for _ in ()).throw(OSError("push failed")),
                         lambda _: self.fail("sent before durable reservation"))

    def test_feishu_requires_explicit_success(self):
        for body in (b'<html>error</html>', b'{}', b'{"code":1}', b'{"code":false}'):
            response = contextlib.nullcontext(io.BytesIO(body))
            with patch.dict(os.environ, {"FEISHU_WEBHOOK": "https://example.invalid"}), \
                 patch.object(jobs.urllib.request, "urlopen", return_value=response):
                with self.assertRaises((RuntimeError, json.JSONDecodeError)):
                    jobs.send_once({})

    def test_public_report_must_match_archived_project_set(self):
        report = jobs.weekly_report({"items": [item("a/project")]}, datetime.date(2026, 10, 12))
        page = render_html.render(report).encode()
        for body, valid in ((page, True), (b"2026-10-12 incomplete page", False)):
            with patch.object(jobs.urllib.request, "urlopen", side_effect=lambda *a, **kw: contextlib.nullcontext(io.BytesIO(body))), \
                 patch.object(jobs.time, "sleep"):
                if valid:
                    jobs.verify_public_report(report)
                else:
                    with self.assertRaises(RuntimeError):
                        jobs.verify_public_report(report)

    def test_archive_monthly_and_weekly_links_notes_and_counts(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "render_md.py").write_text((jobs.BASE / "render_md.py").read_text())
            report_state.write(base / "config.json", {"report_url": "https://example.invalid/"})
            report = jobs.weekly_report({"items": [item("a/project")]}, datetime.date(2026, 10, 12))
            with patch.object(jobs, "BASE", base), patch("run_daily.OUT_SITE", str(base / "reports_web")):
                jobs.archive_report(report)
                jobs.archive_report(jobs.monthly_report([report], "2026-10"))
            page = (base / "reports_web/2026/2026-10-12-weekly/index.html").read_text()
            self.assertIn("精选周报", page)
            self.assertIn("我的备注", page)
            self.assertIn("工具", page)
            self.assertIn("2026/2026-10-12-weekly/index.html", (base / "reports_web/index.html").read_text())
            self.assertIn("2026/2026-10/index.html", (base / "reports_web/index.html").read_text())
            self.assertIn("我的备注", (base / "monthly/2026-10.md").read_text())
            self.assertIn("2026-10-12", (base / "monthly/2026-10.md").read_text())

    def test_missing_description_blocks_publication(self):
        with tempfile.TemporaryDirectory() as td:
            report_state.write(Path(td) / "report.json", {"categories": [{"items": [dict(item("a/project"), desc="")]}]})
            with patch.object(apply_desc, "P", lambda n: str(Path(td) / n)), patch("sys.argv", ["apply_desc.py"]):
                with self.assertRaises(RuntimeError):
                    apply_desc.main()


if __name__ == "__main__":
    unittest.main()
