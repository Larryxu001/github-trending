#!/usr/bin/env python3
"""Render report.json and push to WeCom (rich markdown) / Feishu (interactive cards).
Usage: push.py [report_json]   (default: report.json in this dir)
If config.json has "report_url", a link to the full HTML report is included."""
import json, os, sys, time, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "github-trending-bot/1.0", "Content-Type": "application/json"}
LIST_LABEL = {"daily": "日榜", "weekly": "周榜", "monthly": "月榜"}
# feishu header template colors per category emoji
FEISHU_COLOR = {"🧩": "violet", "🤖": "blue", "⚡": "yellow", "🧠": "carmine",
                "🎨": "green", "🛠": "indigo", "🔐": "red", "📚": "orange",
                "📦": "grey", "💾": "wathet", "📱": "turquoise", "⛓": "purple"}


def post(url, payload):
    # 带重试：飞书 webhook 偶发 429/网络抖动时自动重试，避免丢卡片
    last_err = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read().decode()
            try:
                resp = json.loads(body)
                code = resp.get("code", resp.get("errcode", 0))
                if code == 9499 or code == 125404:  # 频率限制，等待后重试
                    last_err = f"feishu rate limit code={code}"
                    time.sleep(3 * (attempt + 1))
                    continue
                if code != 0:
                    raise RuntimeError(f"feishu error code={code}: {body}")
            except json.JSONDecodeError:
                pass  # 非 JSON 响应，按成功处理（如某些代理）
            return body
        except RuntimeError:
            raise
        except Exception as e:
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"feishu post failed after retries: {last_err}")


def stars_fmt(n):
    return f"{n:,}" if isinstance(n, int) else "暂未获取"


def lists_fmt(lists):
    return "/".join(LIST_LABEL[l][0] for l in lists if l in LIST_LABEL) + "榜"


# ---------- Feishu interactive card renderer ----------

def feishu_cover(report, report_url="", total_cards=1):
    monthly = len(report["date"]) == 7
    kind = "月报" if monthly else "日报"
    if monthly:
        subtitle = f"{report['date']} ｜ 本月共收录 {report['new_count']} 个上榜项目 ｜ {len(report['categories'])} 个分类"
    else:
        subtitle = (f"{report['date']} ｜ 今日新项目 {report['new_count']} 个 ｜ "
                    f"{len(report['categories'])} 个分类 ｜ 30 天去重跳过 {report['skipped']} 个")
    els = [{"tag": "div", "text": {"tag": "lark_md", "content": subtitle}}]
    if report_url:
        els.append({"tag": "action", "actions": [{
            "tag": "button",
            "text": {"tag": "plain_text", "content": "🎨 查看完整精美网页版报告"},
            "type": "primary", "url": report_url}]})
    els.append({"tag": "note", "elements": [{"tag": "plain_text",
                "content": f"共 {total_cards} 张卡片，按分类浏览" + ("" if monthly else " · 30 天内已推送的项目自动跳过")}]})
    return {"config": {"wide_screen_mode": True},
            "header": {"template": "indigo",
                       "title": {"tag": "plain_text", "content": f"📊 GitHub Trending {kind}"}},
            "elements": els}


def feishu_cat_card(cat):
    color = FEISHU_COLOR.get(cat["emoji"], "blue")
    els = []
    for i, it in enumerate(cat["items"], 1):
        # 官网：无官网时写「无」，否则用 lark_md 渲染成可点击的超链接，并显式展示网址
        if it["site"] == "无":
            site = "无"
        else:
            site = f"[{it['site']}]({it['site']})"
        els.append({"tag": "div", "text": {"tag": "lark_md", "content":
            f"**{i}. [{it['repo']}]({it['url']})**　⭐ {stars_fmt(it['stars'])}\n{it['desc']}"}})
        # 元信息用 div + lark_md（而非 note），这样其中的链接才能被点击
        els.append({"tag": "div", "text": {"tag": "lark_md", "content":
            f"👤 {it['owner']} ｜ 📅 更新 {it['updated']} ｜ 🏷 {lists_fmt(it['lists'])} ｜ 🔗 {site}"}})
        els.append({"tag": "hr"})
    return {"config": {"wide_screen_mode": True},
            "header": {"template": color, "title": {"tag": "plain_text",
                       "content": f"{cat['emoji']} {cat['name']} · {len(cat['items'])} 个项目"}},
            "elements": els[:-1]}


def push_feishu(url, report, report_url=""):
    cats = report["categories"]
    cards = [feishu_cover(report, report_url, len(cats))] + [feishu_cat_card(c) for c in cats]
    for i, card in enumerate(cards):
        resp = post(url, {"msg_type": "interactive", "card": card})
        print(f"  feishu card {i+1}/{len(cards)}: {resp}", file=sys.stderr)
        time.sleep(1)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "report.json")
    report = json.load(open(path))
    cfg = json.load(open(os.path.join(BASE, "config.json")))
    report_url = cfg.get("report_url", "")
    # webhook 优先取环境变量（GitHub Actions secrets），其次取 config.json
    feishu = os.environ.get("FEISHU_WEBHOOK") or cfg.get("feishu_webhook") or ""
    if feishu:
        print("pushing to feishu...", file=sys.stderr)
        push_feishu(feishu, report, report_url)
    else:
        print("[error] no feishu webhook configured", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
