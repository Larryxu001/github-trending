#!/usr/bin/env python3
"""每周「精选回顾」推送。

读取仓库 saved.json（收藏真源），生成飞书「我的精选」回顾卡片并推送。
由 GitHub Actions weekly.yml 每周调用，零积分、自动。

Usage:
  python sync_saved.py            # 读 saved.json，推飞书
  python sync_saved.py --no-push  # 仅生成 saved_report.json 不推送
"""
import json, os, sys, time, urllib.request, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "github-trending-bot/1.0", "Content-Type": "application/json"}

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
                pass
            return body
        except RuntimeError:
            raise
        except Exception as e:
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"feishu post failed after retries: {last_err}")


def stars_fmt(n):
    return f"{n:,}" if isinstance(n, int) else "—"


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
        })
    for c in cats.values():
        c["items"].sort(key=lambda x: -(x["stars"] or 0))
    categories = sorted(cats.values(), key=lambda c: -sum(i["stars"] or 0 for i in c["items"]))
    return {"date": "精选", "new_count": len(items), "skipped": 0, "categories": categories}


def feishu_cover(report):
    els = [{"tag": "div", "text": {"tag": "lark_md", "content":
            f"我的精选 ｜ 共收藏 **{report['new_count']}** 个项目 ｜ {len(report['categories'])} 个分类"}}]
    els.append({"tag": "note", "elements": [{"tag": "plain_text",
                "content": f"共 {len(report['categories'])} 张卡片 · 按分类浏览"}]})
    return {"config": {"wide_screen_mode": True},
            "header": {"template": "red",
                       "title": {"tag": "plain_text", "content": "★ 我的精选 · GitHub 项目收藏"}},
            "elements": els}


def feishu_cat_card(cat):
    color = FEISHU_COLOR.get(cat["emoji"], "blue")
    els = []
    for i, it in enumerate(cat["items"], 1):
        site = "无" if it["site"] == "无" else f"[{it['site']}]({it['site']})"
        els.append({"tag": "div", "text": {"tag": "lark_md", "content":
            f"**{i}. [{it['repo']}]({it['url']})**　⭐ {stars_fmt(it['stars'])}\n{it['desc']}"}})
        els.append({"tag": "div", "text": {"tag": "lark_md", "content":
            f"👤 {it['owner']} ｜ 🔗 {site}"}})
        els.append({"tag": "hr"})
    return {"config": {"wide_screen_mode": True},
            "header": {"template": color, "title": {"tag": "plain_text",
                       "content": f"{cat['emoji']} {cat['name']} · {len(cat['items'])} 个项目"}},
            "elements": els[:-1]}


def push_feishu(url, report):
    cards = [feishu_cover(report)] + [feishu_cat_card(c) for c in report["categories"]]
    for i, card in enumerate(cards):
        resp = post(url, {"msg_type": "interactive", "card": card})
        print(f"  feishu card {i+1}/{len(cards)}: {resp}", file=sys.stderr)
        time.sleep(1)


def main():
    no_push = "--no-push" in sys.argv
    saved_path = os.path.join(BASE, "saved.json")
    all_items = json.load(open(saved_path, encoding="utf-8")).get("items", [])

    # 每周精选回顾 = 只推「最近 7 天」新收藏的项目，避免重复推送历史收藏、卡片无限膨胀
    # 注意：GitHub Actions 的 ubuntu 默认 UTC 时区，这里显式用北京时间（UTC+8），
    # 避免周一边缘时段（北京 00:00~08:00）的收藏被 UTC 日期误判为「上周」而漏推。
    today = datetime.date.fromtimestamp(
        time.time() + 8 * 3600)  # 北京时间日期
    cutoff = today - datetime.timedelta(days=7)
    items = []
    for it in all_items:
        d = (it.get("saved_at") or "")[:10]
        try:
            if d and datetime.date.fromisoformat(d) >= cutoff:
                items.append(it)
        except ValueError:
            items.append(it)  # 无有效日期则纳入，保守起见不丢

    if not items:
        print("[done] no new saved items in last 7 days, nothing to push", file=sys.stderr)
        return

    report = build_report(items)
    json.dump(report, open(os.path.join(BASE, "saved_report.json"), "w"),
              ensure_ascii=False, indent=1)
    print(f"[done] saved_report.json built: {report['new_count']} items (last 7d) in "
          f"{len(report['categories'])} categories")

    if no_push:
        return

    cfg = json.load(open(os.path.join(BASE, "config.json")))
    feishu = os.environ.get("FEISHU_WEBHOOK") or cfg.get("feishu_webhook") or ""
    if feishu:
        print("pushing to feishu...", file=sys.stderr)
        push_feishu(feishu, report)
    else:
        print("[warn] no feishu webhook configured, skip push", file=sys.stderr)


if __name__ == "__main__":
    main()
