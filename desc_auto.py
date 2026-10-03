#!/usr/bin/env python3
"""
自动为 pending 项目生成中文描述。

两种模式（自动选择）：
1. 有 DEEPSEEK_API_KEY（环境变量）→ 调用 DeepSeek 大模型，为每个项目生成
   「通俗易懂的一段话（做什么/有什么用/必要时举例）+ 分类 + emoji + 官网」。
2. 无 API Key → 降级到内置规则 + 启发式模板（质量较低，但零成本）。

只生成 desc/cat/emoji/site，不碰星数。site 缺省时取 items 里的 homepage，仍空则「无」。
写回 new_desc.json（apply_desc.py 的输入格式）。

DeepSeek API 为 OpenAI 兼容协议：
  POST https://api.deepseek.com/chat/completions
  模型 deepseek-chat（V3）
"""
import json
import os
import re
import sys
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
P = lambda n: os.path.join(BASE, n)

DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# 允许的分类（约束模型只能在这些里选，保证稳定）
ALLOWED_CATS = [
    "AI / 大模型", "Agent 基础设施与框架", "Agent 技能与插件", "Agent 效率优化",
    "开发工具与框架", "数据 / 数据库", "移动 / 桌面应用", "安全",
    "学习资源", "区块链", "其他",
]
CAT_EMOJI = {
    "AI / 大模型": "🧠", "Agent 基础设施与框架": "🤖", "Agent 技能与插件": "🧩",
    "Agent 效率优化": "⚡", "开发工具与框架": "🛠", "数据 / 数据库": "💾",
    "移动 / 桌面应用": "📱", "安全": "🔐", "学习资源": "📚", "区块链": "⛓",
    "其他": "📦",
}

# ---- 内置精选描述表（repo -> (cat, emoji, desc, site_or_None)）----
DESC_MAP = {
    "flutter/flutter": ("开发工具与框架", "🛠",
        "Google 出品的跨平台 UI 框架，用一套 Dart 代码同时构建 iOS、Android、Web 和桌面应用，性能接近原生。", None),
    "vercel/next.js": ("开发工具与框架", "🛠",
        "目前最主流的 React 全栈框架，支持服务端渲染、静态生成和混合渲染，做网站和 Web 应用的首选。", None),
    "pytorch/pytorch": ("AI / 大模型", "🧠",
        "深度学习领域标杆级框架，提供 GPU 加速的张量计算和动态神经网络，做模型训练和推理的基础设施。", None),
    "getsentry/sentry": ("开发工具与框架", "🛠",
        "开发者常用的错误追踪和性能监控平台，应用崩溃或变慢时能实时定位到具体代码位置。", None),
    "anthropics/claude-code": ("开发工具与框架", "🛠",
        "Anthropic 官方的终端 AI 编程助手，能理解整个代码库、执行任务并处理 git 工作流。", None),
    "harry0703/MoneyPrinterTurbo": ("AI 应用与内容生成", "🎨",
        "输入一个主题即可一键生成高清短视频：AI 自动写文案、找素材、配音、加字幕，全流程自动化。", None),
    "longbridge/gpui-kit": ("开发工具与框架", "🛠",
        "长桥证券开源的 Rust GUI 组件库，基于 GPUI 构建跨平台桌面应用。", "http://gpui-kit.com"),
    "NVIDIA/SkillSpector": ("安全", "🔐",
        "NVIDIA 开源的 Agent 技能安全扫描器，在安装前检测漏洞、提示注入、数据外泄等 70 多种风险。",
        "https://docs.nvidia.com/skills/"),
}

# ---- 启发式分类规则（无 Key 时的降级方案）----
CAT_RULES = [
    ("AI / 大模型", "🧠", ["llm", "large-language", "deep-learning", "machine-learning",
        "rag", "inference", "transformer", "fine-tun", "model", "neural", "gpu-kernel"]),
    ("Agent 基础设施与框架", "🤖", ["agent", "multi-agent", "computer-use", "mcp",
        "agent-framework", "agent-infrastructure", "llm-agent"]),
    ("Agent 技能与插件", "🧩", ["skill", "plugin", "claude-skills", "cursor", "claude-code"]),
    ("Agent 效率优化", "⚡", ["agent-optimization", "context", "token", "workflow", "automation"]),
    ("开发工具与框架", "🛠", ["framework", "cli", "developer-tools", "sdk", "api",
        "web", "react", "vue", "typescript", "javascript", "rust", "go", "python"]),
    ("安全", "🔐", ["security", "vulnerability", "scanner", "cve", "audit", "pentest"]),
    ("数据 / 数据库", "💾", ["database", "sql", "nosql", "data-engineering", "etl", "vector-database"]),
    ("移动 / 桌面应用", "📱", ["mobile", "desktop", "ios", "android", "electron", "tauri"]),
    ("学习资源", "📚", ["awesome", "tutorial", "course", "learning", "roadmap", "book"]),
    ("区块链", "⛓", ["blockchain", "crypto", "ethereum", "web3", "bitcoin"]),
]


# ================= DeepSeek =================

