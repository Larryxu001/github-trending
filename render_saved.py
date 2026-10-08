#!/usr/bin/env python3
"""渲染「我的精选」独立页 site/saved.html。
页面访问验证后，从收藏服务读取最新列表。
Usage: render_saved.py"""
import json, os
from page_access import protect_page

BASE = os.path.dirname(os.path.abspath(__file__))
P = lambda n: os.path.join(BASE, n)

RAW_URL = "https://raw.githubusercontent.com/Larryxu001/github-trending/main/saved.json"


CSS = """
  :root { --ink:#2B2419; --sub:#7A7263; --red:#C02B1F;
          --paper:#FBF7EC; --soft:#F4EEDD; --hair:#E6DDC6;
          --serif:"Noto Serif SC","Songti SC","STSong",Georgia,serif;
          --sans:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:var(--paper); color:var(--ink); font-family:var(--serif);
         font-size:17px; line-height:1.7; }
  a { color:inherit; }
  .masthead { max-width:860px; margin:0 auto; padding:32px 24px 0; text-align:center; }
  .topline { font-family:var(--sans); font-size:11px; letter-spacing:.22em; color:var(--sub);
             display:flex; justify-content:space-between; padding-bottom:12px;
             border-bottom:1px solid var(--ink); }
  h1 { font-weight:900; font-size:clamp(32px,6vw,46px); letter-spacing:.02em; padding:24px 0 8px; }
  .stand { font-style:italic; color:var(--sub); font-size:15px; }
  .doublerule { border-top:1px solid var(--ink); border-bottom:3px double var(--ink); height:5px; margin-top:18px; }
  .wrap { padding:28px 24px 60px; }
  .layout { max-width:1180px; margin:0 auto; display:flex; align-items:flex-start; }
  main { flex:1; min-width:0; max-width:800px; margin:0 auto; }
  section { padding:44px 24px 8px; scroll-margin-top:20px; }

  /* ---------- table of contents ---------- */
  .toc { width:260px; flex-shrink:0; position:sticky; top:24px;
          max-height:calc(100vh - 48px); overflow-y:auto;
          padding:44px 8px 24px 8px; font-family:var(--sans); scrollbar-width:thin; }
  .toc-title { font-size:11px; letter-spacing:.2em; color:var(--sub);
                padding-bottom:10px; border-bottom:1px solid var(--ink); margin-bottom:4px; }
  .toc a { display:flex; align-items:baseline; gap:10px;
            color:var(--ink); text-decoration:none; transition:color .15s; }
  .toc a:hover { color:var(--red); }
  .toc details { border-bottom:1px solid var(--hair); padding:2px 0; }
  .toc summary { display:flex; align-items:baseline; gap:10px;
                  padding:10px 0 8px; font-size:13.5px; font-weight:600;
                  cursor:pointer; list-style:none; user-select:none; transition:color .15s; }
  .toc summary::-webkit-details-marker { display:none; }
  .toc summary::after { content:"▾"; margin-left:auto; font-size:11px; color:var(--sub);
                         transition:transform .2s; }
  .toc details:not([open]) > summary::after { transform:rotate(-90deg); }
  .toc summary:hover { color:var(--red); }
  .toc summary .toc-n { margin-left:0; }
  .toc summary::after { margin-left:auto; }
  .toc-proj { padding:5px 0 5px 26px; font-size:12.5px; color:#6B6355;
               border-bottom:1px dashed var(--hair); }
  .toc-proj:hover { color:var(--red); }
  .toc-no { font-family:var(--serif); font-style:italic; color:#C9BB93; font-weight:700;
             font-size:12px; min-width:18px; }
  .toc-n { margin-left:auto; font-size:11px; color:var(--sub); }
  @media (max-width:1020px) {
    .layout { display:block; }
    .toc { position:static; width:auto; max-width:720px; margin:0 auto;
            max-height:none; overflow:visible; padding:20px 24px 0; }
  }
  .sec-kicker { display:flex; align-items:baseline; gap:12px; font-family:var(--sans); }
  .sec-no { font-size:11px; letter-spacing:.18em; color:var(--red); font-weight:600; }
  .sec-name { font-family:var(--serif); font-weight:700; font-size:22px; }
  .sec-count { margin-left:auto; font-size:11px; letter-spacing:.12em; color:var(--sub); }
  .rule { border:none; border-top:1px solid var(--ink); margin:8px 0 4px; }


  .item, .toc-proj { scroll-margin-top:24px; }
  .item .title, .item .site { overflow-wrap:anywhere; }
  .search-row input { min-width:0; }
  .bar { display:flex; align-items:center; gap:12px; font-family:var(--sans); font-size:13px;
         color:var(--sub); margin-bottom:8px; flex-wrap:wrap; }
  .bar .count { font-weight:700; color:var(--ink); }
  .bar .spacer { flex:1; }
  .bar button { font-family:var(--sans); font-size:12px; padding:6px 12px; border:1px solid var(--hair);
                border-radius:4px; background:transparent; color:var(--ink); cursor:pointer; }
  .bar button:hover { color:var(--red); border-color:var(--red); }
  .bar button.active { color:var(--red); border-color:var(--red); background:#FBE7E4; }
  .search-row { display:flex; gap:10px; margin:14px 0 6px; }
  .search-row input { flex:1; padding:9px 14px; font-size:14px; border:1px solid var(--hair);
                      border-radius:6px; background:#fff; color:var(--ink); font-family:var(--sans); }
  .search-row input:focus { outline:none; border-color:var(--red); }
  .search-row select { padding:9px 10px; font-size:13px; border:1px solid var(--hair);
                       border-radius:6px; background:#fff; color:var(--ink); font-family:var(--sans); cursor:pointer; }
  .import-box { padding:16px 0 20px; border-bottom:1px solid var(--hair); margin-bottom:18px; font-family:var(--sans); }
  .import-box label { display:block; font-size:15px; font-weight:600; }
  .import-row { display:flex; gap:10px; margin:10px 0 6px; }
  .import-row input { flex:1; min-width:0; padding:10px 12px; font:14px var(--sans); border:1px solid var(--hair); border-radius:6px; }
  .import-row button { padding:10px 14px; background:var(--ink); color:var(--paper); border:0; border-radius:6px; cursor:pointer; }
  .import-row button:disabled { opacity:.6; cursor:wait; }
  .import-box p { font-size:12px; color:var(--sub); }
  .import-box :focus-visible { outline:2px solid var(--red); outline-offset:3px; }
  .tagbar { display:flex; flex-wrap:wrap; gap:6px; margin:6px 0 4px; }
  .tagbar .tag { font-size:12px; padding:3px 10px; border:1px solid var(--hair); border-radius:13px;
                 cursor:pointer; user-select:none; color:var(--ink); font-family:var(--sans); }
  .tagbar .tag.on { color:var(--red); border-color:var(--red); background:#FBE7E4; }
  .item { padding:22px 0; border-bottom:1px solid var(--hair); display:flex; gap:16px; align-items:flex-start; }
  .item .emoji { font-size:22px; width:32px; flex-shrink:0; text-align:center; }
  .item .body { flex:1; min-width:0; }
  .item .head { display:flex; align-items:baseline; gap:12px; flex-wrap:wrap; }
  .item .title { font-size:19px; font-weight:700; }
  .item .title a { text-decoration:none; border-bottom:2px solid transparent; }
  .item .title a:hover { border-bottom-color:var(--red); color:var(--red); }
  .item .stars { font-family:var(--sans); font-weight:700; font-size:14px; color:var(--sub); }
  .item .cat { font-family:var(--sans); font-size:11px; color:var(--red); letter-spacing:.06em; }
  .item .desc { margin:6px 0 8px; color:#4A4234; font-size:15px; }
  .item .note { margin:0 0 8px; padding:8px 12px; background:var(--soft); border-left:3px solid var(--red);
                color:#5A4E3A; font-size:14px; border-radius:0 4px 4px 0; }
  .item .note b { color:var(--ink); font-family:var(--sans); font-size:12px; font-weight:600; }
  .item .tags { display:flex; flex-wrap:wrap; gap:5px; margin:0 0 8px; }
  .item .tags span { font-family:var(--sans); font-size:11px; padding:2px 8px; border:1px solid var(--hair);
                     border-radius:11px; color:var(--sub); }
  .item .meta { font-family:var(--sans); font-size:12px; color:var(--sub); display:flex;
                gap:8px; flex-wrap:wrap; align-items:center; }
  .item .meta i { font-style:normal; color:var(--hair); }
  .item .site { color:var(--ink); font-weight:600; text-decoration:none; border-bottom:1px solid var(--ink); }
  .item .site:hover { color:var(--red); border-bottom-color:var(--red); }
  .item .date { font-family:var(--sans); font-size:11px; color:#C9BB93; }
  .item .unsave { margin-left:auto; font-family:var(--sans); font-size:12px; color:var(--sub);
                  background:transparent; border:1px solid var(--hair); border-radius:4px;
                  padding:3px 10px; cursor:pointer; }
  .item .unsave:hover { color:var(--red); border-color:var(--red); }
  .empty { text-align:center; padding:80px 0; color:var(--sub); font-style:italic; }
  .empty .big { font-size:48px; margin-bottom:12px; }
  .loading { text-align:center; padding:60px 0; color:var(--sub); font-style:italic; }
  @media (max-width:600px) {
    .import-row, .search-row { flex-wrap:wrap; }
    .import-row input, .search-row input { flex-basis:100%; }
  }

"""

