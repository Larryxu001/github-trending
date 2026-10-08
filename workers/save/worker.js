/**
 * GitHub Trending 收藏 Worker
 *
 * 接收网页「收藏」请求，把项目写入 GitHub 仓库的 saved.json（收藏真源）。
 * 通过 GitHub PAT 调用 API，PAT 存在 Worker secrets 里，不进浏览器。
 *
 * 环境变量（secrets）：
 *   GH_PAT  — 有 repo 写权限的 Personal Access Token
 *   GH_REPO — 仓库 "owner/repo"（如 "Larryxu001/github-trending"）
 *   GH_BRANCH — 分支，默认 "main"
 *
 * 请求：POST，body 为项目 meta JSON：
 *   { repo, url, owner, stars, category, emoji, desc, site, note, tags:[] }
 *   取消收藏时传 { repo, _remove:true }
 * 响应：{ ok:true, removed:boolean } 或 { error:"..." }
 */

const DEFAULT_REPO = "Larryxu001/github-trending";
const SAVED_PATH = "saved.json";

async function authorized(request, key) {
  const supplied = (request.headers.get("Authorization") || "").replace(/^Bearer /, "");
  const digest = async value => new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value)));
  const a = await digest(supplied), b = await digest(key);
  let difference = 0;
  for (let i = 0; i < a.length; i++) difference |= a[i] ^ b[i];
  return difference === 0;
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "https://larryxu001.github.io",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
    },
  });
}

async function fetchSaved(repo, branch, token) {
  // 用 GitHub Contents API 读（带 sha，无 raw CDN 缓存延迟）
  const url = `https://api.github.com/repos/${repo}/contents/${SAVED_PATH}?ref=${branch}`;
  const resp = await fetch(url, {
    signal: AbortSignal.timeout(20000),
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "github-trending-save-worker",
    },
  });
  if (resp.status === 404) throw new Error("saved.json missing; refusing to replace existing data");
  if (!resp.ok) {
    throw new Error(`读取 saved.json 失败: HTTP ${resp.status}`);
  }
  const data = await resp.json();
  const sha = data.sha;
  let items;
  try {
    // base64 -> 字节 -> UTF-8 解码（GitHub 返回 UTF-8 内容，不能用 atob 直接转字符串，否则中文乱码）
    const bin = atob(data.content.replace(/\n/g, ""));
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const body = new TextDecoder("utf-8").decode(bytes);
    items = JSON.parse(body).items;
    if (!Array.isArray(items)) throw new Error("invalid items");
  } catch (_) { throw new Error("saved.json is corrupt; refusing to overwrite"); }
  return { items, sha };
}

async function writeSaved(repo, branch, token, items, sha) {
  const url = `https://api.github.com/repos/${repo}/contents/${SAVED_PATH}`;
  const content = btoa(unescape(encodeURIComponent(JSON.stringify({ items }, null, 1))));
  const body = {
    message: "收藏更新 · 自动",
    content,
    branch,
  };
  if (sha) body.sha = sha;

  const resp = await fetch(url, {
    signal: AbortSignal.timeout(20000),
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "Content-Type": "application/json",
      "User-Agent": "github-trending-save-worker",
    },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(`写入失败: HTTP ${resp.status} ${err.message || ""}`);
  }
  return resp.json();
}

