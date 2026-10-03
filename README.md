# github-trending

GitHub Trending 日 / 周 / 月三榜，每日自动解读并推送飞书、归档到本仓库。

## 这是什么

每天 09:00（北京时间），GitHub Actions 会自动：

1. 抓取 GitHub Trending 的日榜、周榜、月榜
2. 按 `pushed.json` 做 **30 天去重**（同一项目一个月内不重复推送）
3. 分析每个新项目：开发者、星标数、官网、最近更新日期、项目用途、归类
4. 复用 `desc_cache.json` 里已写过的描述（零重复工作）
5. 渲染成中文 Markdown 日报 + 精美网页版
6. 推送到飞书群机器人
7. 归档到本仓库，自动重建索引

## 目录结构

```
fetch_trending.py      抓榜 + 去重 → items.json
prepare_report.py      骨架 + 描述复用 → report.json / pending.json
desc_auto.py           自动生成中文描述（内置表 + 启发式模板）
apply_desc.py          合并描述 → report.json + desc_cache.json
render_html.py         report.json → 网页版（报纸编辑风）
render_md.py           report.json → Markdown
push.py                推送飞书（交互式卡片）
run_daily.py           Actions 每日流水线入口
pipeline.sh            本机两段式流水线（prepare / finalize）
build_monthly.py       月报构建（合并当月归档）
desc_cache.json        描述缓存（repo → 分类/emoji/描述/官网）
pushed.json            30 天去重记录
reports/YYYY/          日报 Markdown 归档
reports_web/YYYY/      网页版归档 + 索引
data/YYYY-MM-DD.json   结构化数据
archive/               当月日报归档（月报数据源）
state/                 状态文件快照
```

## 网页版

GitHub Pages 免费托管：**https://larryxu001.github.io/github-trending/**

每日/每月的网页版报告都会归档到 `reports_web/`，由 `pages.yml` 自动部署。

## 配置

- **飞书 webhook**：存 GitHub Secrets（`FEISHU_WEBHOOK`），运行时通过环境变量注入，
  **不会写入仓库**（`config.json` 里的 feishu_webhook 保持为空）
- **GitHub token**：工作流用 `${{ github.token }}` 自动注入（`GH_TOKEN` 环境变量），
  用于提高 GitHub API 限额；仓库内公开数据本身不需要额外 token
- **DeepSeek API Key**（可选）：存 GitHub Secrets（`DEEPSEEK_API_KEY`），用于 AI 生成
  项目的中文总结与归类。**未配置时自动降级**为内置规则 + 模板（零成本，描述质量较低）
- 本地开发把真实配置放在 `config.local.json`（已被 .gitignore 忽略）

## 手动触发

在仓库 **Actions** 标签页选 `Daily Trending Report` / `Monthly Trending Report` → **Run workflow**。

## 说明

- 去重窗口 30 天；`pushed.json` 里超过 30 天的记录会自动清理。
- 描述生成：配置了 `DEEPSEEK_API_KEY` 时用 AI 生成（推荐）；否则用内置精选表 +
  按 topics/language 的启发式分类模板。若要手动提升某个项目的描述质量，直接编辑
  `desc_auto.py` 里的 `DESC_MAP` 或 `desc_cache.json` 后提交即可。
- 推送渠道：**仅飞书**（企业微信已移除）。
- 日报每天 09:00（北京时间）自动运行，等价于 cron `0 1 * * *`（UTC）。
- 月报每月最后一天 09:00 自动运行（cron `0 1 28-31 * *`，程序内判断是否月末）。
