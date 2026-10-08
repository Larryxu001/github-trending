# 收藏服务（现有 github-trending-save Worker）

本目录是生产 Worker 的源码真源，取代 WorkBuddy 目录内的独立副本。
保持原 Worker 名称、账号和 GH_PAT；不迁移或重建 saved.json。

- GET：读取公开收藏（仓库本身公开）。
- POST：必须携带 `Authorization: Bearer <收藏密码>`；拒绝其他网站 Origin。
- `/health`：检查 GitHub 凭证、收藏数据和安全/提醒密钥配置。
- 缺文件、损坏 JSON、非法字段和执行型 URL 均停止写入；并发冲突重读后再尝试。
- 09:00 触发日报兜底；11:20 触发健康检查。GitHub 触发失败时通过独立 FEISHU_WEBHOOK 提醒。

密钥：GH_PAT（沿用）、SAVE_KEY、FEISHU_WEBHOOK。不要写入源码或聊天。
部署保留现有变量，使用 Wrangler 4.125.0（本次已验证）。

```bash
node --test workers/save/worker.test.mjs
wrangler deploy --config workers/save/wrangler.toml --dry-run
wrangler deploy --config workers/save/wrangler.toml --keep-vars --secrets-file .local/worker-secrets.json
```

本机收藏密码保存在仓库 `.local/save-password.txt`，目录不入 Git。
网页首次写入时输入密码，当前浏览会话内保留；输入错误后清除缓存。
Workers Logs 与 Traces 已开启。网络/接口错误可在日志中定位，日志不记录凭证或收藏备注。


主动导入接口：`POST /imports`（现有密码鉴权，`{"url":"https://github.com/owner/repo"}`），返回 `202` 和任务 ID；`GET /imports/<id>` 查询 Actions 状态。分析复用 GitHub Secrets，不向 Worker 复制 AI 密钥。`POST /feishu/events` 为飞书事件接收入口，仅接收配置的群与用户，验证 Verification Token，支持 HTTPS 明文事件。部署时保留现有 Secrets。

新增飞书配置：`FEISHU_VERIFICATION_TOKEN`（Secret）、`FEISHU_IMPORT_CHAT_ID`、`FEISHU_IMPORT_USER_ID`；未配置时关闭飞书接收入口，不影响网页入口、采集或推送。详见 `docs/feishu-import.md`。
