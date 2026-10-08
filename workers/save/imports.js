// Both entrances enqueue the same durable GitHub Actions job; AI secrets stay in Actions.
export function parseRepository(value) {
  let url;
  try { url = new URL(value.trim()); } catch (_) { throw new Error('请输入 GitHub 项目首页链接'); }
  const parts = url.pathname.replace(/^\/+|\/+$/g, '').split('/');
  if (url.protocol !== 'https:' || url.host.toLowerCase() !== 'github.com' || url.username || url.password || parts.length !== 2) {
    throw new Error('请输入 https://github.com/owner/repo 格式的项目首页链接');
  }
  const repo = parts.join('/').replace(/\.git$/, '');
  if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repo)) throw new Error('GitHub 项目链接不合法');
  return 'https://github.com/' + repo;
}

async function bodyJSON(request) {
  const reader = request.body?.getReader();
  if (!reader) throw new Error('请求体为空');
  const chunks = []; let size = 0;
  while (true) {
    const {done, value} = await reader.read();
    if (done) break;
    size += value.length;
    if (size > 20000) { await reader.cancel(); throw new Error('请求过大'); }
    chunks.push(value);
  }
  const bytes = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  return JSON.parse(new TextDecoder().decode(bytes));
}

async function github(env, path, body) {
  const response = await fetch(`https://api.github.com/repos/${env.GH_REPO || 'Larryxu001/github-trending'}/actions/${path}`, {
    method: body ? 'POST' : 'GET', signal: AbortSignal.timeout(2500),
    headers: {Authorization: `Bearer ${env.GH_PAT}`, Accept:'application/vnd.github+json',
      'User-Agent':'github-trending-import', 'Content-Type':'application/json'},
    ...(body ? {body:JSON.stringify(body)} : {})
  });
  if (!response.ok) throw new Error(`GitHub 请求失败 HTTP ${response.status}`);
  return response;
}

async function dispatch(env, urls, id, source) {
  await github(env, 'workflows/import.yml/dispatches', {
    ref:env.GH_BRANCH || 'main', inputs:{urls:JSON.stringify(urls), request_id:id, source}
  });
}

export async function handleImport(request, env, authorized, json) {
  const path = new URL(request.url).pathname;
  const feishu = path === '/feishu/events';
  if (!feishu && path !== '/imports' && !path.startsWith('/imports/')) return null;
  if (!env.GH_PAT) return json({error:'GitHub 服务未配置'},503);
  if (!feishu) {
    if (!env.SAVE_KEY) return json({error:'访问密码未配置'},503);
    if (!await authorized(request, env.SAVE_KEY)) return json({error:'访问密码不正确'},401);
  }
  try {
    if (feishu) {
      if (request.method !== 'POST') return json({error:'仅支持 POST'},405);
      if (!env.FEISHU_VERIFICATION_TOKEN) return json({error:'飞书接收功能尚未配置'},503);
      const body = await bodyJSON(request);
      if (body.encrypt) return json({error:'此入口使用 HTTPS 明文事件，请关闭事件加密或先配置解密支持'},400);
      const token = body.header?.token || body.token || '';
      const tokenRequest = new Request(request.url,{headers:{Authorization:'Bearer '+token}});
      if (!await authorized(tokenRequest, env.FEISHU_VERIFICATION_TOKEN)) return json({error:'事件验证失败'},401);
      if (body.type === 'url_verification' && typeof body.challenge === 'string') return json({challenge:body.challenge});
      if (body.header?.event_type !== 'im.message.receive_v1') return json({ok:true});
      if (!env.FEISHU_IMPORT_CHAT_ID || !env.FEISHU_IMPORT_USER_ID) return json({error:'请配置允许导入的群和用户'},503);
      const message = body.event?.message, sender = body.event?.sender;
      if (message?.chat_id !== env.FEISHU_IMPORT_CHAT_ID || sender?.sender_id?.open_id !== env.FEISHU_IMPORT_USER_ID || sender?.sender_type !== 'user') return json({ok:true});
      // Require an explicit mention as well as the platform's @message permission.
      if (message.chat_type !== 'group' || !Array.isArray(message.mentions) || !message.mentions.length) return json({ok:true});
      // Accept text and rich-text posts only; bot cards and old/replayed events never import.
      if (!['text','post'].includes(message.message_type)) return json({ok:true});
      const age = Date.now() - Number(message.create_time);
      if (!Number.isFinite(age) || age < -60000 || age > 300000) return json({ok:true});
      const id = body.header?.event_id;
      if (typeof id !== 'string' || !/^[A-Za-z0-9_-]{1,100}$/.test(id)) return json({error:'事件 ID 不合法'},400);
      const candidates = String(message.content).match(/https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+(?:\/[^\s"<>]*)?/gi) || [];
      const urls = [];
      for (const candidate of candidates) {
        try { const url = parseRepository(candidate); if (!urls.includes(url)) urls.push(url); } catch (_) { /* skip non-repository links */ }
      }
      if (!urls.length) return json({ok:true});
      if (urls.length > 5) return json({error:'每条消息最多 5 个项目，请分开发送'},400);
      await dispatch(env, urls, id, 'feishu');
      return json({ok:true});
    }
    if (path === '/imports' && request.method === 'POST') {
      const body = await bodyJSON(request);
      if (typeof body.url !== 'string') return json({error:'请输入 GitHub 项目链接'},400);
      const url = parseRepository(body.url), id = crypto.randomUUID();
      await dispatch(env, [url], id, 'pages');
      return json({ok:true,id},202);
    }
    if (path.startsWith('/imports/') && request.method === 'GET') {
      const id = path.slice('/imports/'.length);
      if (!/^[A-Za-z0-9_-]{1,100}$/.test(id)) return json({error:'请求 ID 不合法'},400);
      const response = await github(env, 'workflows/import.yml/runs?event=workflow_dispatch&per_page=100');
      const data = await response.json();
      const run = data.workflow_runs?.find(run => run.display_title === 'import-' + id);
      return json({ok:true,status:run?.status || 'queued',conclusion:run?.conclusion || null,
        url:run?.html_url || `https://github.com/${env.GH_REPO || 'Larryxu001/github-trending'}/actions/workflows/import.yml`});
    }
    return json({error:'请求方法不支持'},405);
  } catch (error) {
    console.error(JSON.stringify({event:'import_request_failure', type:error.name}));
    return json({error: error.name === 'TimeoutError' ? 'GitHub 响应超时，任务可能已提交，请查看 Actions 后再重试' : error.message},
      /GitHub|超时/.test(error.message) || error.name === 'TimeoutError' ? 502 : 400);
  }
}
