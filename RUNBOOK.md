# GitHub Trending 每日分析推送 — 标准作业流程（SOP）

所有文件在 `~/.workbuddy/github-trending-bot/`。定时任务的职责只有 3 件事：
跑两个脚本命令、给新项目写描述、更新线上站点。其余全部由脚本保证，不要手工干预。

```
PY=/Users/larryxu/.workbuddy/binaries/python/versions/3.13.12/bin/python3
BASE=/Users/larryxu/.workbuddy/github-trending-bot
```

---

## A. 日报（每天 09:00）

### 步骤 1 — 抓榜 + 去重 + 生成骨架
```
$BASE/pipeline.sh prepare
```
内部执行：`fetch_trending.py`（抓日/周/月三榜 → GitHub API 补全信息 → 按 `pushed.json`
做 30 天去重 → 只把新项目写进 `items.json`），然后 `prepare_report.py`
（命中 `desc_cache.json` 的项目直接复用描述，未命中的写进 `pending.json`）。
输出最后一行是 pending 数量。

### 步骤 2 — 给「新」项目写中文描述（唯一的模型工作量）
- pending 数为 0 → **直接跳到步骤 3**，不要写任何东西。
- 否则读 `pending.json`（每项含 owner / stars / updated / homepage / language / topics / 英文简介），
  为每个项目写：
  - `cat` 分类名 + `emoji`（单个）：优先复用已有分类
    （Agent 技能与插件 🧩、Agent 基础设施与框架 🤖、Agent 效率优化 ⚡、AI / 大模型 🧠、
    AI 应用与内容生成 🎨、开发工具与框架 🛠、数据 / 数据库 💾、移动 / 桌面应用 📱、
    安全 🔐、学习资源 📚、区块链 ⛓、其他 📦）
  - `desc`：通俗易懂的一段话（1-3 句），说清它做什么、解决什么问题，必要时举例。
    不要照抄英文简介，不要写「无 / 暂无」占位。
  - `site`：官网 URL，没有写「无」
- 用 Write 存为 `new_desc.json`，**只含本次新项目**（已缓存的绝不能再写一遍）：
  ```json
  {"owner/repo": {"cat": "开发工具与框架", "emoji": "🛠", "desc": "……", "site": "https://…"}}
  ```
- 单个仓库信息不足时，最多额外 WebFetch 10 次 GitHub 页面补充。

### 步骤 3 — 收尾
```
$BASE/pipeline.sh finalize
```
内部依次执行（任何一步失败立即中止，且**不会**写 pushed.json / 不会归档）：
1. `apply_desc.py`：合并描述进 report.json（分类归位 + 组内星数降序）+ 回填 `desc_cache.json`
2. 完整性校验：所有项目必须有 desc
3. `render_html.py` + `render_md.py`：生成 `site/index.html` 和 `report-<date>.md`
4. `push.py`：推送飞书（交互式卡片），消息里自动带网页版链接；官网以可点击的超链接展示完整网址
5. 归档 `archive/report-<date>.json`，更新 `pushed.json`（并清理 30 天前记录）
6. `sync_github.py`：把日报 Markdown + JSON 提交到 GitHub 仓库 `Larryxu001/github-trending`，
   并自动重建 README 索引
7. 清空 `new_desc.json`

### 步骤 4 — 更新线上站点（保持同一链接）
用 `workbuddy_sites_deploy` 工具发布 `directory = $BASE/site`（language `static`），
会覆盖到同一个应用、链接不变：**https://github-trending-daily-11993.app.workbuddy.host/**
若工具返回需要确认，不要强行重试，跳过并在汇报里说明（站点仍显示上一期）。

### 步骤 5 — 汇报
一句话说明：新项目数 / 其中复用缓存多少 / 跳过多少 / 线上是否更新。

> 推送渠道：**仅飞书**（企业微信已按用户要求移除）。

---

## B. 月报（每月最后一天 09:00）

0. **先判断是否当月最后一天**，不是就立即结束（不推送、不产生任何文件）。
1. `$PY $BASE/build_monthly.py` → 合并 `archive/report-*.json`，去重汇总当月全部项目，
   用 token 刷新星数，产出 `monthly-YYYY-MM.json`。
2. **沿用归档里已有的中文描述**，只对明显写得差的做优化，最多 10 个。
3. `$PY $BASE/render_html.py monthly-YYYY-MM.json`、`$PY $BASE/render_md.py monthly-YYYY-MM.json`
   （date 为 YYYY-MM 时自动切换「Github开源趋势月报」刊头与 VOL.Mxx 编号）。
4. `$PY $BASE/push.py monthly-YYYY-MM.json`（标题自动为「GitHub Trending 月报」，仅推送飞书）。
5. `$PY $BASE/sync_github.py monthly-YYYY-MM.json`（写入仓库 `monthly/` 与 `data/`）。
6. 更新线上站点（同步骤 4）。
7. **月报不写 pushed.json**，不影响日报的 30 天去重。

---

## C. 状态文件

| 文件 | 作用 |
|---|---|
| `pushed.json` | 去重唯一依据：`repo -> 首次推送日期`，30 天窗口外的自动清理 |
| `desc_cache.json` | 描述唯一依据：`repo -> {cat, emoji, desc, site}`，复用即零消耗 |
| `items.json` | 当日新增原始条目（含 stars / updated / homepage / topics） |
| `pending.json` | 本次需要写描述的新项目 |
| `report.json` | 当期结构化报告（push / render 的输入） |
| `archive/report-*.json` | 月报数据源 |
| `site/index.html` | 每日渲染的网页版（部署目标） |
| `repo/` | GitHub 仓库本地克隆（sync_github.py 维护） |

## D. 硬规则

1. 30 天内已推送的项目**绝不重复推送**。
2. `desc_cache.json` 里已有描述的项目**绝不重写**，只刷新星数 / 更新日期。
3. 推送失败时**绝不**写 `pushed.json`、绝不归档。
4. 报告一律中文，星数用千分位（12,345），官网缺失统一写「无」。
5. 全部脚本用绝对路径 + 托管 Python 运行，不依赖本机 python 环境。
