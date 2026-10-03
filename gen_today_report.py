#!/usr/bin/env python3
"""One-off: build report.json for 2026-10-03 from items.json + curated mapping."""
import json

BASE = "/Users/larryxu/.workbuddy/github-trending-bot/"
data = json.load(open(BASE + "items.json"))

# repo -> (category, emoji, chinese_desc, site_override_or_None)
M = {
 "obra/superpowers": ("Agent 技能与插件", "🧩", "Agent 技能框架与软件开发方法论，让 AI 编程助手按规范流程干活", None),
 "mattpocock/skills": ("Agent 技能与插件", "🧩", "TypeScript 大佬开源的私人 .agents 技能目录，面向实战工程师", None),
 "tt-a1i/archify": ("Agent 技能与插件", "🧩", "Agent 技能：生成漂亮的架构图、时序图、数据流图，自包含 HTML 可导出", None),
 "pbakaus/impeccable": ("Agent 技能与插件", "🧩", "一套设计语言技能，显著提升 AI 生成界面的设计质量", None),
 "ayghri/i-have-adhd": ("Agent 技能与插件", "🧩", "让编程助手输出 ADHD 友好答案的技能：结论前置、不绕弯子", None),
 "coreyhaines31/marketingskills": ("Agent 技能与插件", "🧩", "给 Claude Code 等 Agent 用的营销技能包：转化率优化、文案、SEO、增长分析", None),
 "anthropics/financial-services": ("Agent 技能与插件", "🧩", "Anthropic 官方金融服务行业 Agent 技能/插件集", None),
 "alirezarezvani/claude-skills": ("Agent 技能与插件", "🧩", "380+ 技能、70+ 命令、30+ 子 Agent 的大合集，覆盖工程、营销、合规等", None),
 "anthropics/knowledge-work-plugins": ("Agent 技能与插件", "🧩", "Anthropic 官方知识工作者插件库，配合 Claude Cowork 使用", None),
 "google/skills": ("Agent 技能与插件", "🧩", "Google 官方 Agent 技能集，覆盖 Google 产品与云技术", None),
 "cursor/plugins": ("Agent 技能与插件", "🧩", "Cursor 官方插件规范与官方插件集", None),
 "paperclipai/paperclip": ("Agent 基础设施与框架", "🤖", "开源的「AI 员工管理台」：统一管理工作中多个 Agent 的任务与协作", None),
 "Panniantong/Agent-Reach": ("Agent 基础设施与框架", "🤖", "给 AI Agent 装上「眼睛」：一条 CLI 读取 Twitter/Reddit/YouTube/B站/小红书，零 API 费用", None),
 "vectorize-io/hindsight": ("Agent 基础设施与框架", "🤖", "会自我学习的 Agent 记忆系统，让 Agent 越用越聪明", None),
 "THU-MAIC/OpenMAIC": ("Agent 基础设施与框架", "🤖", "清华出品：开源多智能体互动课堂，一键获得沉浸式多 Agent 学习体验", None),
 "trycua/cua": ("Agent 基础设施与框架", "🤖", "Computer-Use Agent 基础设施：跨系统驱动、容器集群与训练评测基准", None),
 "NVIDIA/OpenShell": ("Agent 基础设施与框架", "🤖", "为自主 AI Agent 提供的安全、私有运行时沙箱", None),
 "google/ax": ("Agent 基础设施与框架", "🤖", "Google 开源的 Agent 编排运行时", None),
 "TencentCloud/Octop": ("Agent 基础设施与框架", "🤖", "腾讯云自托管的多用户、多 Agent AI 助手，带长期记忆", None),
 "mvschwarz/openrig": ("Agent 基础设施与框架", "🤖", "用 Claude Code/Codex 组建持久化 Agent 团队：角色分工、共享上下文", None),
 "superdesigndev/treg": ("Agent 基础设施与框架", "🤖", "Agent 工具界的 OpenRouter：统一管理工具凭证与路由", None),
 "affaan-m/ECC": ("Agent 效率优化", "⚡", "Agent 性能优化系统：技能、记忆、安全、研究驱动开发，适配 Claude Code/Codex/Cursor", None),
 "DietrichGebert/ponytail": ("Agent 效率优化", "⚡", "让 AI Agent 像「最懒的资深工程师」一样思考：能不写的代码就不写（YAGNI）", None),
 "JuliusBrussee/caveman": ("Agent 效率优化", "⚡", "病毒式技能+代理：让编程 Agent「说穴居人话」，省 65% token", None),
 "colbymchenry/codegraph": ("Agent 效率优化", "⚡", "预索引代码知识图谱，代码变更自动同步，为 Agent 省 token 省工具调用，100% 本地", None),
 "mksglu/context-mode": ("Agent 效率优化", "⚡", "AI 编程 Agent 上下文窗口优化：工具输出沙箱化（减 98%），支持 17 个平台", None),
 "max-sixty/worktrunk": ("Agent 效率优化", "⚡", "Git worktree 管理 CLI，专为多 Agent 并行工作流设计", None),
 "pytorch/pytorch": ("AI / 大模型", "🧠", "深度学习框架标杆：GPU 加速张量计算与动态神经网络", None),
 "Tencent/WeKnora": ("AI / 大模型", "🧠", "腾讯开源 LLM 知识平台：文档变 RAG 问答、推理 Agent 和自维护 Wiki", None),
 "tashfeenahmed/freellmapi": ("AI / 大模型", "🧠", "聚合 34 家免费 LLM 提供商、635 个免费端点到统一 /v1 接口，智能路由与故障转移", None),
 "tile-ai/tilelang": ("AI / 大模型", "🧠", "高性能 GPU/CPU 算子开发领域专用语言（DSL），简化 kernel 编写", None),
 "harry0703/MoneyPrinterTurbo": ("AI 应用与内容生成", "🎨", "输入主题一键生成高清短视频：AI 文案+素材+配音+字幕全自动", None),
 "heygen-com/hyperframes": ("AI 应用与内容生成", "🎨", "写 HTML 渲染视频，专为 Agent 设计的程序化视频生成框架", None),
 "debpalash/VoiceStudio": ("AI 应用与内容生成", "🎨", "开源本地版 ElevenLabs：声音克隆、配音、听写、转写、有声书，支持 646 种语言", None),
 "bilawalsidhu/gods-eye-view": ("AI 应用与内容生成", "🎨", "浏览器里的「间谍卫星模拟器」：真实开源空间情报数据+逼真 3D 地球", None),
 "flutter/flutter": ("开发工具与框架", "🛠", "Google 跨平台 UI 框架，一套代码构建移动/桌面/Web 应用", None),
 "anthropics/claude-code": ("开发工具与框架", "🛠", "终端里的 Agent 编程工具：理解代码库、执行任务、处理 git 工作流", None),
 "vercel/next.js": ("开发工具与框架", "🛠", "最流行的 React 全栈框架：SSR/SSG/混合渲染", None),
 "getsentry/sentry": ("开发工具与框架", "🛠", "开发者首选的错误追踪与性能监控平台", None),
 "alibaba/open-code-review": ("开发工具与框架", "🛠", "阿里开源代码评审工具：确定性流水线+LLM Agent 混合架构，内置多语言安全规则集", None),
 "Effect-TS/effect": ("开发工具与框架", "🛠", "TypeScript 生产级应用框架：结构化并发、错误处理、依赖注入", None),
 "anthropics/claude-code-action": ("开发工具与框架", "🛠", "Claude Code 官方 GitHub Action，在 CI 中自动处理 issue 和 PR", None),
 "longbridge/gpui-kit": ("开发工具与框架", "🛠", "长桥开源：基于 GPUI 的 Rust GUI 组件库，构建跨平台桌面应用", None),
 "NVIDIA/SkillSpector": ("安全", "🔐", "NVIDIA 开源 Agent 技能安全扫描器：安装前检测漏洞、提示注入、数据外泄等 71 种风险模式", "https://docs.nvidia.com/skills/"),
 "rohitg00/ai-engineering-from-scratch": ("学习资源", "📚", "从零学 AI 工程：深度学习、LLM、Agent、强化学习全栈教程", None),
 "pablostanley/yoinks": ("其他", "📦", "终端视频下载工具，无广告无套路", None),
}

