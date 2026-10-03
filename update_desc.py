#!/usr/bin/env python3
"""One-off: rewrite desc fields in report.json with plain-language paragraphs."""
import json

BASE = "/Users/larryxu/.workbuddy/github-trending-bot/"

DESC = {
"obra/superpowers": "一套给 AI 编程助手用的「技能框架+开发方法论」。它把资深工程师的工作习惯（先想清楚再动手、小步提交、写测试）固化成可安装的技能包，让 Claude Code 这类工具不再上来就乱写代码。比如你说「做个登录功能」，它会先出方案、拆任务，再逐步实现并自测——像正规军，不像游击队。",
"mattpocock/skills": "TypeScript 教育圈顶流作者 Matt Pocock 公开的自己每天在用的 AI 技能库。相当于把一位顶级工程师调教 AI 助手的私房配置全盘托出，你拷到自己项目里就能用，省去几个月摸索提示词的时间。",
"tt-a1i/archify": "让 AI 助手帮你画专业图表的技能。你说一句「画一个用户下单的系统架构图」，它就生成带动画、可导出高清图片的精美网页图表，比 Mermaid 那种朴素线条好看一个档次——写技术文档、做汇报直接就能用。",
"pbakaus/impeccable": "专治「AI 生成的网页丑」。它是一套喂给 AI 的设计语言规范，教 AI 什么是好的间距、字体层级和配色。装上之后 AI 做的界面明显更像专业设计师出品，而不是千篇一律的模板风。",
"ayghri/i-have-adhd": "一个让 AI「说重点」的技能。默认情况下 AI 喜欢先铺垫一大段背景再给答案，这个技能强制它结论先行、短句输出、拒绝废话——对 ADHD 人群和没耐心的工程师都特别友好。",
"coreyhaines31/marketingskills": "给 AI 助手装上「营销大脑」。包含转化率优化、文案写作、SEO、数据分析等一整套营销技能。比如让它帮你写落地页文案、诊断注册转化率为什么低——相当于请了个 7x24 的免费增长顾问。",
"anthropics/financial-services": "Anthropic 官方出品的金融行业技能包，教 Claude 干金融人的活：读财报、做尽职调查、写投研备忘录等。相当于把金融分析师的标准工作流程固化成了 AI 技能，金融机构落地 AI 的捷径。",
"alirezarezvani/claude-skills": "「全家桶」式 AI 技能合集：380+ 技能、70+ 快捷命令、30+ 专业子 Agent，覆盖编程、营销、产品、合规甚至高管顾问。不想一个个挑技能的话，装这一套基本够日常用了。",
"anthropics/knowledge-work-plugins": "Anthropic 官方为白领知识工作者做的插件库，配合 Claude Cowork 使用，覆盖写文档、做表格、整理调研资料等日常办公场景——让 AI 真正接手办公室里的重复杂活。",
"google/skills": "Google 官方技能集，教 AI 助手熟练使用 Google 家的产品和技术（Google Cloud 等）。技术栈在 Google 生态里的团队直接用，省去自己写集成说明的功夫。",
"cursor/plugins": "Cursor 编辑器的官方插件规范与官方插件集。想知道 Cursor 插件怎么写、官方都提供了哪些能力，看这一个仓库就够了——Cursor 插件开发的「官方说明书」。",
"paperclipai/paperclip": "当公司里同时跑着好几个 AI Agent，这个开源应用就是它们的「人事部+项目管理台」：分配任务、查看进度、管理权限。相当于给你的 AI 员工们请了一位项目经理。",
"Panniantong/Agent-Reach": "AI 助手自己不会刷网页？这个工具一条命令行就让它能读 Twitter、Reddit、YouTube、B站、小红书的内容，而且不用花钱买各家的 API。比如跟 AI 说「总结一下今天 Reddit 上关于某话题的讨论」，它就能自己去抓、自己读、自己写摘要。",
"vectorize-io/hindsight": "给 AI Agent 装的「会成长的记忆」。普通记忆只是存聊天记录，Hindsight 会从过去的成功和失败里总结规律，下次遇到类似任务做得更好——让 AI 像新人一样逐渐变成老手。",
"THU-MAIC/OpenMAIC": "清华团队做的开源「AI 互动课堂」：多个 AI 分别扮演老师、助教、同学陪你一起学，一键就能开课。比看录播课有互动感得多，适合搭企业内训或在线教育产品。",
"trycua/cua": "让 AI 像人一样操作电脑的基础设施：模拟鼠标键盘、跨 Mac/Windows/Linux 批量部署，还附带训练和评测工具。想做「会操作电脑的 AI」（类似 Claude Computer Use）的团队可以拿它打底。",
"NVIDIA/OpenShell": "英伟达出的 AI Agent「安全屋」。自主运行的 Agent 可能误删文件、乱发请求，OpenShell 给它们一个隔离的运行环境——既能放开手脚干活，又闯不了祸，企业才敢真正放心用。",
"google/ax": "Google 开源的 Agent 编排引擎。当一个任务需要多个 AI 协作（一个查资料、一个写代码、一个验收），它负责调度谁干什么、按什么顺序来——多 Agent 系统的「交通指挥中心」。",
"TencentCloud/Octop": "腾讯云出的自托管 AI 助手平台：支持多人同时使用、多个 Agent 协作、长期记忆。适合想在自己服务器上搭团队共享 AI 助手、又不想让数据出门的公司。",
"mvschwarz/openrig": "把 Claude Code、Codex 这些编程 AI 组建成「常驻开发团队」：给每个 AI 分配角色、共享项目上下文、各自认领任务。像用 tmux 管理终端窗口一样管理一支 AI 开发小队。",
"superdesigndev/treg": "AI Agent 调用各种外部工具需要一堆 API key，treg 做统一的密钥管理和分发，号称「Agent 工具界的 OpenRouter」：一处配好凭证，所有 Agent 都能用，还能细粒度控制权限。",
"affaan-m/ECC": "一套给编程 Agent 做「性能调优」的系统：技能管理、记忆、安全检查、先调研再动手的工作流，适配 Claude Code/Codex/Cursor 等主流工具。目标是让 AI 写代码更快、更稳、更少返工。",
"DietrichGebert/ponytail": "专治 AI「过度设计」的毛病。它让 AI 像房间里最懒的资深工程师一样思考：能复用就不新写，能简单就不复杂——最好的代码是你没写的代码。被 AI 动不动搞出三层抽象折磨过的人，会懂它的价值。",
"JuliusBrussee/caveman": "一个爆火的省钱技巧：让 AI 用「穴居人式」极简英语思考和工作（说 make login work 而不是长篇大论），实测省 65% 的 token 消耗。表面是个梗，实际是真金白银地降 API 账单。",
"colbymchenry/codegraph": "提前把你的代码库索引成「知识图谱」，代码一改自动更新。AI 助手查代码时不用反复翻文件，直接查图谱——省 token、响应快、全程本地不上传。大型项目配 AI 编程的刚需基建。",
"mksglu/context-mode": "AI 编程助手的「上下文瘦身师」：把工具输出里的废话砍掉 98%，只留精华进上下文窗口，还能跨 17 个平台持久保存会话记忆。上下文窗口就那么大，省出来的都是钱和智商。",
"max-sixty/worktrunk": "Git worktree 管理工具，专为「多个 AI 同时改同一个项目」设计：每个 AI 在独立工作区干活互不干扰，最后再合并。多 Agent 并行开发的必备基础设施。",
"pytorch/pytorch": "深度学习领域的事实标准框架，全球几乎所有 AI 研究和大量工业界模型都建立在它上面。从 GPT 类大模型的训练到你手机里的 AI 功能，背后大概率都有 PyTorch。",
"Tencent/WeKnora": "腾讯开源的知识库平台：把公司一堆散落的文档丢进去，就能变成可问答的智能知识库，还能自动整理成 Wiki。典型的 RAG 应用，适合搭企业内部「问啥都知道」的 AI 知识助手。",
"tashfeenahmed/freellmapi": "把 34 家厂商的免费大模型聚合到一个接口：635 个免费模型端点、每月 74 亿 token 额度，自动选路、失败自动切换。个人开发者玩 AI 应用的省钱神器——一个 key 用遍全网免费模型。",
"tile-ai/tilelang": "写 GPU 算子（AI 模型提速的关键环节）门槛很高，这门专用语言让你用接近 Python 的语法写出高性能 kernel，大幅缩短模型推理优化周期。做模型部署加速的团队会很需要。",
"harry0703/MoneyPrinterTurbo": "短视频「印钞机」：输入一个主题（比如「10 个提高工作效率的方法」），AI 自动写稿、找素材、配音、加字幕，输出一条可以直接发抖音/YouTube Shorts 的高清视频。自媒体矩阵号的效率利器。",
"heygen-com/hyperframes": "HeyGen 出的「用 HTML 做视频」框架：写网页代码，渲染出来就是视频。对 AI 特别友好——AI 本来就会写 HTML，现在等于直接会做视频了。批量生成营销视频、动态数据视频都很合适。",
"debpalash/VoiceStudio": "开源、完全本地运行的 ElevenLabs 平替：声音克隆、视频配音、听写转写、制作有声书，支持 646 种语言。不想付订阅费、又要求语音数据不出本机的首选方案。",
"bilawalsidhu/gods-eye-view": "浏览器里的「上帝视角」：把公开的卫星、航班等真实空间情报数据投射到一个照片级 3D 地球上，像情报指挥中心的大屏。GIS 爱好者和开源情报（OSINT）玩家的玩具兼工具。",
"flutter/flutter": "Google 的跨平台 UI 框架：写一套代码，同时产出 iOS、Android、Web 和桌面应用。闲鱼、Google Pay 等知名 App 都是 Flutter 做的，目前跨平台开发最主流的选择之一。",
"anthropics/claude-code": "Anthropic 官方的 AI 编程工具，住在你的终端里：能读懂整个代码库、自己执行命令、处理 git 工作流，用自然语言吩咐它干活就行。当前最火的 Agent 编程工具之一。",
"vercel/next.js": "React 生态最主流的全栈框架：服务端渲染、静态生成、路由方案一把抓。从个人博客到大厂官网都在用，也是前端简历上的必备技能。",
"getsentry/sentry": "线上应用出错了谁第一个知道？Sentry。它自动收集报错堆栈、监控性能瓶颈，让用户还没投诉你就把问题修好了——几乎所有正经互联网公司的标配。",
"alibaba/open-code-review": "阿里开源的 AI 代码评审工具：规则引擎+大模型双保险，能精确到行级指出空指针、线程安全、SQL 注入等问题，经过阿里海量代码的实战检验。相当于给团队请了一位不知疲倦的 reviewer。",
"Effect-TS/effect": "让 TypeScript 写出「壮如牛」的生产级应用：把并发、错误处理、依赖注入这些最容易出幺蛾子的地方全部类型化、标准化。被 JS 异步地狱折磨过的团队会感受到救赎。",
"anthropics/claude-code-action": "把 Claude Code 接进 GitHub 工作流：在 issue 里 @ 它一下，就能自动分析问题、修改代码、提交 PR。相当于仓库里常驻了一位 7x24 待命的 AI 工程师。",
"longbridge/gpui-kit": "长桥开源的 Rust 桌面 UI 组件库，基于 GPUI（Zed 编辑器同款引擎），性能极好。想做 Rust 跨平台桌面应用——尤其是行情、交易这类实时界面——可以直接用这套现成组件。",
"NVIDIA/SkillSpector": "现在人人都在装 AI 技能包，但技能里可能藏着提示注入、偷数据的恶意代码。这个扫描器在安装前检查 17 类共 71 种风险模式——AI 技能界的「杀毒软件」。",
"rohitg00/ai-engineering-from-scratch": "从零学 AI 工程的完整教程：深度学习、LLM、Agent、强化学习一路讲到实战部署。适合想系统转行或进阶 AI 工程师的人——一个仓库顶一套课。",
"pablostanley/yoinks": "终端里的视频下载器：一条命令把网页视频拉到本地，没有垃圾广告和套路。同类工具里界面最清爽的一个。",
}

r = json.load(open(BASE + "report.json"))
missing = []
for c in r["categories"]:
    for it in c["items"]:
        d = DESC.get(it["repo"])
        if d:
            it["desc"] = d
        else:
            missing.append(it["repo"])
json.dump(r, open(BASE + "report.json", "w"), ensure_ascii=False, indent=1)
print("desc updated, missing:", missing)
