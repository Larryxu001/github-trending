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
