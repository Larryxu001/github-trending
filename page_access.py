"""Shared password entrance for public Pages (not confidential hosting)."""
import json


def protect_page(page, api):
    head = '''<style>
#page-content[hidden],#page-access[hidden]{display:none!important}
#page-access{min-height:100vh;box-sizing:border-box;display:grid;place-items:center;padding:32px 24px;background:#FBF7EC;color:#2B2419;font-family:-apple-system,"PingFang SC",sans-serif}
#page-access form{width:100%;max-width:360px;border-top:3px double #2B2419;padding-top:28px}
#page-access h1{font:700 28px Georgia,"Songti SC",serif;margin:0 0 12px}
#page-access p{font-size:14px;line-height:1.6;margin:0 0 28px;color:#7A7263}
#page-access label{display:block;font-size:14px;margin-bottom:10px}
#page-access input{box-sizing:border-box;width:100%;padding:13px 12px;font:16px inherit;border:1px solid #8A7F66;background:#fff;color:#2B2419;border-radius:3px}
#page-access button{margin-top:16px;width:100%;padding:13px;font:inherit;border:0;border-radius:3px;background:#2B2419;color:#fff;cursor:pointer}
#page-access button:disabled{opacity:.6;cursor:wait}
#page-access input:focus-visible,#page-access button:focus-visible{outline:3px solid #C02B1F;outline-offset:3px}
#page-access #access-error{min-height:24px;margin:12px 0 0;color:#A92319}
</style>'''
    entrance = '''<section id="page-access" aria-label="页面访问验证">
<form id="access-form"><h1>GitHub 开源趋势</h1><p>输入访问密码，查看日报与精选项目。</p>
<label for="access-password">访问密码</label><input id="access-password" type="password" required autocomplete="current-password" autofocus aria-describedby="access-error">
<button id="access-submit" type="submit">进入页面</button><p id="access-error" role="status" aria-live="polite"></p>
<noscript>请启用 JavaScript 后输入密码。</noscript></form></section><div id="page-content" hidden inert>'''
    script = '''<script>
(() => {
const api = __API__;
const storageKey = 'trending-save-key';
const gate = document.getElementById('page-access');
const content = document.getElementById('page-content');
const form = document.getElementById('access-form');
const password = document.getElementById('access-password');
const button = document.getElementById('access-submit');
const error = document.getElementById('access-error');
async function unlock(key) {
  button.disabled = true;
  button.textContent = '验证中…';
  error.textContent = '';
  try {
    if (!api) throw new Error('访问验证尚未配置，请联系维护者。');
    const response = await fetch(api.replace(/\/$/, '') + '/auth', {
      headers: {Authorization: 'Bearer ' + key}, cache: 'no-store', signal: AbortSignal.timeout(15000)
    });
    if (response.status === 401) {
      sessionStorage.removeItem(storageKey);
      throw new Error('密码不正确，请重新输入。');
    }
    const result = await response.json();
    if (!response.ok || result.ok !== true) throw new Error('验证服务暂时不可用，请稍后重试。');
    sessionStorage.setItem(storageKey, key);
    password.value = '';
    content.hidden = false;
    content.inert = false;
    gate.hidden = true;
    window.dispatchEvent(new Event('trending-unlocked'));
  } catch (failure) {
    error.textContent = failure.message === 'Failed to fetch' || failure.name === 'TimeoutError'
      ? '网络连接失败，请检查网络后重试。' : failure.message;
    password.focus();
  } finally {
    button.disabled = false;
    button.textContent = '进入页面';
  }
}
form.addEventListener('submit', event => {event.preventDefault(); unlock(password.value.trim());});
const saved = sessionStorage.getItem(storageKey);
if (saved) unlock(saved);
})();
</script>'''.replace('__API__', json.dumps(api))
    return page.replace('</head>', head + '</head>', 1).replace('<body>', '<body>' + entrance, 1).replace('</body>', '</div>' + script + '</body>', 1)
