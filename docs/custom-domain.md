# 自定义访问入口

- 网页：https://github.51vipai.com
- 精选：https://github.51vipai.com/saved.html
- 密码与原入口共用；新域名首次访问需要重新输入密码。
- Cloudflare Worker 从仓库 reports_web 读取页面，浏览器只通过新域名加载页面和 /api 接口。站内绝对链接也会改写为新域名。
- GitHub Pages 保留；新入口自动跟随 reports_web 更新，无需另外部署静态文件。
- 项目仓库链接仍指向 github.com，公司网络可能无法打开仓库本身。
- 项目集成面板：https://project.xulangli.com.cn

部署使用 workers/save/wrangler.toml；执行 wrangler deploy --keep-vars，保留已有密码和密钥配置。