CAT_ORDER = ["Agent 技能与插件", "Agent 基础设施与框架", "Agent 效率优化",
             "AI / 大模型", "AI 应用与内容生成", "开发工具与框架",
             "安全", "学习资源", "其他"]

cats = {c: {"name": c, "emoji": "", "items": []} for c in CAT_ORDER}
for it in data["items"]:
    cat, emoji, desc, site = M[it["repo"]]
    cats[cat]["emoji"] = emoji
    cats[cat]["items"].append({
        "repo": it["repo"],
        "url": f"https://github.com/{it['repo']}",
        "owner": it["owner"],
        "stars": it["stars"],
        "updated": it.get("updated") or "未知",
        "lists": it["lists"],
        "desc": desc,
        "site": site if site is not None else (it["homepage"] or "无"),
    })

for c in cats.values():
    c["items"].sort(key=lambda x: -(x["stars"] or 0))

report = {
    "date": data["date"],
    "new_count": len(data["items"]),
    "skipped": data["skipped_already_pushed"],
    "categories": [cats[c] for c in CAT_ORDER if cats[c]["items"]],
}
json.dump(report, open(BASE + "report.json", "w"), ensure_ascii=False, indent=1)
print("report.json written,", sum(len(c["items"]) for c in report["categories"]), "items")
