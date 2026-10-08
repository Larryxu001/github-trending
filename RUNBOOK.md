# GitHub Trending 运行与恢复

## 调度与层次

全部使用北京时间。每 3 小时采集三榜，不发消息、不调用 AI。
每天 09:00 发一轮日报；每周一 09:00 发一轮精选周报；月末 09:00 发一轮精选月报。每轮是一张封面和按分类配色的独立卡片，恢复原有信息流。
周报只取上一个完整星期新增、仍在 `saved.json` 中的精选；月报取最近 4 期已经发送的周报快照，按 repo 去重。
没有新项目时仍发一条明确的空期消息，避免无法区分“没项目”和“任务失败”。
新规则从部署后开始积累周报；启动不足 4 期会注明实际期数。历史日报不用于凑数。

## 一次发送的保护

唯一周期工作流是 collect.yml，每次采集后按日期运行到期日报、周报、月报，避免同一时间多个定时任务相互挤掉。日/周/月工作流保留手动入口；收藏 Worker 每 3 小时触发采集与到期报告，作为调度兜底。
09:00 前只采集；09:00 后如果本期报告已经成功发送则跳过。准备或部署失败可在之后的采集周期恢复；不确定的发送仍禁止自动重发。

所有采集/报告/keepalive 工作流共享 `trending-state` 并发组，不取消正在发送的任务。
工作流拿到锁之后重新拉取 main，读取最新状态。Worker 的额外 workflow_dispatch 也受同一守卫约束。
每期流程：生成完整报告并归档 → 提交 prepared → Pages 部署与公开内容验收成功 → 为每张卡片提交 sending → 飞书明确回执 → 提交该卡片 sent → 全部完成后提交报告 sent。
消息超过大小/元素限额时拆分分类卡片，不删除介绍。明确拒收可重试未发送卡片，已经收到的封面/分类不再重复。
日报 sent 后更新 `pushed.json` 与 `last_push.json`；已有历史 `last_push.json` 标记继续生效。
日报同时避开最近 30 天处于 sent/sending/unknown 的报告项目，防止发送后回执提交失败造成次日重复。

飞书 webhook 没有本项目可用的服务端幂等键。网络超时可能发生在消息已被接收之后，所以不能保证“绝不重复”和“任何故障都自动补发”同时成立。本项目优先避免重复：不自动重试不确定的发送。

## 故障恢复

- 抓榜有一榜失败/解析为空：任务失败，保留上次采集数据；下一次采集再试。
- 缺描述、状态 JSON 损坏：任务失败，不假装为空报告继续发送。
- prepared：还未尝试发送，可以手动重跑同一工作流；复用已生成的报告，不重新消耗 AI token。
- sending/unknown：可能已经发到飞书，工作流会报错并停止重发。先检查对应日期的飞书消息；逐张核对 `cards`：确认收到的卡片改为 sent，确认未收到的改为 pending；报告改为 prepared，提交后重跑，只发送剩余卡片。不要把未完成整期直接标为 sent。
- sent：重复触发直接跳过。
- Pages 失败：不发消息，修复部署后重跑。
- 飞书 secret 缺失/回执不是明确成功：任务失败，检查 Actions 日志和对应消息；按 sending/unknown 处理。

`deliveries.json` 是持久化发送状态和冻结报告，勿随意删除。不要直接运行历史 `push.py` 或旧两阶段流水线绕过去重。

## 配置与外部依赖

`FEISHU_WEBHOOK` 和 `DEEPSEEK_API_KEY` 放 GitHub Secrets；不要把真实凭证写入 `config.json`。
收藏 Worker 真源是 `workers/save/`，生产部署仍为原 Worker。SAVE_KEY 同时用于页面入口验证与写入口鉴权，GH_PAT 保持原凭证。损坏数据绝不当成空列表覆盖；saved.json 不做迁移。
本机密码在 `.local/save-password.txt`（仅本机、不入库）；页面首次访问时输入，日报、归档与精选页共用会话，收藏/取消无需另输密码。以前生成的网页已同步更新鉴权与 URL 校验。
Worker 每 3 小时额外触发 collect.yml（mode=scheduled），但不能绕过 daily.yml 的并发锁、9 点前守卫和每期发送状态。
GitHub schedule 可能延迟。health.yml 在失败及每天 11:20 检查采集/日报/未完成报告/Worker/PAT，health_state.json 去重通知；超时的提醒也不会自动重发。Cloudflare 11:20 独立触发健康检查，GitHub 无法触发时走独立飞书故障提醒。
Webhook 失效时飞书自身无法收到提醒，Actions/Worker 日志仍明确报错；不要将此情况视为正常。

验证命令：`python3 -m unittest discover -s tests -v`。

Worker 检查：`node --test workers/save/worker.test.mjs`；部署说明见 `workers/save/README.md`。

收藏提速：页面 GET 仍读 GitHub 最新数据，同时缓存带 SHA 的快照 10 分钟。POST 优先复用快照，命中时只执行一次 GitHub 写入；SHA 冲突时重新读最新数据合并。缓存失效或不可用退回原流程，成功必须得到 GitHub 写入回执。Worker 日志 favorite_write 记录 snapshot_hit、attempts 与 duration_ms，不记录密码或备注。

页面入口只需要访问密码，无账号。同一标签页会话内自动验证，关闭后下次需重新输入。Pages 与仓库仍公开；入口不等同于私密托管，源代码及历史静态内容不具备保密性。密码由 Worker 验证，不写入 HTML。
