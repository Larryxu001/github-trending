#!/usr/bin/env python3
"""
自动为 pending 项目生成中文描述（无 LLM 依赖）。

策略（按优先级）：
1. 命中内置模板表 DESC_MAP（精心维护的常见/重要仓库 → 分类 + emoji + 中文描述 + 可选官网）
2. 用项目的 topics + 描述关键词做启发式分类，并套用该分类的句式模板生成描述
3. 兜底进「其他」，描述用英文简介兜底翻译式模板

只生成 desc/cat/emoji/site，不碰星数。site 缺省时取 items 里的 homepage，仍空则「无」。
写回 new_desc.json（apply_desc.py 的输入格式）。
"""
import json
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
P = lambda n: os.path.join(BASE, n)

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

# ---- 启发式分类规则（关键词 -> (cat, emoji)）----
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


def classify(repo, lang, topics, desc_en):
    """返回 (cat, emoji)。先看内置表，再看 topics/language 关键词，兜底其他。"""
    if repo in DESC_MAP:
        return DESC_MAP[repo][0], DESC_MAP[repo][1]
    hay = " ".join((topics or []) + [lang or ""] + [desc_en or ""]).lower()
    for cat, emoji, kws in CAT_RULES:
        if any(k in hay for k in kws):
            return cat, emoji
    return "其他", "📦"


def build_desc(cat, lang, desc_en):
    """按分类套用句式模板生成一句中文描述。"""
    lead = desc_en.strip().rstrip(".") if desc_en else ""
    if len(lead) > 120:
        lead = lead[:120] + "…"
    if cat == "AI / 大模型":
        return f"一个与 AI / 大模型相关的开源项目" + (f"，简介：{lead}" if lead else "，可用于模型训练、推理或应用开发。")
    if cat == "Agent 基础设施与框架":
        return f"一个面向 AI Agent 的基础设施/框架类项目" + (f"，简介：{lead}" if lead else "，用于构建、编排或运行智能体。")
    if cat == "Agent 技能与插件":
        return f"一个给 AI 编程助手用的技能/插件项目" + (f"，简介：{lead}" if lead else "，用于扩展 Agent 的能力。")
    if cat == "Agent 效率优化":
        return f"一个提升 AI Agent 效率的项目" + (f"，简介：{lead}" if lead else "，用于省 token、优化上下文或加速工作流。")
    if cat == "开发工具与框架":
        return f"一个开发工具/框架类项目" + (f"，简介：{lead}" if lead else "，帮助开发者更高效地构建软件。")
    if cat == "安全":
        return f"一个安全相关项目" + (f"，简介：{lead}" if lead else "，用于漏洞扫描、审计或安全加固。")
    if cat == "数据 / 数据库":
        return f"一个数据/数据库相关项目" + (f"，简介：{lead}" if lead else "，用于数据存储、处理或分析。")
    if cat == "移动 / 桌面应用":
        return f"一个移动/桌面应用项目" + (f"，简介：{lead}" if lead else "，提供跨平台或终端用户体验。")
    if cat == "学习资源":
        return f"一个学习资源类项目" + (f"，简介：{lead}" if lead else "，提供教程、清单或系统化的学习路径。")
    if cat == "区块链":
        return f"一个区块链/Web3 项目" + (f"，简介：{lead}" if lead else "，涉及加密、去中心化或链上应用。")
    return f"一个开源项目" + (f"，简介：{lead}" if lead else "。")


def main():
    pending = json.load(open(P("pending.json"), encoding="utf-8"))
    items = {i["repo"]: i for i in json.load(open(P("items.json"), encoding="utf-8"))["items"]}
    out = {}
    for p in pending:
        repo = p["repo"]
        if repo in DESC_MAP:
            cat, emoji, desc, site = DESC_MAP[repo]
        else:
            cat, emoji = classify(repo, p.get("language"), p.get("topics"), p.get("readme_hint"))
            desc = build_desc(cat, p.get("language"), p.get("readme_hint"))
            site = None
        home = p.get("homepage") or ""
        out[repo] = {"cat": cat, "emoji": emoji, "desc": desc,
                     "site": site or home or "无"}
    json.dump(out, open(P("new_desc.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"[done] auto-generated {len(out)} descriptions")


if __name__ == "__main__":
    main()