def _llm_one(p):
    """调用 DeepSeek，为单个项目返回 {cat, emoji, desc, site}。"""
    cats_line = "、".join(ALLOWED_CATS)
    system = (
        "你是开源项目解读专家。为给定的 GitHub 项目写一段通俗易懂的中文介绍，"
        "并用一个最贴切的分类来归类。只输出 JSON，不要任何多余文字。"
    )
    user = (
        f"项目名：{p['repo']}\n"
        f"主要语言：{p.get('language') or '未知'}\n"
        f"主题标签：{', '.join(p.get('topics') or [])}\n"
        f"官方英文简介：{p.get('readme_hint') or '（无）'}\n"
        f"官网：{p.get('homepage') or '（无）'}\n\n"
        f"请输出如下 JSON（严格按此结构）：\n"
        f'{{"cat": "从以下选一个：{cats_line}", "desc": "一段话（80-160字），'
        f'用通俗语言说清它做什么、解决什么问题、有什么用，必要时举一个具体例子", '
        f'"site": "官网 URL，没有就写「无」"}}'
    )
    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.4,
        "max_tokens": 500,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_KEY}",
            "User-Agent": "github-trending-bot/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read().decode("utf-8"))
    content = resp["choices"][0]["message"]["content"]
    # 容错：去掉可能的 markdown 代码块包裹
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.S).strip()
    d = json.loads(content)
    cat = d.get("cat", "其他")
    if cat not in ALLOWED_CATS:
        cat = "其他"
    site = (d.get("site") or "").strip()
    if site in ("", "无", "null", "None"):
        site = "无"
    desc = (d.get("desc") or "").strip()
    return {"cat": cat, "emoji": CAT_EMOJI.get(cat, "📦"), "desc": desc, "site": site}


def run_llm(pending, items):
    """批量调用 DeepSeek，逐个项目生成描述，失败的降级到规则模板。"""
    out = {}
    for p in pending:
        try:
            r = _llm_one(p)
            # 官网优先用 GitHub API 里的 homepage（更可靠）
            if r["site"] == "无" and (p.get("homepage")):
                r["site"] = p["homepage"]
            out[p["repo"]] = r
        except Exception as e:
            print(f"[warn] LLM fail {p['repo']}: {e}", file=sys.stderr)
            # 降级到规则
            cat, emoji = classify(p["repo"], p.get("language"), p.get("topics"), p.get("readme_hint"))
            desc = build_desc(cat, p.get("language"), p.get("readme_hint"))
            out[p["repo"]] = {"cat": cat, "emoji": emoji, "desc": desc,
                              "site": p.get("homepage") or "无"}
        import time
        time.sleep(0.3)
    return out


# ================= 降级规则（无 Key 时） =================

def classify(repo, lang, topics, desc_en):
    if repo in DESC_MAP:
        return DESC_MAP[repo][0], DESC_MAP[repo][1]
    hay = " ".join((topics or []) + [lang or ""] + [desc_en or ""]).lower()
    for cat, emoji, kws in CAT_RULES:
        if any(k in hay for k in kws):
            return cat, emoji
    return "其他", "📦"


def build_desc(cat, lang, desc_en):
    lead = desc_en.strip().rstrip(".") if desc_en else ""
    if len(lead) > 120:
        lead = lead[:120] + "…"
    tpl = {
        "AI / 大模型": "一个与 AI / 大模型相关的开源项目",
        "Agent 基础设施与框架": "一个面向 AI Agent 的基础设施/框架类项目",
        "Agent 技能与插件": "一个给 AI 编程助手用的技能/插件项目",
        "Agent 效率优化": "一个提升 AI Agent 效率的项目",
        "开发工具与框架": "一个开发工具/框架类项目",
        "安全": "一个安全相关项目",
        "数据 / 数据库": "一个数据/数据库相关项目",
        "移动 / 桌面应用": "一个移动/桌面应用项目",
        "学习资源": "一个学习资源类项目",
        "区块链": "一个区块链/Web3 项目",
        "其他": "一个开源项目",
    }
    head = tpl.get(cat, "一个开源项目")
    return head + (f"，简介：{lead}" if lead else "。")


def main():
    pending = json.load(open(P("pending.json"), encoding="utf-8"))
    items = {i["repo"]: i for i in json.load(open(P("items.json"), encoding="utf-8"))["items"]}

    if DEEPSEEK_KEY:
        print(f"[ok] using DeepSeek LLM for {len(pending)} items", file=sys.stderr)
        out = run_llm(pending, items)
    else:
        print("[warn] no DEEPSEEK_API_KEY, fallback to rule-based templates", file=sys.stderr)
        out = {}
        for p in pending:
            repo = p["repo"]
            if repo in DESC_MAP:
                cat, emoji, desc, site = DESC_MAP[repo]
                out[repo] = {"cat": cat, "emoji": emoji, "desc": desc,
                             "site": site or p.get("homepage") or "无"}
            else:
                cat, emoji = classify(repo, p.get("language"), p.get("topics"), p.get("readme_hint"))
                desc = build_desc(cat, p.get("language"), p.get("readme_hint"))
                out[repo] = {"cat": cat, "emoji": emoji, "desc": desc,
                             "site": p.get("homepage") or "无"}

    json.dump(out, open(P("new_desc.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"[done] generated {len(out)} descriptions")


if __name__ == "__main__":
    main()
