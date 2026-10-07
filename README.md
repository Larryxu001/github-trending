# github-trending

GitHub Trending 持续收录与精选分层日报。主流程由 GitHub Actions 自动运行，不需要 Codex 或 WorkBuddy 在线。

## 运行规则（北京时间 UTC+8）

| 流程 | 时间 | 内容 | AI token |
|---|---|---|---|
| 采集 | 每 3 小时，00/03/06/09/12/15/18/21 点 | 保存日、周、月三榜出现的项目，不发飞书 | 不消耗 |
| 日报 | 每天 09:00 | 累计采集、尚未推送的新项目，30 天项目去重 | 仅新项目描述使用 DeepSeek，缓存复用 |
| 精选周报 | 每周一 09:00 | 上周一至本周一（不含本周一）新增且仍在收藏里的项目 | 不消耗 |
| 精选月报 | 月末 09:00 | 当时最近 4 期已发送精选周报的项目并集，同项目去重 | 不消耗 |

每期只发送 **一条飞书摘要消息 + 完整网页链接**。详细描述、备注、标签保存在网页和 Markdown 中。
月报可能跨月；不足 4 期时标明实际来源期数，不把旧日报混入精选月报。
GitHub Actions 定时执行可能延迟，09:00 是计划时间。

## 主流程

- `report_jobs.py`：统一采集、报告构建、归档、部署、发送入口。
- `fetch_trending.py --collect`：采集并累计保存到 `collected.json`，每天刷新一次项目元数据。
- `prepare_report.py / desc_auto.py / apply_desc.py`：生成日报描述，缓存复用，缺描述时停止发布。
- `report_state.py`：显式北京时间与原子 JSON 写入。
- `deliveries.json`：持久化每期报告和发送状态，发送前必须提交到远程。
- `weekly/YYYY-MM-DD.json`：周报快照，是月报来源；`monthly/YYYY-MM.json`：月报快照。
- `reports/`、`data/`、`archive/`、`reports_web/`：完整报告及公开网页。
- `saved.json`：收藏真源，由收藏 Worker 管理，Actions 不提交此文件。

网页版：[往期归档](https://larryxu001.github.io/github-trending/)。

## 密钥与运行

GitHub Secrets：`FEISHU_WEBHOOK`、可选 `DEEPSEEK_API_KEY`。工作流注入 `GH_TOKEN=${{ github.token }}`。
`config.json` 只保留无密钥模板。没有 DeepSeek key 时使用规则描述。

在 Actions 手动运行 `Collect Trending` 只采集，不发送消息。
手动运行日报、周报或月报使用同一去重守卫；北京时间 09:00 前跳过发送，月报非月末跳过。
旧入口 `run_daily.py / sync_saved.py / build_monthly.py` 转到统一流程；旧 `push.py` 为历史底层脚本，不应直接调用。

## 验证

```bash
python3 -m unittest discover -s tests -v
```

故障恢复、重复发送保护与限制见 [RUNBOOK.md](RUNBOOK.md)。
