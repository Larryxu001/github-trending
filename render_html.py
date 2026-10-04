#!/usr/bin/env python3
"""Render report.json into an NYT-editorial-style HTML report at site/index.html.
Design recipe: nyt-the-daily (web-design-engineer skill) — serif voice, hairlines, no cards.
Usage: render_html.py [report_json]"""
import json, os, sys, html, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
LIST_LABEL = {"daily": "日榜", "weekly": "周榜", "monthly": "月榜"}
EPOCH = datetime.date(2026, 10, 3)  # 创刊日

CN_NUM = "零一二三四五六七八九"

def esc(s):
    return html.escape(str(s))

def stars_fmt(n):
    return f"{n:,}" if isinstance(n, int) else "—"

def cn_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.year} 年 {d.month} 月 {d.day} 日"

def masthead_info(report):
    """Return (title, standfirst, dateline, vol_label) for daily (YYYY-MM-DD) or monthly (YYYY-MM)."""
    date = report["date"]
    if len(date) == 7:  # 月报
        y, m = int(date[:4]), int(date[5:7])
        issue = (y - 2026) * 12 + (m - 10) + 1
        title = "Github开源趋势月报"
        stand = "本月 GitHub Trending 上榜项目全景总结，一期读懂开源风向标"
        line = (f"<b>{y} 年 {m} 月</b>　·　第 {issue} 期（月刊）　·　"
                f"本月共收录 <b>{report['new_count']}</b> 个项目")
        return title, stand, line, f"VOL.M{issue:02d}"
    issue = (datetime.date.fromisoformat(date) - EPOCH).days + 1
    title = "Github开源趋势日报"
    stand = "GitHub Trending 日 / 周 / 月三榜精选，人工解读每一个上榜项目"
    line = (f"<b>{cn_date(date)}</b>　·　第 {issue} 期　·　"
            f"本期新收录 <b>{report['new_count']}</b> 个项目　·　30 天去重跳过 {report['skipped']} 个")
    return title, stand, line, f"VOL.{issue:03d}"