JS = """
const RAW_URL = {raw_url};
const SAVE_API = {save_api};

function esc(s) {{ return String(s).replace(/[&<>"]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c])); }}
function starsFmt(n) {{ return (n && n > 0) ? '★ ' + Number(n).toLocaleString() : ''; }}


function saveHeaders() {{
  const key = sessionStorage.getItem('trending-save-key');
  if (!key) {{ location.reload(); return null; }}
  return {{'Content-Type':'application/json', 'Authorization':'Bearer ' + key.trim()}};
}}
function safeUrl(value) {{
  try {{ const u = new URL(value); return ['https:','http:'].includes(u.protocol) ? u.href : ''; }}
  catch(_) {{ return ''; }}
}}

let allRows = [];
let activeTags = new Set();

async function loadSaved() {{
  const list = document.getElementById('list');
  list.innerHTML = '<div class="loading">加载中…</div>';
  try {{
    let items = null;
    // 优先走 Worker GET（GitHub API，无 CDN 缓存）
    if (SAVE_API) {{
      try {{
        const r = await fetch(SAVE_API, {{ cache: 'no-store' }});
        if (r.ok) {{
          const d = await r.json();
          if (d.ok && Array.isArray(d.items)) items = d.items;
        }}
      }} catch(_) {{}}
    }}
    // 降级：raw + 时间戳穿透
    if (items === null) {{
      const sep = RAW_URL.indexOf('?') >= 0 ? '&' : '?';
      const resp = await fetch(RAW_URL + sep + 'cb=' + Date.now(), {{ cache: 'no-store' }});
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      const data = await resp.json();
      items = (data.items || []);
    }}
    allRows = items;
    renderTagBar();
    render();
  }} catch(e) {{
    list.innerHTML = '<div class="empty"><div class="big">★</div>加载失败，请稍后重试<br><span style="font-size:12px;">' + esc(e.message) + '</span></div>';
  }}
}}

function renderTagBar() {{
  const bar = document.getElementById('tagBar');
  const counts = {{}};
  allRows.forEach(r => (r.tags || []).forEach(t => counts[t] = (counts[t] || 0) + 1));
  const tags = Object.keys(counts).sort((a,b) => counts[b] - counts[a]);
  bar.innerHTML = tags.map(t =>
    '<span class="tag' + (activeTags.has(t) ? ' on' : '') + '" data-tag="' + esc(t) + '" onclick="toggleTag(this)">' +
    esc(t) + ' <span style="opacity:.6">' + counts[t] + '</span></span>').join('');
}}

window.toggleTag = function(el) {{
  const t = el.dataset.tag;
  if (activeTags.has(t)) activeTags.delete(t); else activeTags.add(t);
  renderTagBar();
  render();
}};

window.sortChanged = function() {{
  render();
}};

function getFiltered() {{
  const q = (document.getElementById('search').value || '').trim().toLowerCase();
  let rows = allRows.slice();
  if (activeTags.size > 0) rows = rows.filter(r => (r.tags || []).some(t => activeTags.has(t)));
  if (q) rows = rows.filter(r =>
    (r.repo + ' ' + (r.desc || '') + ' ' + (r.note || '') + ' ' + (r.category || '') + ' ' + (r.tags || []).join(' ')).toLowerCase().includes(q));
  const sort = document.getElementById('sort').value;
  if (sort === 'stars') rows.sort((a,b) => (b.stars||0) - (a.stars||0));
  else if (sort === 'time') rows.sort((a,b) => (b.saved_at||'').localeCompare(a.saved_at||''));
  else if (sort === 'name') rows.sort((a,b) => a.repo.localeCompare(b.repo));
  return rows;
}}

function render() {{
  const list = document.getElementById('list');
  const count = document.getElementById('count');
  const toc = document.getElementById('toc-items');
  toc.innerHTML = '';
  const rows = getFiltered();
  count.textContent = allRows.length + (rows.length !== allRows.length ? ' / 筛出 ' + rows.length : '');
  if (allRows.length === 0) {{
    list.innerHTML = '<div class="empty"><div class="big">★</div>还没有收藏。粘贴 GitHub 项目链接，或去日报里点击「☆ 收藏」。</div>';
    return;
  }}
  if (rows.length === 0) {{
    list.innerHTML = '<div class="empty"><div class="big">∅</div>没有匹配的收藏，换个关键词或标签试试</div>';
    return;
  }}
  const groups = new Map();
  rows.forEach(r => {{
    const category = r.category || '其他';
    if (!groups.has(category)) groups.set(category, []);
    groups.get(category).push(r);
  }});
  const categories = [...groups.keys()].sort((a,b) => a === '其他' ? 1 : b === '其他' ? -1 : a.localeCompare(b, 'zh-CN'));
  list.innerHTML = categories.map((category, si) => {{
    const items = groups.get(category);
    const sectionId = 'sec-' + (si + 1);
    const number = String(si + 1).padStart(2, '0');
    toc.innerHTML += '<details><summary><span class="toc-no">' + number + '</span>' + esc(category) +
      '<span class="toc-n">' + items.length + '</span></summary>' +
      items.map((r,i) => '<a class="toc-proj" href="#' + sectionId + '-' + (i + 1) + '"><span class="toc-no">' +
        String(i + 1).padStart(2, '0') + '</span>' + esc(r.repo.split('/').pop()) + '</a>').join('') + '</details>';
    return '<section id="' + sectionId + '"><div class="sec-kicker"><span class="sec-no">SECTION ' + number +
      '</span><h2 class="sec-name">' + esc(category) + '</h2><span class="sec-count">' + items.length +
      ' 个项目</span></div><hr class="rule">' + items.map((r,i) => {{
    const site = (r.site && r.site !== '无' && r.site !== '')
      ? '<a class="site" href="' + esc(safeUrl(r.site)) + '" target="_blank">' + esc(r.site) + '</a>' : '无官网';
    const url = safeUrl(r.url) || 'https://github.com/' + r.repo;
    const date = r.saved_at ? '<span class="date">收藏于 ' + esc(String(r.saved_at).slice(0,10)) + '</span>' : '';
    const tags = (r.tags && r.tags.length) ? '<div class="tags">' + r.tags.map(t => '<span>' + esc(t) + '</span>').join('') + '</div>' : '';
    const note = r.note ? '<div class="note"><b>我的备注</b><br>' + esc(r.note) + '</div>' : '';
    return '<div class="item" id="' + sectionId + '-' + (i + 1) + '" data-repo="' + esc(r.repo) + '">' +
      '<div class="emoji">' + esc(r.emoji || '📦') + '</div>' +
      '<div class="body">' +
        '<div class="head"><span class="cat">' + esc(r.category || '其他') + '</span>' +
        '<span class="title"><a href="' + esc(url) + '" target="_blank">' + esc(r.repo) + '</a></span>' +
        '<span class="stars">' + starsFmt(r.stars) + '</span>' +
        '<button class="unsave" onclick="unsave(this)">取消收藏</button></div>' +
        (r.desc ? '<p class="desc">' + esc(r.desc) + '</p>' : '') +
        note + tags +
        '<div class="meta"><span>' + esc(r.owner || '') + '</span><i>·</i><span>' + site + '</span><i>·</i>' + date + '</div>' +
      '</div></div>';
    }}).join('') + '</section>';
  }}).join('');
}}

window.unsave = async function(btn) {{
  if (!SAVE_API) {{ alert('收藏服务未配置'); return; }}
  const repo = btn.closest('.item').dataset.repo;
  if (!confirm('确定取消收藏「' + repo + '」？')) return;
  const authHeaders = saveHeaders();
  if (!authHeaders) return;
  try {{
    const resp = await fetch(SAVE_API, {{
      method: 'POST',
      headers: authHeaders,
      body: JSON.stringify({{ repo: repo, _remove: true }}),
    }});
    const result = await resp.json();
    if (resp.status === 401) sessionStorage.removeItem('trending-save-key');
    if (!resp.ok || result.error) {{ alert(result.error || '取消失败'); return; }}
    // 乐观更新：立刻从本地移除并重绘，不等 raw 回读
    allRows = allRows.filter(r => r.repo !== repo);
    renderTagBar();
    render();
  }} catch(err) {{
    const msg = (err && err.message) ? err.message : '请检查网络';
    const isNet = /fetch|network/i.test(msg);
    alert((isNet ? '网络错误' : '程序错误') + '，取消失败：' + msg);
  }}
}};


let importPending = false;
let importPollCount = 0;
function importMessage(message, url) {{
  const status = document.getElementById('import-status');
  status.textContent = message;
  if (url) {{
    const a = document.createElement('a'); a.href = url; a.target = '_blank'; a.rel = 'noopener';
    a.textContent = ' 查看任务'; status.appendChild(a);
  }}
}}
function importBusy(value) {{
  importPending = value;
  document.getElementById('import-submit').disabled = value;
  document.getElementById('import-submit').textContent = value ? '处理中…' : 'AI 分析并加入';
}}
async function pollImport(id) {{
  const headers = saveHeaders(); if (!headers) return;
  try {{
    const response = await fetch(SAVE_API + '/imports/' + encodeURIComponent(id), {{headers, signal:AbortSignal.timeout(15000)}});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || '任务状态暂时无法读取');
    if (result.status === 'completed') {{
      sessionStorage.removeItem('trending-import-id'); importBusy(false);
      if (result.conclusion === 'success') {{
        importMessage('已处理完成，项目已在精选库中。将按收藏时间纳入周报和月报。');
        document.getElementById('import-url').value = ''; await loadSaved();
      }} else {{
        importMessage('任务未成功完成，请查看任务详情；修复后可以重新提交。', result.url);
      }}
      return;
    }}
    importMessage(result.status === 'in_progress' ? '正在读取项目信息并进行 AI 分析…' : '已提交，正在排队。你可以离开页面，任务会继续处理。', result.url);
    if (++importPollCount >= 40) {{
      importMessage('任务仍在处理中，可查看任务进度；刷新此页面可继续查询。', result.url);
      importBusy(false); return;
    }}
    setTimeout(() => pollImport(id), 15000);
  }} catch (error) {{
    importMessage(error.message + '；刷新页面可继续查询任务。'); importBusy(false);
  }}
}}
window.submitImport = async function(event) {{
  event.preventDefault(); if (importPending) return;
  const headers = saveHeaders(); if (!headers) return;
  const url = document.getElementById('import-url').value.trim();
  importBusy(true); importMessage('正在提交项目…');
  try {{
    const response = await fetch(SAVE_API + '/imports', {{method:'POST',headers,
      body:JSON.stringify({{url}}),signal:AbortSignal.timeout(15000)}});
    const result = await response.json();
    if (response.status === 401) sessionStorage.removeItem('trending-save-key');
    if (!response.ok) throw new Error(result.error || '提交失败');
    sessionStorage.setItem('trending-import-id', result.id); importPollCount = 0;
    await pollImport(result.id);
  }} catch (error) {{
    importMessage(error.message + '；请确认任务状态后再重试。'); importBusy(false);
  }}
}};
window.addEventListener('trending-unlocked', () => {{
  const id = sessionStorage.getItem('trending-import-id');
  if (id) {{ importBusy(true); pollImport(id); }}
}});

window.addEventListener('trending-unlocked', loadSaved);
"""


