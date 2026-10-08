# 飞书群添加 GitHub 精选

当前日报使用自定义机器人 webhook，只能发消息。接收群消息需创建一个飞书自建应用机器人；原推送机器人继续发送日报及导入结果。

## 应用配置

1. 在飞书开放平台创建企业自建应用，启用机器人能力并加入当前日报群。
2. 申请接收群内 @机器人 消息权限 `im:message.group_at_msg:readonly`，订阅「接收消息」`im.message.receive_v1`。已选择只接收 @消息：请在群里 **@新机器人 + GitHub 项目首页链接**。仅开通 `im:message.group_at_msg:readonly`，不申请全部群消息或机器人消息读取权限。后端同时拒绝没有 @信息的消息。
3. 事件接收方式选择开发者服务器，URL：`https://github-trending.51vipai.com/feishu/events`。本实现使用 HTTPS 明文事件；不要启用 Encrypt Key 加密。先配置 Worker Verification Token，再完成 URL challenge 验证。
4. 在 Cloudflare Worker 设置 `FEISHU_VERIFICATION_TOKEN`（密钥，不写入 GitHub），以及 `FEISHU_IMPORT_CHAT_ID`（该群 chat_id）、`FEISHU_IMPORT_USER_ID`（你的 open_id，必须属于此自建应用）。这三项不能用推送 webhook 中的字段代替。
5. 发布应用版本并完成权限审批，确认机器人已在原群。只有配置的用户在配置的群发出的文本/富文本消息可触发导入，每条最多 5 个公开 GitHub 项目首页链接。

不需要更改 SAVE_KEY、现有推送 webhook 或 GitHub DeepSeek 密钥。不得把应用 Secret、Verification Token 发到群或聊天中。

## 使用与验收

- 网页：在「我的精选」粘贴 `https://github.com/owner/repo`，点击「AI 分析并加入」，等待真实任务完成并出现项目。
- 飞书：@接收机器人发送同一项目链接，后台任务完成后，现有推送机器人会反馈「已加入精选」及中文介绍，或提示项目已存在；失败会提示查看 Actions 后重试。
- 两个入口共用 `import.yml`，使用与报表相同的排队锁。重复事件可能触发重复任务，但任务会先检查精选库，不重复添加或覆盖已有备注。已经成功收录的重复项目不会重复调用 AI。
- 如通知发送失败，项目可能已写入；以精选库和 Actions 步骤为准，重试不会重复收录。GitHub 排队或 DeepSeek 服务缓慢时可能需要数分钟；网页关闭后任务继续执行。
- 分析使用 GitHub 介绍和最多 12,000 字符 README，没有执行仓库代码，AI 生成的介绍仍可能需要人工核对。

官方参考：[消息接收事件](https://open.feishu.cn/document/server-docs/im-v1/message/events/receive)、[事件订阅](https://open.feishu.cn/document/server-docs/event-subscription-guide/event-subscription-configure-/request-url-configuration-case)。
