# 自定义访问入口

- 网页：https://github.51vipai.com
- 精选：https://github.51vipai.com/saved.html
- 密码与原入口共用；新域名首次访问需要重新输入密码。
- Cloudflare Worker 从仓库 reports_web 读取页面，浏览器只通过新域名加载页面和 /api 接口。站内绝对链接也会改写为新域名。
- GitHub Pages 保留；新入口自动跟随 reports_web 更新，无需另外部署静态文件。
- 项目仓库链接仍指向 github.com，公司网络可能无法打开仓库本身。
- 项目集成面板：https://project.xulangli.com.cn

部署使用 workers/save/wrangler.toml；执行 wrangler deploy --keep-vars，保留已有密码和密钥配置。

## 源码包下载

每个报告项目和精选项目提供「下载源码 ZIP」。固定地址格式：
`https://github.51vipai.com/download/OWNER/REPO.zip`

Cloudflare 从公开仓库的默认分支获取最新源码并流式返回，不向客户端重定向到 GitHub，也不向下载上游发送密码或 GitHub PAT。无需预先保存每个 ZIP；仓库后续更新会反映在新的下载中。私有、已删除或不可用项目返回错误。

这是源码快照，不是 Release 安装包；不含 Git 历史、额外依赖或子模块内容，安装依赖仍取决于公司网络。下载不会调用 AI 或消耗模型 token。未做永久归档，不能作为项目删除后的备份。