def render(save_api=""):
    js = JS.format(raw_url=json.dumps(RAW_URL), save_api=json.dumps(save_api))
    return protect_page(f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>我的精选 · Github开源趋势日报</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@500;700;900&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
  <header class="masthead">
    <div class="topline"><span>MY SAVED REPOS</span><span>我的精选</span></div>
    <h1>我的精选</h1>
    <div class="stand">收藏热榜项目，也收录你主动发现的好工具</div>
    <div class="doublerule"></div>
  </header>

  <div class="layout">
    <aside class="toc" aria-label="分类目录">
      <div class="toc-title">目录 · CONTENTS</div>
      <div id="toc-items"></div>
    </aside>
  <main class="wrap">
    <div class="bar">
      <span>共 <span class="count" id="count">0</span> 个收藏</span>
      <span class="spacer"></span>
      <button onclick="location.href='index.html'">返回归档</button>
    </div>

    <form class="import-box" onsubmit="submitImport(event)">
      <label for="import-url">添加你发现的 GitHub 项目</label>
      <div class="import-row">
        <input type="url" id="import-url" placeholder="https://github.com/owner/repo" required autocomplete="off">
        <button id="import-submit" type="submit">AI 分析并加入</button>
      </div>
      <p id="import-status" role="status" aria-live="polite">自动生成中文介绍和分类，加入精选后纳入周报、月报。</p>
    </form>
    <div class="search-row">
      <input type="text" id="search" placeholder="搜索项目名 / 描述 / 备注 / 标签…" oninput="render()">
      <select id="sort" onchange="sortChanged()">
        <option value="stars">按星数排序</option>
        <option value="time">按收藏时间</option>
        <option value="name">按名称</option>
      </select>
    </div>
    <div class="tagbar" id="tagBar"></div>

    <div id="list"></div>
  </main>
  </div>

<script>{js}</script>
</body>
</html>""", save_api)


def main():
    site_dir = P("site")
    os.makedirs(site_dir, exist_ok=True)
    dest = os.path.join(site_dir, "saved.html")
    # 读取 save_api（CF Worker 地址），用于精选页取消收藏
    save_api = ""
    cp = P("save_config.json")
    if os.path.exists(cp):
        try:
            save_api = json.load(open(cp, encoding="utf-8")).get("save_api", "")
        except Exception:
            pass
    open(dest, "w").write(render(save_api))
    print(dest)


if __name__ == "__main__":
    main()
