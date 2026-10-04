# GitHub Trending 每日分析推送 — 运行说明

> **当前主流程已迁移到 GitHub Actions**（仓库 `Larryxu001/github-trending`），
> 每天 09:00（北京时间）由 GitHub 服务器自动运行，**不再消耗 WorkBuddy 积分**。

## 一、线上自动运行（GitHub Actions，主流程）

- **触发**：每天 09:00（`cron: 0 1 * * *` UTC），也可在仓库 Actions 页手动 Run workflow。
- **入口**：`.github/workflows/daily.yml` → `python run_daily.py`
- **流程**：抓榜 → 去重 → 复用/自动生成描述 → 渲染 → 推送飞书 → 归档 → 提交回仓库
- **密钥**：飞书 webhook 存 `FEISHU_WEBHOOK` secret，经环境变量注入；token 用 `${{ github.token }}`
- **归档**：`reports/`（Markdown）、`reports_web/`（网页版）、`data/`（JSON）、`archive/`（当月）

## 二、本地手动运行（开发/调试用）

```
PY=/Users/larryxu/.workbuddy/binaries/python/versions/3.13.12/bin/python3
cd ~/.workbuddy/github-trending-bot
cp config.local.json config.json   # 本地填真实 webhook/token
$PY run_daily.py
```

或两段式（可中途人工介入写描述）：
```
$PY pipeline.sh prepare    # 抓榜 + 去重 + 骨架
# （可选）人工编辑 new_desc.json
$PY pipeline.sh finalize   # 合并 + 渲染 + 推送 + 归档
```

## 三、脚本职责

| 脚本 | 作用 |
|---|---|
| `run_daily.py` | Actions 每日流水线入口（无 LLM 依赖） |
| `pipeline.sh` | 本地两段式流水线（prepare / finalize） |
| `fetch_trending.py` | 抓日/周/月三榜 + API 补全 + 30 天去重 → items.json |
| `prepare_report.py` | 骨架 + 描述复用 → report.json / pending.json |
| `desc_auto.py` | 自动生成中文描述（内置表 + 启发式模板） |
| `apply_desc.py` | 合并描述 → report.json + desc_cache.json |
| `render_html.py` / `render_md.py` | report.json → 网页版 / Markdown |
| `push.py` | 推送飞书（交互式卡片，官网可点击） |
| `build_monthly.py` | 月报构建（合并当月归档） |

## 四、状态文件

| 文件 | 作用 |
|---|---|
| `pushed.json` | 去重唯一依据（30 天窗口，自动清理过期） |
| `desc_cache.json` | 描述唯一依据（复用即零成本） |
| `config.json` | 仓库内无密钥模板；本地密钥放 config.local.json（gitignored） |

## 五、硬规则

1. 30 天内已推送的项目**绝不重复推送**。
2. `desc_cache.json` 里已有描述的项目**绝不重写**。
3. 推送失败时**绝不**写 pushed.json、绝不归档。
4. 报告一律中文，星数千分位，官网缺失统一写「无」。
5. **密钥绝不入库**：webhook/token 只走环境变量或 config.local.json。

## 六、收藏功能维护（CF Worker + saved.json）

- **真源**：仓库根 `saved.json`（Worker 经 GitHub API 实时读写，无 CDN 缓存延迟）。
- **Worker 目录**：`~/.workbuddy/github-trending-save-worker/`（worker.js + wrangler.toml）。
- **部署命令**（wrangler 不在 PATH，npx 直跑会被 SIGTERM，必须用 npx 缓存里的完整路径）：
  ```
  cd ~/.workbuddy/github-trending-save-worker
  ~/.npm/_npx/32026684e21afda6/node_modules/.bin/wrangler deploy
  ```
- **改前端收藏 JS 后必须**：重新 `render_html.py` / `render_saved.py`，并把
  `site/index.html` 同步到 `reports_web/<年>/<日期>/index.html`、`site/saved.html`
  同步到 `reports_web/saved.html`，再 commit push（Pages 自动部署）。
- **线上自检命令**：
  ```
  curl -s https://github-trending-save.larryxu-4e5.workers.dev          # GET 应返回 {ok:true,items:[...]}
  curl -s https://larryxu001.github.io/github-trending/saved.html | grep -c "程序错误"  # ≥1 说明新版已部署
  ```
- **周报**：`weekly.yml` 每周一 09:00 北京时间跑 `sync_saved.py`，只推近 7 天
  （按 `saved_at`，北京时间口径，与 Worker 写入口径一致）。
- **已知坑**：前端 catch 里把 JS 异常报成「网络错误」会严重误导排查；错误提示必须
  带 `err.message` 并区分网络/程序错误（已实现）。