def render(report, save_api="", saved_url="saved.html", archive_url="index.html"):
    date = report["date"]
    title, stand, dateline, vol = masthead_info(report)
    monthly = len(date) == 7
    doc_title = f"GitHub Trending {'月报' if monthly else '日报'} · {date}"
    sections = []
    toc_items = []
    for si, cat in enumerate(report["categories"], 1):
        proj_links = []
        for i, it in enumerate(cat["items"], 1):
            short = it["repo"].split("/")[-1]
            proj_links.append(
                f'<a class="toc-proj" href="#sec-{si}-{i}"><span class="toc-no">{i:02d}</span>{esc(short)}</a>')
        toc_items.append(
            f'<details><summary><span class="toc-no">{si:02d}</span>{esc(cat["name"])}'
            f'<span class="toc-n">{len(cat["items"])}</span></summary>'
            + "".join(proj_links) + "</details>")
        items = []
        for i, it in enumerate(cat["items"], 1):
            lists = " · ".join(LIST_LABEL[l] for l in it["lists"] if l in LIST_LABEL)
            daily = "daily" in it["lists"]
            site = ("无官网" if it["site"] == "无"
                    else f'<a class="site" href="{esc(it["site"])}" target="_blank">{esc(it["site"])}</a>')
            # 收藏按钮所需的项目元数据（JSON 序列化后放入 data 属性）
            meta = json.dumps({
                "repo": it["repo"], "url": it["url"], "owner": it["owner"],
                "stars": it["stars"], "desc": it["desc"], "site": it["site"],
                "category": cat["name"], "emoji": cat["emoji"],
            }, ensure_ascii=False)
            items.append(f"""
        <article class="item" id="sec-{si}-{i}">
          <div class="item-head">
            <span class="no">{i:02d}</span>
            <h3 class="title"><a href="{esc(it['url'])}" target="_blank">{esc(it['repo'])}</a></h3>
            <span class="stars">★ {stars_fmt(it['stars'])}</span>
            <button class="save-btn" data-meta='{esc(meta)}' aria-label="收藏项目">☆ 收藏</button>
          </div>
          <p class="desc">{esc(it['desc'])}</p>
          <div class="byline">
            <span>{esc(it['owner'])}</span><i>·</i>
            <span>更新于 {esc(it['updated'])}</span><i>·</i>
            <span class="{'hot' if daily else ''}">{lists}</span><i>·</i>
            {site}
          </div>
        </article>""")
        sections.append(f"""
      <section id="sec-{si}">
        <div class="sec-kicker"><span class="sec-no">SECTION {si:02d}</span><span class="sec-name">{esc(cat['name'])}</span><span class="sec-count">{len(cat['items'])} 个项目</span></div>
        <hr class="rule">
        {''.join(items)}
      </section>""")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{doc_title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@500;700;900&display=swap" rel="stylesheet">
<style>
  :root {{
    --ink:#2B2419; --sub:#7A7263; --red:#C02B1F;
    --paper:#FBF7EC; --soft:#F4EEDD; --hair:#E6DDC6;
    --serif:"Noto Serif SC","Songti SC","STSong",Georgia,"Times New Roman",serif;
    --sans:-apple-system,"Helvetica Neue","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:var(--paper); color:var(--ink); font-family:var(--serif);
         font-size:17px; line-height:1.75; -webkit-font-smoothing:antialiased; }}
  a {{ color:inherit; }}

  /* ---------- masthead ---------- */
  .masthead {{ max-width:800px; margin:0 auto; padding:28px 24px 0; text-align:center; }}
  .topline {{ font-family:var(--sans); font-size:11px; letter-spacing:.22em;
              color:var(--sub); display:flex; justify-content:space-between;
              padding-bottom:12px; border-bottom:1px solid var(--ink); }}
  h1 {{ font-weight:900; font-size:clamp(34px,7vw,52px); letter-spacing:.02em;
        padding:26px 0 10px; }}
  .standfirst {{ font-style:italic; color:var(--sub); font-size:16px; }}
  .dateline {{ font-family:var(--sans); font-size:12px; color:var(--sub);
               letter-spacing:.06em; margin:18px 0 14px; }}
  .dateline b {{ color:var(--ink); font-weight:600; }}
  .doublerule {{ border-top:1px solid var(--ink); border-bottom:3px double var(--ink);
                 height:5px; }}

  /* ---------- sections ---------- */
  .layout {{ max-width:1180px; margin:0 auto; display:flex; align-items:flex-start; }}
  main {{ flex:1; min-width:0; max-width:800px; margin:0 auto; }}
  section {{ padding:44px 24px 8px; scroll-margin-top:20px; }}

  /* ---------- table of contents ---------- */
  .toc {{ width:260px; flex-shrink:0; position:sticky; top:24px;
          max-height:calc(100vh - 48px); overflow-y:auto;
          padding:44px 8px 24px 8px; font-family:var(--sans); scrollbar-width:thin; }}
  .toc-title {{ font-size:11px; letter-spacing:.2em; color:var(--sub);
                padding-bottom:10px; border-bottom:1px solid var(--ink); margin-bottom:4px; }}
  .toc a {{ display:flex; align-items:baseline; gap:10px;
            color:var(--ink); text-decoration:none; transition:color .15s; }}
  .toc a:hover {{ color:var(--red); }}
  .toc details {{ border-bottom:1px solid var(--hair); padding:2px 0; }}
  .toc summary {{ display:flex; align-items:baseline; gap:10px;
                  padding:10px 0 8px; font-size:13.5px; font-weight:600;
                  cursor:pointer; list-style:none; user-select:none; transition:color .15s; }}
  .toc summary::-webkit-details-marker {{ display:none; }}
  .toc summary::after {{ content:"▾"; margin-left:auto; font-size:11px; color:var(--sub);
                         transition:transform .2s; }}
  .toc details:not([open]) > summary::after {{ transform:rotate(-90deg); }}
  .toc summary:hover {{ color:var(--red); }}
  .toc summary .toc-n {{ margin-left:0; }}
  .toc summary::after {{ margin-left:auto; }}
  .toc-proj {{ padding:5px 0 5px 26px; font-size:12.5px; color:#6B6355;
               border-bottom:1px dashed var(--hair); }}
  .toc-proj:hover {{ color:var(--red); }}
  .toc-no {{ font-family:var(--serif); font-style:italic; color:#C9BB93; font-weight:700;
             font-size:12px; min-width:18px; }}
  .toc-n {{ margin-left:auto; font-size:11px; color:var(--sub); }}
  @media (max-width:1020px) {{
    .layout {{ display:block; }}
    .toc {{ position:static; width:auto; max-width:720px; margin:0 auto;
            max-height:none; overflow:visible; padding:20px 24px 0; }}
  }}
  .sec-kicker {{ display:flex; align-items:baseline; gap:12px; font-family:var(--sans); }}
  .sec-no {{ font-size:11px; letter-spacing:.18em; color:var(--red); font-weight:600; }}
  .sec-name {{ font-family:var(--serif); font-weight:700; font-size:22px; }}
  .sec-count {{ margin-left:auto; font-size:11px; letter-spacing:.12em; color:var(--sub); }}
  .rule {{ border:none; border-top:1px solid var(--ink); margin:8px 0 4px; }}

  /* ---------- items ---------- */
  .item {{ padding:26px 0 22px; border-bottom:1px solid var(--hair); }}
  .item:last-child {{ border-bottom:none; }}
  .item-head {{ display:flex; align-items:baseline; gap:14px; }}
  .no {{ font-family:var(--serif); font-style:italic; color:#D6C9A8;
         font-size:26px; font-weight:700; min-width:36px; }}
  .title {{ font-size:20px; font-weight:700; line-height:1.4; }}
  .title a {{ text-decoration:none; border-bottom:2px solid transparent; transition:border-color .15s; }}
  .title a:hover {{ border-bottom-color:var(--red); color:var(--red); }}
  .stars {{ margin-left:auto; font-family:var(--serif); font-weight:700;
            font-size:16px; white-space:nowrap; padding-left:16px; }}
  .save-btn {{ margin-left:12px; font-family:var(--sans); font-size:12px; font-weight:600;
               color:var(--sub); background:transparent; border:1px solid var(--hair);
               border-radius:4px; padding:3px 10px; cursor:pointer; white-space:nowrap;
               transition:all .15s; }}
  .save-btn:hover {{ color:var(--red); border-color:var(--red); }}
  .save-btn.saved {{ color:var(--red); border-color:var(--red); background:#FBE7E4; }}
  .desc {{ margin:10px 0 14px 50px; color:#4A4234; text-wrap:pretty; }}
  .byline {{ margin-left:50px; font-family:var(--sans); font-size:12px;
             color:var(--sub); display:flex; gap:8px; flex-wrap:wrap; align-items:center; }}
  .byline i {{ font-style:normal; color:var(--hair); }}
  .byline .hot {{ color:var(--red); font-weight:600; }}
  .site {{ color:var(--ink); font-weight:600; text-decoration:none;
           border-bottom:1px solid var(--ink); }}
  .site:hover {{ color:var(--red); border-bottom-color:var(--red); }}

  /* ---------- footer ---------- */
  footer {{ max-width:800px; margin:40px auto 0; padding:20px 24px 44px;
            border-top:1px solid var(--ink); font-family:var(--sans);
            font-size:11px; letter-spacing:.08em; color:var(--sub);
            display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px; }}

  /* ---------- save toast ---------- */
  .toast {{ position:fixed; bottom:28px; left:50%; transform:translateX(-50%) translateY(20px);
            background:var(--ink); color:var(--paper); padding:10px 20px; border-radius:20px;
            font-family:var(--sans); font-size:13px; opacity:0; transition:all .25s;
            z-index:1100; pointer-events:none; }}
  .toast.show {{ opacity:1; transform:translateX(-50%) translateY(0); }}

  /* ---------- save dialog ---------- */
  .dlg-mask {{ display:none; position:fixed; inset:0; background:rgba(43,36,25,.45);
               z-index:1000; justify-content:center; align-items:center; padding:24px; }}
  .dlg-mask.open {{ display:flex; }}
  .dlg {{ background:var(--paper); max-width:460px; width:100%; border-radius:10px;
          padding:26px 24px 22px; box-shadow:0 20px 60px rgba(0,0,0,.28);
          font-family:var(--sans); position:relative; }}
  .dlg h2 {{ font-family:var(--serif); font-size:20px; margin:0 0 2px; }}
  .dlg .repo-name {{ font-size:13px; color:var(--sub); margin-bottom:18px;
                      font-family:var(--sans); word-break:break-all; }}
  .dlg label {{ display:block; font-size:12px; color:var(--sub); margin:14px 0 5px; }}
  .dlg textarea {{ width:100%; min-height:72px; padding:10px 12px; font-size:14px;
                   border:1px solid var(--hair); border-radius:6px; background:#fff;
                   color:var(--ink); resize:vertical; font-family:var(--sans); }}
  .dlg input[type=text] {{ width:100%; padding:9px 12px; font-size:14px;
                           border:1px solid var(--hair); border-radius:6px; background:#fff;
                           color:var(--ink); }}
  .dlg textarea:focus, .dlg input:focus {{ outline:none; border-color:var(--red); }}
  .dlg .tag-chips {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:8px; }}
  .dlg .tag-chip {{ font-size:12px; padding:4px 12px; border:1px solid var(--hair);
                    border-radius:14px; cursor:pointer; user-select:none; color:var(--ink); }}
  .dlg .tag-chip.on {{ color:var(--red); border-color:var(--red); background:#FBE7E4; }}
  .dlg .btn-row {{ display:flex; gap:10px; margin-top:20px; }}
  .dlg .btn-row button {{ flex:1; padding:10px; font-size:14px; font-weight:600;
                          border-radius:6px; cursor:pointer; border:1px solid var(--hair);
                          background:transparent; color:var(--ink); }}
  .dlg .btn-row button.primary {{ background:var(--red); color:#fff; border-color:var(--red); }}
  .dlg .btn-row button.primary:disabled {{ opacity:.5; cursor:not-allowed; }}
  .dlg .hint {{ font-size:11px; color:#C9BB93; margin-top:4px; }}

  @media (max-width:600px) {{
    .desc,.byline {{ margin-left:0; }}
    .item-head {{ flex-wrap:wrap; }}
    .stars {{ padding-left:0; }}
  }}
</style>
</head>
<body>
  <header class="masthead">
    <div class="topline"><span>GITHUB TRENDING {'MONTHLY' if monthly else 'DAILY'}</span><span>{vol}</span></div>
    <h1>{title}</h1>
    <div class="standfirst">{stand}</div>
    <div class="dateline">{dateline}</div>
    <div class="doublerule"></div>
  </header>

  <div class="layout">
    <aside class="toc">
      <div class="toc-title">目录 · CONTENTS</div>
      {''.join(toc_items)}
    </aside>
    <main>
    {''.join(sections)}
    </main>
  </div>

  <footer>
    <span>GITHUB TRENDING {'MONTHLY' if monthly else 'DAILY'} · 自动生成</span>
    <span><a href="{saved_url}" style="color:var(--red);text-decoration:none;">★ 我的精选</a> · <a href="{archive_url}" style="color:var(--ink);text-decoration:none;">往期归档</a> · 数据来源 github.com/trending</span>
  </footer>

  <div class="toast" id="toast"></div>

  <div class="dlg-mask" id="dlgMask">
    <div class="dlg" id="dlg">
      <h2>收藏到「我的精选」</h2>
      <div class="repo-name" id="dlgRepo"></div>
      <label>为什么觉得有用？（备注，可选）</label>
      <textarea id="dlgNote" placeholder="例如：用来做视频剪辑、学习 RAG 落地、给团队搭 Agent…"></textarea>
      <label>打标签（可选，可多选或自定义）</label>
      <div class="tag-chips" id="dlgTags"></div>
      <input type="text" id="dlgNewTag" placeholder="输入新标签后回车添加" style="margin-top:8px;">
      <div class="hint">标签会自动沉淀，之后可在「我的精选」里筛选</div>
      <div class="btn-row">
        <button onclick="closeDlg()">取消</button>
        <button class="primary" id="dlgOk" onclick="confirmSave()">确认收藏</button>
      </div>
    </div>
  </div>

<script>
(function(){{
  const saveApi = {json.dumps(save_api)};
  const rawSavedUrl = 'https://raw.githubusercontent.com/Larryxu001/github-trending/main/saved.json';
  const PRESET_TAGS = ['学习','做视频','做 Agent','做工具','RAG','前端','后端','效率','安全','有趣'];

  let pendingMeta = null;      // 待收藏的项目 meta
  let knownTags = [];          // 已存在的所有标签（来自 saved.json，用于联想）
  let savedSet = new Set();    // 已收藏 repo 集合

  function toast(msg) {{
    const t = document.getElementById('toast');
    t.textContent = msg; t.classList.add('show');
    clearTimeout(t._t); t._t = setTimeout(() => t.classList.remove('show'), 2200);
  }}

  async function loadSavedData() {{
    try {{
      const resp = await fetch(rawSavedUrl, {{ cache: 'no-store' }});
      if (!resp.ok) return;
      const data = await resp.json();
      savedSet = new Set((data.items || []).map(r => r.repo));
      const allTags = new Set(PRESET_TAGS);
      (data.items || []).forEach(r => (r.tags || []).forEach(t => allTags.add(t)));
      knownTags = [...allTags];
    }} catch(_) {{}}
  }}

  async function refreshSavedStates() {{
    document.querySelectorAll('.save-btn').forEach(btn => {{
      let meta; try {{ meta = JSON.parse(btn.dataset.meta); }} catch(_) {{ return; }}
      const saved = savedSet.has(meta.repo);
      btn.classList.toggle('saved', saved);
      btn.textContent = saved ? '★ 已收藏' : '☆ 收藏';
    }});
  }}

  function renderTagChips() {{
    const box = document.getElementById('dlgTags');
    const chips = knownTags.map(t => {{
      const on = pendingMeta && (pendingMeta.tags || []).includes(t);
      return '<span class="tag-chip' + (on ? ' on' : '') + '" data-tag="' + escAttr(t) + '" onclick="toggleTag(this)">' + escHtml(t) + '</span>';
    }});
    box.innerHTML = chips.join('');
  }}

  function escHtml(s) {{ return String(s).replace(/[&<>"]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c])); }}
  function escAttr(s) {{ return String(s).replace(/["&<>]/g, c => ({{'"':'&quot;','&':'&amp;','<':'&lt;','>':'&gt;'}}[c])); }}

  window.toggleTag = function(chip) {{
    const t = chip.dataset.tag;
    if (!pendingMeta.tags) pendingMeta.tags = [];
    const i = pendingMeta.tags.indexOf(t);
    if (i >= 0) pendingMeta.tags.splice(i, 1); else pendingMeta.tags.push(t);
    chip.classList.toggle('on');
  }};

  window.closeDlg = function() {{
    document.getElementById('dlgMask').classList.remove('open');
    pendingMeta = null;
  }};

  window.openSaveDlg = function(meta) {{
    pendingMeta = {{ ...meta, tags: [], note: '' }};
    document.getElementById('dlgRepo').textContent = meta.repo;
    document.getElementById('dlgNote').value = '';
    document.getElementById('dlgNewTag').value = '';
    renderTagChips();
    document.getElementById('dlgMask').classList.add('open');
  }};

  window.confirmSave = async function() {{
    if (!pendingMeta) return;
    if (!saveApi) {{ toast('收藏服务未配置，请联系维护者'); return; }}
    pendingMeta.note = document.getElementById('dlgNote').value.trim();
    const btn = document.getElementById('dlgOk');
    btn.disabled = true;
    try {{
      const resp = await fetch(saveApi, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(pendingMeta),
      }});
      const result = await resp.json().catch(() => ({{}}));
      if (!resp.ok || result.error) {{
        toast(result.error || '收藏失败，请重试');
        return;
      }}
      toast(result.removed ? '已取消收藏' : '已收藏到「我的精选」');
      closeDlg();
      await loadSavedData();
      await refreshSavedStates();
    }} catch(_) {{
      toast('网络错误，收藏失败');
    }} finally {{
      btn.disabled = false;
    }}
  }};

  // 新标签输入：回车添加
  document.getElementById('dlgNewTag').addEventListener('keydown', function(e) {{
    if (e.key !== 'Enter') return;
    e.preventDefault();
    const v = this.value.trim();
    if (!v) return;
    if (!pendingMeta.tags) pendingMeta.tags = [];
    if (!pendingMeta.tags.includes(v)) pendingMeta.tags.push(v);
    if (!knownTags.includes(v)) knownTags.push(v);
    this.value = '';
    renderTagChips();
  }});

  // 已收藏时直接取消（走 Worker toggle）
  async function removeSave(meta) {{
    if (!saveApi) {{ toast('收藏服务未配置'); return; }}
    try {{
      const resp = await fetch(saveApi, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ repo: meta.repo, _remove: true }}),
      }});
      const result = await resp.json().catch(() => ({{}}));
      if (!resp.ok || result.error) {{ toast(result.error || '取消失败'); return; }}
      toast('已取消收藏');
      await loadSavedData();
      await refreshSavedStates();
    }} catch(_) {{ toast('网络错误，取消失败'); }}
  }}

  // 绑定收藏按钮：点击弹出对话框
  document.addEventListener('click', (e) => {{
    const btn = e.target.closest('.save-btn');
    if (!btn) return;
    let meta; try {{ meta = JSON.parse(btn.dataset.meta); }} catch(_) {{ return; }}
    if (savedSet.has(meta.repo)) {{
      if (confirm('已收藏「' + meta.repo + '」，确定取消收藏？')) removeSave(meta);
      return;
    }}
    openSaveDlg(meta);
  }});

  // 点击遮罩关闭
  document.getElementById('dlgMask').addEventListener('click', function(e) {{
    if (e.target === this) closeDlg();
  }});

  (async function init() {{
    await loadSavedData();
    refreshSavedStates();
  }})();
}})();
</script>
</body>
</html>"""

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "report.json")
    report = json.load(open(path))
    # 收藏 API（CF Worker）地址 + 精选页 URL + 归档 URL
    save_api = ""
    saved_url = "saved.html"
    archive_url = "index.html"
    cp = os.path.join(BASE, "save_config.json")
    if os.path.exists(cp):
        try:
            save_api = json.load(open(cp)).get("save_api", "")
        except Exception:
            pass
    # 从 config.json 读 report_url 拼出精选页/归档绝对地址
    try:
        cfg = json.load(open(os.path.join(BASE, "config.json")))
        base = cfg.get("report_url", "")
        if base:
            base = base.rstrip("/")
            saved_url = base + "/saved.html"
            archive_url = base + "/index.html"
    except Exception:
        pass
    site_dir = os.path.join(BASE, "site")
    os.makedirs(site_dir, exist_ok=True)
    dest = os.path.join(site_dir, "index.html")
    open(dest, "w").write(render(report, save_api, saved_url, archive_url))
    print(dest)

if __name__ == "__main__":
    main()