export default {
  // Cloudflare Cron 定时触发：每天调 GitHub workflow_dispatch 触发日报 pipeline，
  // 作为 GitHub 自身 schedule（best-effort、可能延迟）的免费兜底。
  async scheduled(event, env, ctx) {
    const health = event.cron === "20 3 * * *";
    const workflow = health ? "health.yml" : "collect.yml";
    try {
      if (!env.GH_PAT) throw new Error("GH_PAT is missing");
      const resp = await fetch(`https://api.github.com/repos/${env.GH_REPO || DEFAULT_REPO}/actions/workflows/${workflow}/dispatches`, {
        method: "POST", signal: AbortSignal.timeout(20000),
        headers: {Authorization: `Bearer ${env.GH_PAT}`, "Content-Type": "application/json", "User-Agent": "github-trending-save-worker"},
        body: JSON.stringify({ref: env.GH_BRANCH || "main", ...(health ? {} : {inputs:{mode:"scheduled"}})}),
      });
      if (!resp.ok) throw new Error(`GitHub dispatch HTTP ${resp.status}`);
      console.log(JSON.stringify({event:"cron_dispatch", workflow, status:resp.status}));
    } catch(error) {
      console.error(JSON.stringify({event:"cron_failure", workflow, error:error.message}));
      // Independent daily fallback when GitHub credentials/schedules cannot trigger monitoring.
      if (health && env.FEISHU_WEBHOOK) {
        const resp = await fetch(env.FEISHU_WEBHOOK, {method:"POST", signal:AbortSignal.timeout(20000),
          headers:{"Content-Type":"application/json"}, body:JSON.stringify({msg_type:"text",text:{content:`GitHub Trending 自动化故障：${error.message}。请检查 Worker GH_PAT、GitHub Actions 与 health.yml。`}})});
        const result = await resp.json();
        if (!resp.ok || (result.code ?? result.StatusCode) !== 0) throw new Error("Failure alert was not confirmed");
      }
      throw error;
    }
  },

  async fetch(request, env) {
    // CORS 预检
    if (request.method === "OPTIONS") {
      return json({ ok: true });
    }

    const origin = request.headers.get("Origin");
    if (origin && origin !== "https://larryxu001.github.io") return json({error:"Origin forbidden"},403);
    if (new URL(request.url).pathname === "/auth") {
      if (request.method !== "GET") return json({error:"仅支持 GET"},405);
      if (!env.SAVE_KEY) return json({error:"访问密码未配置"},503);
      const valid = await authorized(request, env.SAVE_KEY);
      return json(valid ? {ok:true} : {error:"密码不正确"}, valid ? 200 : 401);
    }
    const token = env.GH_PAT;
    const repo = env.GH_REPO || DEFAULT_REPO;
    const branch = env.GH_BRANCH || "main";
    if (!token) {
      return json({ error: "Worker 未配置 GH_PAT" }, 500);
    }

    if (new URL(request.url).pathname === "/health" && request.method === "GET") {
      try {
        await fetchSaved(repo, branch, token);
        if (!env.SAVE_KEY || !env.FEISHU_WEBHOOK) throw new Error("Security or alert secret missing");
        return json({ok:true,version:"hardened-v1"});
      } catch(error) { return json({error:error.message},503); }
    }

    // GET：直接读最新收藏列表（走 GitHub API，无 CDN 缓存），供精选页/日报页使用
    if (request.method === "GET") {
      try {
        const { items } = await fetchSaved(repo, branch, token);
        return json({ ok: true, items });
      } catch (e) {
        return json({ error: e.message || "内部错误" }, 500);
      }
    }

    if (request.method !== "POST") {
      return json({ error: "仅支持 GET / POST" }, 405);
    }

    if (!env.SAVE_KEY) return json({error:"收藏写入密码未配置"},503);
    if (!await authorized(request, env.SAVE_KEY)) return json({error:"访问密码不正确"},401);
    if (Number(request.headers.get("Content-Length") || 0) > 20000) return json({error:"请求过大"},413);
    let meta;
    try {
      const reader = request.body?.getReader();
      let size = 0; const chunks = [];
      if (!reader) return json({error:"请求体为空"},400);
      while (true) {
        const {done,value} = await reader.read();
        if (done) break;
        size += value.length;
        if (size > 20000) { await reader.cancel(); return json({error:"请求过大"},413); }
        chunks.push(value);
      }
      const bytes = new Uint8Array(size); let offset = 0;
      for (const chunk of chunks) { bytes.set(chunk,offset); offset += chunk.length; }
      meta = JSON.parse(new TextDecoder().decode(bytes));
    } catch {
      return json({ error: "请求体不是合法 JSON" }, 400);
    }
    if (!meta || typeof meta.repo !== "string" || !/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(meta.repo)) return json({error:"repo 格式不正确"},400);
    for (const key of ["url","site"]) {
      if (meta[key] !== undefined && (typeof meta[key] !== "string" || meta[key].length > 4000)) return json({error:"链接字段不合法"},400);
      if (meta[key] && meta[key] !== "无") {
        try { if (!["https:","http:"].includes(new URL(meta[key]).protocol)) throw new Error(); }
        catch (_) { return json({error:"仅允许 HTTP/HTTPS 链接"},400); }
      }
    }
    for (const key of ["owner","category","emoji","desc","note"]) {
      if (meta[key] !== undefined && (typeof meta[key] !== "string" || meta[key].length > 4000)) return json({error:"字段不合法"},400);
    }
    if (meta.stars !== undefined && (!Number.isSafeInteger(meta.stars) || meta.stars < 0)) return json({error:"stars 不合法"},400);
    if (meta._remove !== undefined && typeof meta._remove !== "boolean") return json({error:"删除标志不合法"},400);
    if (meta.tags !== undefined && (!Array.isArray(meta.tags) || meta.tags.length > 30 || meta.tags.some(t=>typeof t !== "string" || t.length > 100))) return json({error:"tags 不合法"},400);

    try {
      // 计算目标 items 列表（对原始 items 做增删改）
      // 注意北京时间 = UTC+8，与周报 sync_saved.py 的 7 天窗口口径一致；
      // 用 UTC 的话，北京时间凌晨 0~8 点的收藏会被算成「昨天」。
      const bjToday = () => new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 10);
      const applyChange = (baseItems) => {
        const idx = baseItems.findIndex((it) => it.repo === meta.repo);
        let removed = false;
        if (meta._remove) {
          // 取消收藏
          if (idx >= 0) baseItems.splice(idx, 1);
          removed = idx >= 0;
        } else if (idx >= 0) {
          // 已收藏：幂等更新。只刷新动态元数据，保留用户填的 note / tags / saved_at，
          // 避免「前端状态丢失后重复点收藏」把已有备注清空或误删收藏。
          const cur = baseItems[idx];
          baseItems[idx] = {
            ...cur,
            url: meta.url || cur.url,
            owner: meta.owner || cur.owner,
            stars: meta.stars ?? cur.stars,
            category: meta.category || cur.category,
            emoji: meta.emoji || cur.emoji,
            desc: meta.desc || cur.desc,
            site: meta.site || cur.site,
          };
          removed = false; // 仍是收藏状态
        } else {
          baseItems.push({
            repo: meta.repo,
            url: meta.url || `https://github.com/${meta.repo}`,
            owner: meta.owner || meta.repo.split("/")[0],
            stars: meta.stars || 0,
            category: meta.category || "其他",
            emoji: meta.emoji || "📦",
            desc: meta.desc || "",
            site: meta.site || "无",
            note: meta.note || "",
            tags: Array.isArray(meta.tags) ? meta.tags : [],
            saved_at: bjToday(),
          });
        }
        return { removed };
      };

      // 带冲突重试的写入：并发收藏时可能拿到旧 sha，写入 409/422，此时重读最新再写
      let items, removed, sha;
      for (let attempt = 0; attempt < 3; attempt++) {
        const cur = await fetchSaved(repo, branch, token);
        items = cur.items;
        sha = cur.sha;
        const change = applyChange(items);
        removed = change.removed;
        try {
          await writeSaved(repo, branch, token, items, sha);
          break; // 写入成功
        } catch (e) {
          const conflict = /409|422/.test(String(e.message));
          if (!conflict || attempt === 2) throw e;
          // 冲突：短暂等待后重读最新 sha 重试
          await new Promise((r) => setTimeout(r, 200 * (attempt + 1)));
        }
      }

      // 返回最新完整列表，前端可直接用，无需再回读 raw
      return json({ ok: true, removed, items });
    } catch (e) {
      return json({ error: e.message || "内部错误" }, 500);
    }
  },
};
