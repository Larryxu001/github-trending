"""Detect stalled collection/delivery, unhealthy Worker and expired credentials."""
import datetime
import json
import os
import urllib.request

from report_state import BASE, load, write, now


def problems():
    current = now()
    errors = []
    catalog = load(BASE / "collected.json", {})
    collected = catalog.get("last_collected")
    if not collected or current - datetime.datetime.fromisoformat(collected) > datetime.timedelta(hours=7):
        errors.append("采集超过 7 小时未更新")
    if current.hour >= 11 and load(BASE / "last_push.json", {}).get("date") != current.date().isoformat():
        errors.append("今天日报尚未完成")
    state = load(BASE / "deliveries.json", {})
    if any(d["status"] in ("sending", "unknown", "prepared") for d in state.values()):
        errors.append("存在未完成的报告，需要查看日志或核对飞书后恢复")
    worker = load(BASE / "save_config.json", {}).get("save_api", "")
    try:
        request = urllib.request.Request(worker.rstrip("/") + "/health", headers={"User-Agent":"github-trending-health"})
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
        if result.get("ok") is not True or result.get("version") != "hardened-v1":
            raise ValueError("Worker health invalid")
    except Exception:
        errors.append("收藏服务或 GitHub PAT 异常")
    failed = os.environ.get("FAILED_WORKFLOW")
    if failed:
        errors.append(f"工作流失败：{failed}")
    return sorted(errors)


def run():
    from report_jobs import checkpoint, send_once
    try:
        errors = problems()
    except Exception:
        errors = ["状态文件损坏，健康检查无法读取"]
    try:
        previous = load(BASE / "health_state.json", {})
    except Exception:
        previous = {}
        errors = sorted(set(errors + ["健康通知状态文件损坏"]))
    if errors == previous.get("errors"):
        print("[health] unchanged; no repeated alert")
        return
    write(BASE / "health_state.json", {"errors":errors, "checked_at":now().isoformat(), "notification":"sending"})
    # Persist intent first: a failed or timed-out alert must not spam on retries.
    checkpoint("健康状态变化 · 通知准备")
    if errors or previous.get("errors"):
        text = "GitHub Trending 故障提醒\n" + "\n".join(errors) if errors else "GitHub Trending 已恢复正常。"
        text += "\n查看：https://github.com/Larryxu001/github-trending/actions"
        send_once({"msg_type":"text", "text":{"content":text}})
    write(BASE / "health_state.json", {"errors":errors, "checked_at":now().isoformat(), "notification":"sent"})
    checkpoint("健康状态变化 · 通知完成")
    print("[health]", "failed" if errors else "healthy")


if __name__ == "__main__":
    run()
