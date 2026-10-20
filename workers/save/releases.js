const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function page(repo, content, status = 200) {
  return new Response(`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escape(repo)} · 最新 Release</title><style>body{margin:0;background:#FBF7EC;color:#2B2419;font-family:-apple-system,"PingFang SC",sans-serif}main{max-width:760px;margin:auto;padding:48px 24px}h1{font-family:Georgia,"Songti SC",serif;overflow-wrap:anywhere}a{color:#C02B1F}li{padding:16px 0;border-bottom:1px dashed #E6DDC6;overflow-wrap:anywhere}ul{list-style:none;padding:0}p,small{color:#7A7263;line-height:1.8}</style><main><a href="/">← 往期归档</a><h1>${escape(repo)}</h1>${content}<p><a href="/download/${escape(repo)}.zip">下载默认分支源码 ZIP</a></p></main></html>`, {status, headers:{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'"}});
}

export async function releaseDownload(request) {
  const url = new URL(request.url);
  const match = url.pathname.match(/^\/release\/([A-Za-z0-9_-]+)\/([A-Za-z0-9_.-]+)\/?$/);
  if (!match || ['.', '..'].includes(match[2])) return new Response('Invalid repository', {status:400});
  if (!['GET', 'HEAD'].includes(request.method)) return new Response('Method not allowed', {status:405,headers:{Allow:'GET, HEAD'}});
  const repo = `${match[1]}/${match[2]}`;
  try {
    // Public metadata only. Never forward browser credentials or the private repository token.
    const metadata = await fetch(`https://api.github.com/repos/${repo}/releases/latest`, {
      headers:{Accept:'application/vnd.github+json','User-Agent':'github-trending-release'},
      signal:AbortSignal.timeout(20000), cf:{cacheTtl:300,cacheEverything:true}
    });
    if (metadata.status === 404) return page(repo, '<p>该项目暂无正式 Release，或仓库已不可用。仍可尝试下载默认分支源码。</p>', 404);
    if (!metadata.ok) return page(repo, '<p>暂时无法读取最新版本，请稍后重试。</p>', 503);
    const release = await metadata.json();
    const assets = Array.isArray(release.assets) ? release.assets : [];
    if (url.searchParams.get('source') === '1') {
      if (typeof release.tag_name !== 'string' || !release.tag_name) return page(repo, '<p>版本标签无效。</p>', 502);
      const response = await fetch(`https://codeload.github.com/${repo}/zip/refs/tags/${encodeURIComponent(release.tag_name)}`, {method:request.method,redirect:'manual',signal:AbortSignal.timeout(120000)});
      if (!response.ok) return page(repo, '<p>版本源码暂时无法下载，请稍后重试。</p>', 502);
      return new Response(response.body, {headers:{'Content-Type':'application/zip','Content-Disposition':`attachment; filename="${match[2]}-release-source.zip"`,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
    }
    const assetId = url.searchParams.get('asset');
    if (assetId !== null) {
      const asset = assets.find(a => String(a.id) === assetId);
      if (!asset) return page(repo, '<p>该附件已不存在于最新版本，请重新打开最新 Release 页面。</p>', 404);
      const target = new URL(asset.browser_download_url);
      if (target.origin !== 'https://github.com' || !target.pathname.startsWith(`/${repo}/releases/download/`)) return page(repo, '<p>下载地址无效。</p>', 502);
      const response = await fetch(target.href, {method:request.method,redirect:'follow',signal:AbortSignal.timeout(120000)});
      if (!response.ok) return page(repo, '<p>附件暂时无法下载，请稍后重试。</p>', 502);
      const headers = new Headers({'Content-Type':'application/octet-stream','Content-Disposition':`attachment; filename="release-asset"; filename*=UTF-8''${encodeURIComponent(asset.name).replace(/'/g, '%27')}`,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});
      if (response.headers.has('Content-Length')) headers.set('Content-Length', response.headers.get('Content-Length'));
      return new Response(response.body, {headers});
    }
    const links = assets.map(a => `<li><a href="/release/${escape(repo)}?asset=${encodeURIComponent(a.id)}">${escape(a.name)}</a><br><small>${(Number(a.size) / 1048576).toFixed(2)} MB</small></li>`).join('');
    return page(repo, `<h2>最新正式版 ${escape(release.tag_name)}</h2><p>发布于 ${escape((release.published_at || '').slice(0,10))} · 版本信息最多缓存 5 分钟</p><p>请选择适合你系统的附件，文件通过本站下载。</p>${links ? `<ul>${links}</ul>` : '<p>此版本未上传安装包或其他附件，可下载本版本源码。</p>'}<p><a href="/release/${escape(repo)}?source=1">下载本版本源码 ZIP</a></p>`);
  } catch (_) {
    return page(repo, '<p>获取版本或下载超时，请稍后重试。</p>', 502);
  }
}
