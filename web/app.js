const API = '';
const BUILD = 'v20260918-9';   // 页面构建标识（每页左上角徽章 + 「我的」页可见）
let pollTimers = {};

const $ = (s, p = document) => p.querySelector(s);
const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
const esc = s => { if (!s) return ''; const d = document.createElement('div'); d.textContent = String(s); return d.innerHTML; };
const fmtDur = ms => { if (ms == null || isNaN(ms)) return '--'; const s = Math.round(ms/1000); return `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`; };
const fmtDur2 = ms => { const s = Math.round(ms/1000); return `${String(Math.floor(s/60)).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`; };
const fmtT = ms => { const t = ms/1000; return `${String(Math.floor(t/60)).padStart(2,'0')}:${t%60 < 10 ? '0' : ''}${(t%60).toFixed(1)}`; };
const fmtSize = b => { if (!b) return '--'; if (b > 1073741824) return (b/1073741824).toFixed(1)+'GB'; if (b > 1048576) return (b/1048576).toFixed(1)+'MB'; return (b/1024).toFixed(0)+'KB'; };
const stem = n => (n || '未命名').replace(/\.[^.]+$/, '');
const svg = (path, w=16, h=16) => `<svg width="${w}" height="${h}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${path}</svg>`;

const I = {
  check: '<path d="M20 6 9 17l-5-5"/>',
  checkFat: '<path d="M20 6 9 17l-5-5"/>',
  spark: '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/>',
  arrowR: '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
  arrowL: '<path d="m15 18-6-6 6-6"/>',
  chart: '<path d="M3 3v16h16"/><path d="m7 13 4-4 4 3 5-6"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
  smile: '<circle cx="12" cy="12" r="9"/><path d="M8 14s1.5 2.2 4 2.2S16 14 16 14"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/>',
  music: '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
  sliders: '<path d="M4 21v-7"/><path d="M4 10V3"/><path d="M12 21v-9"/><path d="M12 8V3"/><path d="M20 21v-5"/><path d="M20 12V3"/><path d="M1 14h6"/><path d="M9 8h6"/><path d="M17 16h6"/>',
  wave: '<path d="M2 12h3l2-7 4 14 3-9 2 2h6"/>',
  done: '<path d="M21.8 10A10 10 0 1 0 12 21.8"/><path d="M9 11l3 3L22 4"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/>',
  film: '<rect x="2" y="4" width="6" height="16" rx="1.5"/><rect x="10" y="4" width="6" height="16" rx="1.5"/><path d="m18.5 8 3-2v12l-3-2"/>',
  refresh: '<path d="M21.5 12a9.5 9.5 0 1 1-2.77-6.7"/><path d="M21 3v5h-5"/>',
  regen: '<path d="M3 12a9 9 0 0 1 15.3-6.4L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15.3 6.4L3 16"/><path d="M3 21v-5h5"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/><path d="M12 15V3"/>',
  scissors: '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><line x1="20" y1="4" x2="8.12" y2="15.88"/><line x1="14.47" y1="14.48" x2="20" y2="20"/><line x1="8.12" y1="8.12" x2="12" y2="12"/>',
  trash: '<path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
  up: '<path d="m18 15-6-6-6 6"/>',
  down: '<path d="m6 9 6 6 6-6"/>',
  x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  undo: '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>',
  swapH: '<path d="M4 12h16"/><path d="m8 8-4 4 4 4"/><path d="m16 8 4 4-4 4"/>',
  type: '<path d="M4 7V5h16v2"/><path d="M12 5v14"/><path d="M9 19h6"/>',
  share: '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.6" y1="10.5" x2="15.4" y2="6.5"/><line x1="8.6" y1="13.5" x2="15.4" y2="17.5"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/>',
  plus: '<path d="M12 5v14"/><path d="M5 12h14"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06.06a2 2 0 0 1 2.83 2.83l-.06-.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
  play: '<polygon points="6 3 20 12 6 21"/>',
  playBig: '<polygon points="7 4 21 12 7 20"/>',
  pauseBig: '<rect x="6" y="4" width="4.5" height="16" rx="1.4"/><rect x="13.5" y="4" width="4.5" height="16" rx="1.4"/>',
  transDissolve: '<circle cx="12" cy="12" r="6" fill="currentColor" stroke="none" opacity=".22"/><circle cx="12" cy="12" r="6"/>',
  transDissolveS: '<circle cx="12" cy="12" r="6"/>',
  transPush: '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
  transIris: '<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M4 12h8l8-8"/>',
  transFlash: '<circle cx="12" cy="12" r="4" fill="currentColor" stroke="none"/><path d="M12 2v3"/><path d="M12 19v3"/><path d="M2 12h3"/><path d="M19 12h3"/>',
  transNone: '<path d="M17.5 3H21v3.5"/><path d="M15 5 19 9"/><path d="M6.5 21H3v-3.5"/><path d="M9 19l-4-4"/><path d="M21 17.5V21h-3.5"/><path d="M19 15l-4 4"/><path d="M3 6.5V3h3.5"/><path d="M5 9l4-4"/>',
  wx: '<path d="M21 11.5a8.4 8.4 0 0 1-8.5 8.4 9 9 0 0 1-3.8-.8L3 21l1.9-4.6a8.2 8.2 0 0 1-1.4-4.9 8.4 8.4 0 0 1 8.5-8.4 8.4 8.4 0 0 1 8.5 8.4Z"/><path d="M8.5 10.5h.01"/><path d="M12 10.5h.01"/><path d="M15.5 10.5h.01"/>',
  pyq: '<circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 1 0 18"/><circle cx="12" cy="8" r="2.4"/><circle cx="8.4" cy="14" r="2.4"/><circle cx="15.6" cy="14" r="2.4"/>',
  xhs: '<rect x="3" y="3" width="18" height="18" rx="4.5"/><path d="M8 16c2.5-4 5.5-8 8-8"/><path d="M10 9.5c2 1.5 4 4 5.5 6.5"/>',
};
const svgFill = (path, w=16, h=16) => `<svg width="${w}" height="${h}" viewBox="0 0 24 24" fill="currentColor">${path}</svg>`;

function toast(msg, isError) {
  const t = $('#toast'); t.textContent = msg; t.className = 'toast show' + (isError ? ' error' : '');
  setTimeout(() => t.className = 'toast', 2500);
}

async function api(path, opts = {}) {
  const tok = localStorage.getItem('sj_token');
  if (tok) opts.headers = { ...(opts.headers || {}), 'Authorization': 'Bearer ' + tok };
  const res = await fetch(API + path, opts);
  if (res.status === 401 && !path.startsWith('/auth/')) {
    localStorage.removeItem('sj_token'); localStorage.removeItem('sj_user');
    if ((location.hash || '#/') !== '#/login') { toast('请先登录', true); goHash('#/login'); }
    throw new Error('请先登录');
  }
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try { const j = await res.json(); msg = j.detail || msg; } catch {}
    throw new Error(msg);
  }
  const ct = res.headers.get('content-type');
  return ct && ct.includes('json') ? res.json() : res.text();
}

function clearPolls() { Object.values(pollTimers).forEach(t => { clearTimeout(t); clearInterval(t); }); pollTimers = {}; }
function render(html, theme, keepScroll) {
  const a = $('#app');
  a.className = theme === 'dark' ? 'theme-dark' : '';
  a.innerHTML = html;
  if (!document.getElementById('buildBadge')) {
    const b = el('div'); b.id = 'buildBadge'; b.textContent = BUILD;
    document.body.appendChild(b);
  }
  if (!keepScroll) window.scrollTo(0, 0);
}
function showSheet(html) { $('#genSheet').innerHTML = html; $('#genSheet').classList.add('show'); $('#sheetMask').classList.add('show'); }
function hideSheet() { $('#genSheet').classList.remove('show'); $('#sheetMask').classList.remove('show'); }
$('#sheetMask').addEventListener('click', hideSheet);

// ===== 返回上下文：从哪进来就回哪去（作品页进的项目/成片，返回回作品页） =====
let _backCtx = null;   // {hash}，被消费或进入剪辑主流程时清空
function setBackCtx(hash) { _backCtx = hash ? { hash } : null; }
function backOr(fallbackCall) {
  if (_backCtx) { const h = _backCtx.hash; _backCtx = null; goHash(h); }
  else fallbackCall();
}

// ===== Hash 路由（刷新保持页面） =====
let _navGuard = false;
function nav(hash) { _navGuard = true; location.hash = hash; setTimeout(() => _navGuard = false, 50); }   // 页面函数内部已自行渲染，只改地址
function goHash(hash) {   // onclick 直达导航：交给 hashchange → route()
  if (location.hash === hash) route();
  else location.hash = hash;
}
window.addEventListener('hashchange', () => { if (!_navGuard) route(); });
function route() {
  clearPolls(); hideSheet(); stopMusic();
  const h = location.hash || '#/';
  const logged = !!localStorage.getItem('sj_token');
  if (!logged && h !== '#/login') { goLogin(); return; }
  if (logged && h === '#/login') { goProjects(false); return; }
  if (h === '#/login') { renderLoginPage(); return; }
  const wf = h.match(/^#\/works\/(\d+)/);
  if (wf) { goWorksFolder(+wf[1], false); return; }
  if (h === '#/works') { goWorks(false); return; }
  if (h === '#/me') { goMe(false); return; }
  const m = h.match(/^#\/(project|analyze|preview|editor|export|settings)(?:\/(\d+))?(?:\/(\d+))?/);
  if (!m) { goProjects(false); return; }
  const [, page, a, b] = m;
  if (page === 'settings') goSettings(false);
  else if (page === 'project' && a) goProject(+a, false);
  else if (page === 'analyze' && a) goAnalyze(+a, false);
  else if (page === 'preview' && a) goPreview(+a, b ? +b : null, false);
  else if (page === 'editor' && a) goEditor(+a, false);
  else if (page === 'export' && a) goExport(+a, b ? +b : null, false);
  else goProjects(false);
}

// ===== 顶栏 =====
function topbar(title, backLabel, backFn, rightHtml = '') {
  return `<div class="topbar">
    <button class="back-btn" onclick="${backFn}">${svg(I.arrowL,17,17)}${backLabel}</button>
    <div class="topbar-title">${title}</div>
    ${rightHtml}
  </div>`;
}
function topbarHome() {
  return `<div class="topbar">
    <div class="logo"><span class="logo-mark">${svg('<path d="M6 3v12"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="6" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/><path d="M20.5 4.5 18 6"/>',15,15)}</span><span class="logo-name">闪剪<em>AI</em></span></div>
  </div>`;
}

// ===== 底部 Tab 导航（仅首页/作品/我的三个顶层页显示） =====
function renderTabBar(active) {
  const bar = el('nav', 'tabbar');
  bar.innerHTML = `
    <button class="tab-item ${active === 'home' ? 'active' : ''}" onclick="goProjects()">
      ${svg('<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/><path d="M9 22V12h6v10"/>',22,22)}<span>首页</span>
    </button>
    <button class="tab-item ${active === 'works' ? 'active' : ''}" onclick="goWorks()">
      ${svg(I.film,22,22)}<span>作品</span>
    </button>
    <button class="tab-item ${active === 'me' ? 'active' : ''}" onclick="goMe()">
      ${svg('<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',22,22)}<span>我的</span>
    </button>`;
  $('#app').appendChild(bar);
}

// ===== 作品库（项目文件夹形式） =====
async function goWorks(withNav = true) {
  if (withNav) nav('#/works');
  setBackCtx(null);
  clearPolls(); stopMusic();
  render(topbarHome() + `<main class="page-body pb-tab" id="worksPage"><div style="text-align:center;padding:40px"><div class="spinner" style="margin:0 auto"></div></div></main>`);
  try {
    const data = await api('/projects');
    const page = $('#worksPage'); if (!page) return;
    const projects = (data.projects || [])
      .filter(p => p.exports && p.exports.length)
      .sort((a, b) => ((b.exports[0] && b.exports[0].createdAt) || '').localeCompare((a.exports[0] && a.exports[0].createdAt) || ''));
    const total = projects.reduce((s, p) => s + p.exports.length, 0);
    let html = `<div class="sec-head"><h2>我的作品<small>${projects.length} 个项目 · ${total} 个成片</small></h2></div>`;
    if (!projects.length) {
      html += '<div class="empty-state"><div class="icon">🎬</div><div>还没有成片<br>回首页上传素材开始创作</div></div>';
    } else {
      html += projects.map(p => `
      <section class="card anim">
        <div class="work-proj" onclick="goHash('#/works/${p.projectId}')">
          <div class="recent-cover">${p.coverUrl ? `<img src="${p.coverUrl}">` : '<div class="recent-cover-empty">🎬</div>'}</div>
          <div class="recent-main">
            <div class="recent-name">${esc(p.title)}</div>
            <div class="recent-meta">${p.exports.length} 个成片 · 最近 ${(p.exports[0].createdAt || '').slice(5,16)}</div>
          </div>
          ${svg('<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',20,20).replace('<svg ', '<svg style="color:#C7CBD2;flex-shrink:0" ')}
        </div>
      </section>`).join('');
    }
    page.innerHTML = html;
    renderTabBar('works');
  } catch(e) { toast(e.message, true); }
}

// ===== 作品文件夹：某个项目的成片列表 =====
async function goWorksFolder(pid, withNav = true) {
  if (withNav) nav(`#/works/${pid}`);
  clearPolls(); stopMusic();
  render(topbar('成片', '作品', 'goWorks()') + `<main class="page-body pb-tab" id="workFolder"><div style="text-align:center;padding:40px"><div class="spinner" style="margin:0 auto"></div></div></main>`);
  try {
    const [proj, expData] = await Promise.all([
      api(`/projects/${pid}`), api(`/projects/${pid}/exports`)]);
    const page = $('#workFolder'); if (!page) return;
    const exps = expData.exports || [];
    let html = `<div class="sec-head"><h2>${esc(proj.title)}<small>${exps.length} 个成片</small></h2><span style="font-size:11px;color:var(--ink-3)">点成片预览 · 点 × 删除</span></div>`;
    if (!exps.length) {
      html += '<div class="empty-state"><div class="icon">🎬</div><div>该项目还没有成片</div></div>';
    } else {
      html += exps.map(e => `
        <div class="work-ver" onclick="goPreview(${pid}, ${e.version}, true, 'folder')">
          <span class="wv-badge">v${e.version}</span>
          <span class="wv-spec">${e.resolution || '--'} · ${e.fps || 30}fps · ${fmtSize(e.sizeBytes)} · ${(e.createdAt || '').slice(5,16)}</span>
          <span class="wv-play">${svgFill(I.play,12,12)}</span>
          <button class="ver-del" title="删除这个成片" onclick="event.stopPropagation();delExport(${pid}, ${e.version})">${svg(I.x,12,12)}</button>
        </div>`).join('');
    }
    html += `<button class="btn-sub" style="width:100%;margin-top:18px" onclick="delProjectFromWorks(${pid})">${svg(I.trash,14,14)} 删除整个项目（含素材）</button>`;
    page.innerHTML = html;
    renderTabBar('works');
  } catch(e) { toast(e.message, true); goWorks(false); }
}
window.delExport = async (pid, version) => {
  if (!confirm(`删除成片 v${version}？文件会一起删除。`)) return;
  try {
    await api(`/projects/${pid}/exports/${version}`, { method: 'DELETE' });
    toast(`已删除成片 v${version}`);
    goWorksFolder(pid);
  } catch(e) { toast(e.message, true); }
};
window.delProjectFromWorks = async pid => {
  if (!confirm('删除整个项目？素材与全部成片会一起删除。')) return;
  try {
    await api(`/projects/${pid}`, { method: 'DELETE' });
    toast('项目已删除');
    goHash('#/works');
  } catch(e) { toast(e.message, true); }
};

// ===== 我的 =====
async function goMe(withNav = true) {
  if (withNav) nav('#/me');
  setBackCtx(null);
  clearPolls(); stopMusic();
  render(topbarHome() + `<main class="page-body pb-tab" id="mePage"><div style="text-align:center;padding:40px"><div class="spinner" style="margin:0 auto"></div></div></main>`);
  try {
    const data = await api('/projects');
    const page = $('#mePage'); if (!page) return;
    const uname = localStorage.getItem('sj_user') || '';
    const nProj = data.projects.length;
    const nWorks = data.projects.reduce((s, p) => s + ((p.exports && p.exports.length) || 0), 0);
    page.innerHTML = `
      <section class="card anim" style="display:flex;align-items:center;gap:14px;padding:18px 16px">
        <div class="me-avatar">${esc((uname[0] || '闪').toUpperCase())}</div>
        <div style="flex:1;min-width:0">
          <div style="font-size:17px;font-weight:700">${esc(uname)}</div>
          <div style="font-size:12px;color:var(--ink-3);margin-top:4px">${nProj} 个项目 · ${nWorks} 个成片</div>
        </div>
      </section>
      <section class="card anim d1">
        <div class="me-row" onclick="goHash('#/settings')">
          <span class="mr-ico">${svg(I.gear,16,16)}</span>
          <span style="flex:1;min-width:0"><span class="mr-name">AI 模型设置</span><span class="mr-sub" style="display:block">模型与密钥跟着你的账号走</span></span>
          ${svg('<path d="m9 18 6-6-6-6"/>',16,16).replace('<svg ', '<svg class="chev" ')}
        </div>
      </section>
      <button class="btn-sub anim d2" style="width:100%;margin-top:6px" onclick="doLogout()">
        ${svg('<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>',15,15)} 退出登录
      </button>
      <div style="text-align:center;font-size:11px;color:var(--ink-3);margin-top:14px">闪剪 AI · 页面 ${BUILD}</div>`;
    renderTabBar('me');
  } catch(e) { toast(e.message, true); }
}

// ============================================================
// 登录 / 注册
// ============================================================
let _loginMode = 'login';
function goLogin(withNav = true) {
  if (withNav) nav('#/login');
  clearPolls(); stopMusic(); hideSheet();
  _loginMode = 'login';
  renderLoginPage();
}
function renderLoginPage() {
  const reg = _loginMode === 'register';
  render(`<div class="topbar"><div class="logo"><span class="logo-mark">${svg('<path d="M6 3v12"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="6" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/><path d="M20.5 4.5 18 6"/>',15,15)}</span><span class="logo-name">闪剪<em>AI</em></span></div></div>
    <main class="page-body" style="display:flex;flex-direction:column;justify-content:center;min-height:calc(100vh - 52px)">
      <section class="card anim" style="padding:24px 20px;width:100%;max-width:340px;margin:0 auto">
        <div style="text-align:center;margin-bottom:20px">
          <div style="width:58px;height:58px;border-radius:15px;background:var(--brand);color:#fff;display:flex;align-items:center;justify-content:center;margin:0 auto 12px">${svg(I.spark,30,30)}</div>
          <div style="font-size:20px;font-weight:700">${reg ? '创建账号' : '欢迎回来'}</div>
          <div style="font-size:12px;color:var(--ink-3);margin-top:5px">${reg ? '注册后你的素材、项目与成片独立存放' : '各账号数据互相独立，登录后继续创作'}</div>
        </div>
        <input class="login-input" id="lgName" placeholder="用户名" maxlength="24" autocomplete="username">
        <input class="login-input" id="lgPass" type="password" placeholder="密码（至少 6 位）" autocomplete="current-password">
        <button class="btn-main" style="width:100%;margin-top:6px" id="lgBtn" onclick="doLogin()">${reg ? '注 册' : '登 录'}</button>
        <button style="display:block;margin:14px auto 0;background:none;border:none;color:var(--ink-3);font-size:13px;cursor:pointer;padding:6px 10px" onclick="toggleLoginMode()">${reg ? '已有账号？去登录' : '没有账号？注册一个'}</button>
      </section>
    </main>`);
}
window.toggleLoginMode = () => { _loginMode = _loginMode === 'login' ? 'register' : 'login'; renderLoginPage(); };
window.doLogin = async () => {
  const name = ($('#lgName').value || '').trim();
  const pass = $('#lgPass').value || '';
  if (!name) { toast('请输入用户名', true); return; }
  if (pass.length < 6) { toast('密码至少 6 位', true); return; }
  const btn = $('#lgBtn'); btn.disabled = true; btn.textContent = '请稍候…';
  try {
    const r = await api('/auth/' + (_loginMode === 'register' ? 'register' : 'login'), {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, password: pass })
    });
    localStorage.setItem('sj_token', r.token);
    localStorage.setItem('sj_user', r.user.name);
    toast((_loginMode === 'register' ? '注册成功，欢迎' : '欢迎回来') + '，' + r.user.name);
    goHash('#/');
  } catch(e) { toast(e.message, true); }
  btn.disabled = false; btn.textContent = _loginMode === 'register' ? '注 册' : '登 录';
};
window.doLogout = async () => {
  try { await api('/auth/logout', { method: 'POST' }); } catch {}
  localStorage.removeItem('sj_token'); localStorage.removeItem('sj_user');
  toast('已退出登录');
  goHash('#/login');
};

// ============================================================
// 页面 1 · 首页（素材导入 + 最近项目）
// ============================================================
async function goProjects(withNav = true) {
  if (withNav) nav('#/');
  setBackCtx(null);
  clearPolls(); stopMusic();
  let modelBadge = '';
  try {
    const mc = await api('/settings/model');
    const cur = mc.models.find(m => m.current);
    if (cur) {
      const ok = cur.verified;
      modelBadge = `<button onclick="goHash('#/settings')" style="display:inline-flex;align-items:center;gap:5px;font-size:11px;color:${ok ? 'var(--green)' : '#979CA6'};background:${ok ? 'var(--green-bg)' : '#F2F3F5'};border:none;border-radius:4px;padding:4px 8px;cursor:pointer;margin-top:10px">${svg('<path d="M12 2v4"/><path d="M12 18v4"/><path d="m4.93 4.93 2.83 2.83"/><path d="m16.24 16.24 2.83 2.83"/><path d="M2 12h4"/><path d="M18 12h4"/><path d="m4.93 19.07 2.83-2.83"/><path d="m16.24 7.76 2.83-2.83"/>',11,11)}${esc(cur.name)} · ${ok ? '已验证' : cur.configured ? '密钥未验证' : '未配置'}</button>`;
    }
  } catch {}
  const hr = new Date().getHours();
  const greet = hr < 6 ? '夜深了' : hr < 12 ? '上午好' : hr < 18 ? '下午好' : '晚上好';
  const uname = localStorage.getItem('sj_user') || '';
  render(topbarHome() + `
    <main class="page-body pb-tab">
      <div class="hello anim">
        <h1>${uname ? `${greet}，<span>${esc(uname)}</span>` : `${greet}，该剪片了`}</h1>
        <p>把相册里的碎片素材交给 AI，几分钟出一支能发朋友圈的片子。${modelBadge}</p>
      </div>
      <section class="ai-entry anim d1">
        <div class="ai-entry-head">
          <span class="ai-entry-icon">${svg(I.spark,22,22)}</span>
          <div>
            <div class="ai-entry-title">AI 一键成片</div>
            <div class="ai-entry-desc">自动分析画面场景与节奏，配好音乐、剪好片段</div>
          </div>
        </div>
        <div class="ai-entry-tags">
          <span class="ai-tag">${svg(I.check,11,11)}场景识别</span>
          <span class="ai-tag">${svg(I.check,11,11)}智能配乐</span>
          <span class="ai-tag">${svg(I.check,11,11)}自动转场</span>
          <span class="ai-tag">${svg(I.check,11,11)}节拍对齐</span>
        </div>
        <button class="ai-entry-btn" onclick="$('#fileInput').click()">
          导入素材，交给 AI
          <span class="arr">立即开始 ${svg(I.arrowR,14,14)}</span>
        </button>
      </section>
      <input type="file" id="fileInput" accept="video/*" multiple>
      <div id="uploadContainer"></div>
      <section class="anim d2" id="projSection">
        <div class="sec-head">
          <h2>最近项目</h2>
          <button class="sec-link" onclick="loadProjects()">刷新</button>
        </div>
        <div id="projList"><div style="text-align:center;padding:20px"><div class="spinner" style="margin:0 auto"></div></div></div>
      </section>
    </main>
  `);
  renderTabBar('home');
  $('#fileInput').onchange = handleUpload;
  await loadProjects();
}

async function loadProjects() {
  try {
    const data = await api('/projects');
    const list = $('#projList');
    if (!list) return;
    if (!data.projects.length) {
      list.innerHTML = '<div class="empty-state"><div class="icon">🎬</div><div>还没有项目<br>上传视频开始创作</div></div>';
      return;
    }
    list.innerHTML = '<div class="recent-list">' + data.projects.map(p => {
      const totalMs = p.totalDurationMs || 0;
      const hasExport = p.exports && p.exports.length > 0;
      return `<div class="recent-item-wrap" data-pid="${p.projectId}">
        <div class="recent-item" onclick="goProject(${p.projectId})" data-pid="${p.projectId}">
          <div class="recent-cover">${p.coverUrl ? `<img src="${p.coverUrl}">` : '<div class="recent-cover-empty">🎬</div>'}</div>
          <div class="recent-main">
            <div class="recent-name">${esc(p.title)}</div>
            <div class="recent-meta">${p.assetCount} 段 · ${fmtDur(totalMs)}${hasExport ? ' · ' + p.exports.length + ' 个成片' : ''}</div>
          </div>
          <span class="state-chip ${hasExport ? 'done' : 'draft'}">${hasExport ? '已导出' : '草稿'}</span>
        </div>
        <button class="recent-delete" onclick="deleteProject(${p.projectId})">${svg(I.trash,14,14)}删除</button>
      </div>`;
    }).join('') + '</div>';
    bindSwipe();
  } catch(e) { toast(e.message, true); }
}

// ===== 滑动删除 =====
function bindSwipe() {
  document.querySelectorAll('.recent-item').forEach(item => {
    let startX = 0, currentX = 0, isOpen = false;
    const closeAll = () => {
      document.querySelectorAll('.recent-item.sliding').forEach(e => { e.style.transform = ''; e.classList.remove('sliding'); });
    };
    item.addEventListener('touchstart', e => {
      if (e.touches.length > 1) return;
      if (e.target.closest('.recent-delete')) return;
      closeAll();
      startX = e.touches[0].clientX;
      item.classList.add('sliding');
    }, { passive: true });
    item.addEventListener('touchmove', e => {
      if (e.touches.length > 1) return;
      const dx = e.touches[0].clientX - startX;
      const base = isOpen ? -76 : 0;
      currentX = Math.min(0, Math.max(-80, base + dx));
      item.style.transform = `translateX(${currentX}px)`;
    }, { passive: true });
    item.addEventListener('touchend', () => {
      isOpen = currentX < -38;
      item.style.transform = isOpen ? 'translateX(-76px)' : '';
      if (!isOpen) item.classList.remove('sliding');
    });
  });
}

async function deleteProject(pid) {
  if (!confirm('确认删除项目？所有素材和成片文件都会一起删除。')) return;
  try {
    await api(`/projects/${pid}`, { method: 'DELETE' });
    toast('已删除');
    loadProjects();
  } catch(e) { toast(e.message, true); }
}

// ===== 上传 =====
async function handleUpload(e) {
  const files = [...e.target.files];
  if (!files.length) return;
  e.target.value = '';
  const container = $('#uploadContainer');
  let projectId = null;
  for (const f of files) {
    const wrap = el('div', 'upload-progress anim');
    wrap.innerHTML = `
      <div class="file-name">${esc(f.name)}</div>
      <div class="file-meta">${fmtSize(f.size)}</div>
      <div class="bar"><div class="fill" style="width:0%"></div></div>
      <div class="pct">0%</div>`;
    container.prepend(wrap);
    await new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const fd = new FormData();
      fd.append('file', f);
      fd.append('title', f.name.replace(/\.[^.]+$/, ''));
      if (projectId) fd.append('projectId', projectId);
      xhr.upload.addEventListener('progress', ev => {
        if (ev.lengthComputable) {
          const pct = Math.round(ev.loaded / ev.total * 100);
          wrap.querySelector('.fill').style.width = pct + '%';
          wrap.querySelector('.pct').textContent = pct + '%';
        }
      });
      xhr.addEventListener('load', () => {
        try {
          const r = JSON.parse(xhr.responseText);
          if (r.projectId) projectId = r.projectId;
          wrap.querySelector('.fill').style.width = '100%';
          wrap.querySelector('.pct').textContent = '完成';
          wrap.style.opacity = '0.6';
          resolve(r);
        } catch(err) { reject(err); }
      });
      xhr.addEventListener('error', () => reject(new Error('网络错误')));
      xhr.open('POST', API + '/upload');
      const tok = localStorage.getItem('sj_token');
      if (tok) xhr.setRequestHeader('Authorization', 'Bearer ' + tok);
      xhr.send(fd);
    }).catch(err => { toast(err.message, true); });
  }
  toast('上传完成');
  setTimeout(() => { if (projectId) goProject(projectId); }, 500);
}

// ============================================================
// 页面 1.5 · 项目素材页（原型「首页 · 素材导入」的素材区）
// ============================================================
async function goProject(id, withNav = true, from = null) {
  if (withNav) nav(`#/project/${id}`);
  setBackCtx(from === 'works' ? '#/works' : null);
  clearPolls(); stopMusic();
  loadProject._sig = null;
  render(topbar('素材', '首页', 'backOr(() => goProjects())') + `<main class="page-body" id="projDetail"><div style="text-align:center;padding:40px"><div class="spinner" style="margin:0 auto"></div></div></main>`);
  await loadProject(id);
}

// ===== 「参与成片」勾选状态：项目页与分析页共用一份（跨页面保留） =====
function cutSelFor(pid) {
  if (!window._cutSel || window._cutSel.pid !== pid) window._cutSel = { pid, off: new Set() };
  return window._cutSel;
}

async function loadProject(id) {
  try {
    const p = await api(`/projects/${id}`);
    const hasAssets = p.assets && p.assets.length > 0;
    const allReady = hasAssets && p.assets.every(a => a.probeStatus === 1);
    const anyPending = hasAssets && p.assets.some(a => a.probeStatus === 0);
    // 素材解析轮询：状态签名没变就不重建 DOM（避免每次轮询闪一下）
    const sig = JSON.stringify([id, hasAssets ? p.assets.map(a => a.probeStatus) : [], (p.exports || []).map(e => e.version)]);
    if (loadProject._sig === sig && $('#projDetail') !== null) {
      if (anyPending) pollTimers.probe = setTimeout(() => loadProject(id), 2500);
      return;
    }
    loadProject._sig = sig;
    const totalMs = hasAssets ? p.assets.reduce((s,a)=>s+(a.durationMs||0),0) : 0;
    const bestId = hasAssets ? p.assets.reduce((b,a) => (a.qualityScore||0) > (b.qualityScore||0) ? a : b, p.assets[0]).assetId : null;

    let html = '';
    let selTotalMs = totalMs;
    let selCount = hasAssets ? p.assets.length : 0;
    if (hasAssets) {
      // 「参与成片」勾选（与分析页共用）：off = 已取消勾选
      const selS = cutSelFor(id);
      const validIds = new Set(p.assets.map(a => a.assetId));
      selS.off = new Set([...selS.off].filter(x => validIds.has(x)));
      window._projCache = p;
      selCount = p.assets.length - selS.off.size;
      selTotalMs = p.assets.filter(a => !selS.off.has(a.assetId)).reduce((s,a)=>s+(a.durationMs||0),0);

      html += `<section class="anim"><div class="sec-head">
        <h2>本次素材<small id="projSelSmall">已选 ${selCount} / ${p.assets.length} 段 · 点卡片切换勾选</small></h2>
        <button class="sec-link" onclick="$('#moreFiles').click()">添加</button>
      </div>
      <div class="media-grid">`;
      p.assets.forEach((a, idx) => {
        const off = selS.off.has(a.assetId) ? ' off' : '';
        const flag = a.assetId === bestId && a.qualityGood ? '<span class="media-flag">AI 推荐</span>'
                   : a.qualityGood ? '<span class="media-flag plain">画质佳</span>' : '';
        html += `<div class="media-card${off}" data-aid="${a.assetId}">
          <div class="media-cover">${a.thumbUrl ? `<img src="${a.thumbUrl}">` : ''}
            ${flag}
            <span class="media-pick" title="素材序号（提示词里可用「第${idx+1}段」指代）">${idx+1}</span>
            <button class="media-remove" title="移除这段素材" onclick="removeAsset(${id}, ${a.assetId}, '${esc(a.fileName || '').replace(/'/g, "\\'")}')">${svg(I.x,11,11)}</button>
            <span class="media-dur">${fmtDur2(a.durationMs)}</span>
          </div>
          <div class="media-info">
            <div class="media-name">${esc(a.fileName || '未命名')}</div>
            <div class="media-meta">${[a.shotAt ? esc(a.shotAt.slice(5,16)) : '', a.resolution ? (a.resolution.includes('2160') ? '4K' : a.resolution.includes('1080') ? '1080P' : a.resolution) : ''].filter(Boolean).join(' · ')}</div>
          </div>
        </div>`;
      });
      html += `</div></section>`;
      html += `<input type="file" id="moreFiles" accept="video/*" multiple style="display:none">`;
      if (anyPending) html += `<div style="text-align:center;color:var(--amber);font-size:13px;margin:14px 0 4px">部分素材解析中…</div>`;
    }

    // 成片版本列表
    if (p.exports && p.exports.length) {
      html += `<section class="anim d2" style="margin-top:24px"><div class="sec-head"><h2>成片列表</h2><span style="font-size:11px;color:var(--ink-3)">点击预览</span></div>`;
      for (const e of p.exports) {
        html += `<div class="ver-item" onclick="goPreview(${id}, ${e.version}, true, 'project')">
          <div class="ver-play">${p.assets && p.assets[0] && p.assets[0].thumbUrl ? `<img src="${p.assets[0].thumbUrl}">` : ''}${svgFill(I.play,24,24)}</div>
          <div style="flex:1;min-width:0">
            <b style="font-size:14px">成片 v${e.version}</b>
            <div style="font-size:11px;color:var(--ink-3);margin-top:3px">${e.resolution || '--'} · ${fmtSize(e.sizeBytes)} · ${(e.createdAt||'').slice(5,16)}</div>
          </div>
          <span class="state-chip done">已导出</span>
        </div>`;
      }
      html += '</section>';
    }

    const estMs = Math.round(selTotalMs * 0.6 / 1000) * 1000;
    render(topbar(esc(p.title), '首页', 'backOr(() => goProjects())') + `<main class="page-body">${html}</main>
      <footer class="action-bar">
        <div class="picked-sum">
          <b id="pickedCount">已选 ${selCount} / ${p.assets ? p.assets.length : 0} 段素材</b>
          <span id="pickedMeta">共 ${fmtDur(selTotalMs)}${selTotalMs ? ` · 预计成片 ${fmtDur(estMs)}` : ''}</span>
        </div>
        ${allReady && selCount > 0
          ? `<button class="btn-main fix" id="projAnalyzeBtn" onclick="goAnalyze(${id})">开始 AI 分析${svg(I.arrowR,15,15)}</button>`
          : allReady
            ? `<button class="btn-main fix" disabled>至少勾选一段素材</button>`
            : `<button class="btn-main fix" disabled>解析中…</button>`}
      </footer>`, null, true);
    if (hasAssets) bindTapEls($('#app'), '.media-card', node => anToggleAsset(+node.dataset.aid));

    const mf = $('#moreFiles');
    if (mf) mf.onchange = async (e) => {
      const files = [...e.target.files];
      for (const f of files) {
        const fd = new FormData(); fd.append('file', f); fd.append('projectId', id);
        toast(`上传: ${f.name}...`);
        await api('/upload', { method: 'POST', body: fd });
      }
      toast('上传完成');
      loadProject(id);
    };
    if (anyPending) pollTimers.probe = setTimeout(() => loadProject(id), 2500);
  } catch(e) { toast(e.message, true); }
}

// ===== 单段素材移除 =====
window.removeAsset = async (pid, aid, name) => {
  if (!confirm(`移除「${name || '这段素材'}」？原文件会一起删除。`)) return;
  try {
    await api(`/projects/${pid}/assets/${aid}`, { method: 'DELETE' });
    toast('已移除');
    loadProject._sig = null;
    loadProject(pid);
  } catch(e) {
    toast(/HTTP 4\d\d/.test(e.message) ? '移除失败：请重启电脑端服务（新接口需重启生效）' : e.message, true);
  }
};

// ============================================================
// 页面 2 · AI 分析与音乐匹配
// ============================================================
let anState = null; // {pid, report, project, candidates, selectedMusic, refresh, t0}

async function goAnalyze(pid, withNav = true) {
  if (withNav) nav(`#/analyze/${pid}`);
  setBackCtx(null);   // 进入剪辑主流程，返回不再回作品页
  clearPolls(); stopMusic();
  render(topbar('AI 分析与配乐', '素材', `goProject(${pid})`) +
    `<main class="page-body pb-analysis" id="analyzePage"><div style="text-align:center;padding:40px"><div class="spinner" style="margin:0 auto"></div></div></main>`);
  anState = { pid, report: null, project: null, candidates: [], selectedMusic: null, refresh: 0, t0: 0, prompt: '', off: cutSelFor(pid).off };
  try {
    anState.project = await api(`/projects/${pid}`);
    const data = await api(`/projects/${pid}/analysis`);
    if (data.report) {
      anState.report = data.report;
      await loadMusic();
      renderAnalyze();
    } else if (data.job && (data.job.status === 'queued' || data.job.status === 'running')) {
      renderAnalyzeProgress(data.job);
      pollAnalysis(pid);
    } else {
      // 先让用户勾素材、写提示词，再开始分析
      renderAnalyzeIntro();
    }
  } catch(e) { toast(e.message, true); }
}

// 分析前置页：素材清单（可勾选）+ 提示词，点「开始 AI 分析」才跑
function renderAnalyzeIntro() {
  const page = $('#analyzePage'); if (!page || !anState) return;
  const assets = anState.project.assets || [];
  page.innerHTML = `
  <section class="card anim">
    <div class="card-head"><div class="card-title"><span class="ico">${svg(I.film,13,13)}</span>本次素材</div></div>
    ${numberedStripHtml(assets, a => (a.resolution && !a.resolution.includes('1280') ? (a.resolution.includes('2160') ? '4K' : a.resolution.includes('1080') ? '1080P' : '') : ''))}
  </section>
  <section class="card anim d1">
    <div class="card-head"><div class="card-title"><span class="ico">${svg(I.edit,13,13)}</span>告诉 AI 怎么剪</div></div>
    <textarea id="aiPrompt" rows="4" style="width:100%;box-sizing:border-box;border:1px solid #E4E6EB;border-radius:8px;padding:10px;font-size:13px;resize:vertical" placeholder="例如：只用第1、3段，第2段放到结尾；节奏快一点，总长控制在40秒内">${esc(anState.prompt || '')}</textarea>
    <div style="font-size:11px;color:var(--ink-3);margin-top:6px;line-height:1.6">现在写下要求，成片前会一直保留，AI 剪辑时严格遵守；留空则按内容精彩程度自动剪</div>
  </section>`;
  bindSceneTaps(page);
  setAnalyzeBar('analyze');
}

// 底部操作栏随阶段切换：先「开始分析」，完成后「开始智能成片」
function setAnalyzeBar(mode) {
  let bar = $('#analyzeBar');
  if (!bar) {
    bar = el('footer', 'action-bar col'); bar.id = 'analyzeBar';
    $('#app').appendChild(bar);
  }
  if (mode === 'analyze') {
    bar.innerHTML = `<button class="btn-main" onclick="anStartAnalysis()">${svg(I.spark,16,16)}开始 AI 分析</button>
      <div class="gen-note">先分析场景与节奏，完成后挑配乐、调偏好，再一键成片</div>`;
  } else {
    bar.innerHTML = `<button class="btn-main" onclick="doAutoCut(${anState.pid})">${svg(I.spark,16,16)}开始智能成片</button>
      <div class="gen-note">预计 10 秒内完成 · 生成后可随意手动调整</div>`;
  }
}

function renderAnalyzeProgress(job) {
  const page = $('#analyzePage'); if (!page) return;
  const pct = Math.round((job.progress || 0) * 100);
  const msg = job.message || '分析中…';
  // 首次渲染骨架，轮询只 patch 文字与进度条，避免整卡重建导致闪烁
  if (!$('#anaProg')) {
    page.innerHTML = `
    <div class="card anim" id="anaProg">
      <div class="card-head"><div class="card-title"><span class="ico">${svg(I.chart,13,13)}</span>AI 分析中</div></div>
      <div class="steps">
        <div class="step"><span class="step-dot running"></span><div class="step-main"><div class="step-name" id="anaMsg">${esc(msg)}</div><div class="step-note">本地信号 + 视觉大模型逐段理解</div></div></div>
        <div class="step"><span class="step-dot pending"></span><div class="step-main"><div class="step-name">情绪与节奏分析</div><div class="step-note">镜头运动 + 明暗变化 + 人声检测</div></div></div>
        <div class="step"><span class="step-dot pending"></span><div class="step-main"><div class="step-name">配乐匹配</div><div class="step-note">按 BPM 与情绪从曲库挑选</div></div></div>
      </div>
      <div class="upload-progress" style="margin:14px 0 0;background:transparent;border:none;box-shadow:none;padding:0">
        <div class="bar"><div class="fill" id="anaBar" style="width:0%"></div></div>
        <div class="pct" id="anaPct">0%</div>
      </div>
    </div>`;
  }
  const m = $('#anaMsg'); if (m && m.textContent !== msg) m.textContent = msg;
  const bar = $('#anaBar'); if (bar) bar.style.width = pct + '%';
  const p = $('#anaPct'); if (p && p.textContent !== pct + '%') p.textContent = pct + '%';
}

async function pollAnalysis(pid) {
  try {
    const data = await api(`/projects/${pid}/analysis`);
    if (data.report) {
      anState.report = data.report;
      await loadMusic();
      renderAnalyze();
      return;
    }
    if (data.job && (data.job.status === 'queued' || data.job.status === 'running')) {
      renderAnalyzeProgress(data.job);
      pollTimers.analysis = setTimeout(() => pollAnalysis(pid), 2000);
      return;
    }
    if (data.job && (data.job.status === 'failed' || data.job.status === 'error')) {
      toast(data.job.error || '分析失败', true);
    }
    // 无任务无报告：回到可重新开始状态
    renderAnalyzeRetry();
  } catch(e) { toast(e.message, true); }
}

function renderAnalyzeRetry() {
  const page = $('#analyzePage'); if (!page) return;
  page.innerHTML = `
    <div class="card" style="text-align:center">
      <div class="card-title" style="justify-content:center;margin-bottom:10px"><span class="ico">${svg(I.spark,13,13)}</span>AI 分析</div>
      <p style="font-size:13px;color:var(--ink-3);margin-bottom:14px">自动识别场景、情绪与节奏，再按内容挑配乐</p>
      <button class="btn-main" onclick="anRerun()">开始 AI 分析</button>
    </div>`;
}

async function loadMusic() {
  try {
    const md = await api(`/projects/${anState.pid}/music?refresh=${anState.refresh}`);
    anState.candidates = md.candidates || [];
    if (anState.selectedMusic == null && anState.candidates.length) anState.selectedMusic = anState.candidates[0].musicId;
  } catch {}
}

window.anStartAnalysis = async () => {
  const ta = $('#aiPrompt'); if (ta) anState.prompt = ta.value.trim();
  anState.t0 = Date.now();
  try {
    await api(`/projects/${anState.pid}/analysis`, { method: 'POST' });
  } catch(e) { toast(e.message, true); return; }
  renderAnalyzeProgress({ progress: 0, message: '排队中…' });
  pollAnalysis(anState.pid);
};
window.anRerun = () => anStartAnalysis();
window.anRefreshMusic = async () => {
  anState.refresh++;
  await loadMusic();
  renderAnalyze();
};
window.anSelectMusic = mid => { anState.selectedMusic = mid; renderAnalyze(); };
window.anToggleAsset = aid => {
  const pid = anState ? anState.pid : (window._cutSel ? window._cutSel.pid : null);
  if (pid == null) return;
  const selS = cutSelFor(pid);
  selS.off.has(aid) ? selS.off.delete(aid) : selS.off.add(aid);
  if (anState && anState.pid === pid) anState.off = selS.off;
  // 两处素材卡都做 patch（项目页 + 分析页）
  const cell = document.querySelector(`.scene-cell[data-aid="${aid}"]`);
  if (cell) cell.classList.toggle('off', selS.off.has(aid));
  const card = document.querySelector(`.media-card[data-aid="${aid}"]`);
  if (card) card.classList.toggle('off', selS.off.has(aid));
  const hint = $('#anSelHint');
  if (hint && anState && anState.pid === pid && anState.project) {
    const t = anState.project.assets.length;
    hint.textContent = `已选 ${t - selS.off.size} / ${t} 段 · 点卡片切换勾选；提示词里可用「第N段」精准指定素材`;
  }
  // 项目页小标题与底栏
  const p = window._projCache;
  if (p && window._cutSel && window._cutSel.pid === p.projectId) {
    const n = p.assets.length - selS.off.size;
    const small = $('#projSelSmall');
    if (small) small.textContent = `已选 ${n} / ${p.assets.length} 段 · 点卡片切换勾选`;
    const cnt = $('#pickedCount'); if (cnt) cnt.textContent = `已选 ${n} / ${p.assets.length} 段素材`;
    const tot = p.assets.filter(a => !selS.off.has(a.assetId)).reduce((s,a)=>s+(a.durationMs||0),0);
    const meta = $('#pickedMeta'); if (meta) meta.textContent = `共 ${fmtDur(tot)}${tot ? ` · 预计成片 ${fmtDur(Math.round(tot*0.6/1000)*1000)}` : ''}`;
    const btn = $('#projAnalyzeBtn'); if (btn) btn.disabled = n === 0;
  }
};

// 场景归类（无报告时兜底为空标签）
function sceneOf(aid) {
  const ra = ((anState && anState.report && anState.report.assets) || []).find(x => x.assetId === aid) || {};
  return (ra.vlScene && ra.vlScene.scene_type) || (ra.sceneSummary && ra.sceneSummary.label) || '';
}

// 序号素材条（分析前后共用）：圆标 = 序号，点卡片切换勾选
function numberedStripHtml(assets, scFn) {
  const s = anState;
  return `
    <div class="scene-strip ${assets.length <= 6 ? 'fit' : ''}">
      ${assets.map((a, idx) => {
        const off = s.off.has(a.assetId) ? ' off' : '';
        const sc = scFn ? scFn(a) : '';
        return `<div class="scene-cell${off}" data-aid="${a.assetId}" role="button" aria-label="切换勾选">
        <div class="ph">${a.thumbUrl ? `<img src="${a.thumbUrl}" draggable="false">` : ''}<span class="scene-pick">${idx+1}</span><span class="lb">${esc(stem(a.fileName))}</span></div>
        <div class="sc">${esc(sc)}</div>
      </div>`;
      }).join('')}
    </div>
    <div style="font-size:11px;color:var(--ink-3);margin-top:10px" id="anSelHint">已选 ${assets.length - s.off.size} / ${assets.length} 段 · 点卡片切换勾选；提示词里可用「第N段」精准指定素材</div>`;
}
// 通用触屏点击绑定：真人手指轻按会微移，阈值放宽到 30px / 0.8s，避免被当成滑动丢弃
function bindTapEls(root, selector, fire) {
  let lastTouch = 0;
  root.querySelectorAll(selector).forEach(node => {
    const fn = () => fire(node);
    node.addEventListener('click', e => {
      if (node.contains(e.target.closest('.media-remove'))) return;   // × 移除按钮不冒泡处理
      if (Date.now() - lastTouch < 700) return;
      fn();
    });
    let ts = null;
    node.addEventListener('touchstart', e => {
      const t = e.touches[0];
      ts = { x: t.clientX, y: t.clientY, t: Date.now() };
    }, { passive: true });
    node.addEventListener('touchend', e => {
      if (!ts) return;
      if (e.target.closest && e.target.closest('.media-remove')) { ts = null; return; }
      const t = e.changedTouches[0];
      const moved = Math.max(Math.abs(t.clientX - ts.x), Math.abs(t.clientY - ts.y));
      const dur = Date.now() - ts.t;
      ts = null;
      if (moved < 30 && dur < 800) {
        lastTouch = Date.now();
        e.preventDefault();
        fn();
      }
    }, { passive: false });
  });
}
function bindSceneTaps(root) {
  bindTapEls(root, '.scene-cell', node => anToggleAsset(+node.dataset.aid));
}

function renderAnalyze() {
  const page = $('#analyzePage'); if (!page || !anState || !anState.report) return;
  const r = anState.report;
  const proj = anState.project;
  const assets = proj.assets || [];
  anState.off = anState.off || new Set();
  const validIds = new Set(assets.map(a => a.assetId));
  anState.off = new Set([...anState.off].filter(x => validIds.has(x)));
  cutSelFor(anState.pid).off = anState.off;   // 与项目页共享同一份勾选
  const ta0 = $('#aiPrompt'); if (ta0) anState.prompt = ta0.value.trim();   // 重绘保留提示词
  const rAssets = r.assets || [];
  const usedSec = anState.t0 ? `，用时 ${((Date.now()-anState.t0)/1000).toFixed(1)} 秒` : '';
  const totalMs = assets.reduce((s,a)=>s+(a.durationMs||0),0);

  // 场景统计
  const groups = {};
  rAssets.forEach(ra => { const k = sceneOf(ra.assetId) || '素材画面'; groups[k] = (groups[k]||0)+1; });
  const groupKeys = Object.keys(groups);

  let html = `
  <div class="done-banner anim">${svg(I.done,16,16)}${assets.length} 段素材分析完成${usedSec}</div>

  <section class="card anim d1">
    <div class="card-head">
      <div class="card-title"><span class="ico">${svg(I.chart,13,13)}</span>分析了什么</div>
      <button class="card-more" onclick="anRerun()">重新分析</button>
    </div>
    <div class="steps">
      <div class="step"><span class="step-dot">${svg(I.check,11,11)}</span><div class="step-main"><div class="step-name">素材解析</div><div class="step-note">${assets.length} 段视频 · 共 ${fmtDur(totalMs)}</div></div></div>
      <div class="step"><span class="step-dot">${svg(I.check,11,11)}</span><div class="step-main"><div class="step-name">场景识别</div><div class="step-note">识别出 ${groupKeys.length || 1} 类场景</div></div></div>
      <div class="step"><span class="step-dot">${svg(I.check,11,11)}</span><div class="step-main"><div class="step-name">情绪与节奏分析</div><div class="step-note">镜头运动 + 明暗变化 + 人声检测综合判定</div></div></div>
      <div class="step"><span class="step-dot">${svg(I.check,11,11)}</span><div class="step-main"><div class="step-name">配乐匹配</div><div class="step-note">从本机曲库中选出 ${anState.candidates.length || 4} 首</div></div></div>
    </div>
  </section>

  <section class="card anim d2">
    <div class="card-head">
      <div class="card-title"><span class="ico">${svg(I.search,13,13)}</span>你的素材长这样</div>
    </div>
    ${numberedStripHtml(assets, sceneOf)}
    <div class="scene-tags" style="margin-top:14px">
      ${groupKeys.map((k,i) => `<span class="scene-tag"><i class="dot c${(i%4)+1}"></i>${esc(k)} <b>×${groups[k]}</b></span>`).join('')}
    </div>
    ${r.tempoBpm ? `<div class="tempo-line">${svg(I.wave,15,15)}整体节奏 <b>约 ${Math.round(r.tempoBpm)} BPM</b>${r.meta && r.meta.paceAdvice ? '，' + esc(r.meta.paceAdvice) : ''}</div>` : ''}
  </section>`;

  // AI 提示词（紧跟素材卡，改完往下挑配乐、调偏好）
  html += `<section class="card anim d2" style="padding:13px 15px">
    <div class="card-head" style="margin-bottom:9px"><div class="card-title"><span class="ico">${svg(I.edit,13,13)}</span>告诉 AI 怎么剪</div></div>
    <textarea id="aiPrompt" rows="3" style="width:100%;box-sizing:border-box;border:1px solid #E4E6EB;border-radius:8px;padding:10px;font-size:13px;resize:vertical" placeholder="例如：只用第1、3段，第2段放结尾；节奏快一点，总长控制在40秒内">${esc(anState.prompt || '')}</textarea>
    <div style="font-size:11px;color:var(--ink-3);margin-top:6px">可用「第N段」精准指定素材；留空则按内容精彩程度自动裁剪</div>
  </section>`;

  const moods = r.moodMix ? Object.entries(r.moodMix) : [];
  if (moods.length) {
    const moodColors = ['var(--brand)', 'var(--teal)', '#E5A83B', '#8A6BDB'];
    const pct = v => Math.round(v * (v <= 1 ? 100 : 1));  // 服务端返回 0~1 占比
    html += `<section class="card anim d2">
      <div class="card-head"><div class="card-title"><span class="ico">${svg(I.smile,13,13)}</span>情绪构成</div></div>
      ${moods.map(([k,v],i) => `<div class="mood-row"><span class="mood-name">${esc(k)}</span><div class="mood-bar"><i style="width:${pct(v)}%;background:${moodColors[i%4]}"></i></div><span class="mood-val">${pct(v)}%</span></div>`).join('')}
    </section>`;
  }

  // 配乐推荐
  if (anState.candidates.length) {
    const moodCls = ['m1','m2','m3','m4'];
    html += `<section class="card anim d3">
      <div class="card-head">
        <div class="card-title"><span class="ico">${svg(I.music,13,13)}</span>按内容挑的配乐</div>
        <button class="card-more" onclick="anRefreshMusic()">换一批</button>
      </div>
      ${anState.candidates.map((m, i) => {
        const sel = m.musicId === anState.selectedMusic;
        const chorus = m.chorusMs ? ` · 副歌在 ${Math.round(m.chorusMs/1000)} 秒处` : '';
        const pill = i === 0 ? '<span class="pill-hot">最匹配</span>' : (m.reasons && m.reasons[0] ? `<span class="pill-inst">${esc(m.reasons[0])}</span>` : '');
        return `<div class="music-item ${sel ? 'active' : ''}" onclick="anSelectMusic(${m.musicId})">
          <div class="music-cover ${moodCls[i%4]}">${svg(I.music,17,17)}</div>
          <div class="music-main">
            <div class="music-name"><span class="nm">${esc(m.title || '未知')}</span>${pill}</div>
            <div class="music-sub">${esc(m.artist || '本机曲库')} · <span class="dur">${fmtDur2(m.durationMs)}</span>${chorus}</div>
          </div>
          <button class="music-play" title="试听" onclick="event.stopPropagation();toggleMusic(${m.musicId},'${m.previewUrl}',this)">${svgFill(I.play,12,12)}</button>
          <div class="match-col"><span class="match-val" style="${sel?'':'color:var(--ink-2)'}">${m.match || 90}%</span><span class="match-lb">匹配度</span></div>
          ${sel ? `<span class="picked-mark">${svg(I.check,11,11)}</span>` : ''}
        </div>`;
      }).join('')}
    </section>`;
  }

  // 成片偏好
  html += `<section class="card anim d3">
    <div class="card-head"><div class="card-title"><span class="ico">${svg(I.sliders,13,13)}</span>成片偏好</div></div>
    <div class="pref-row"><span class="pref-lb">成片模式</span><div class="pref-opts" id="prefMode">
      <span class="pref-opt sel" data-v="normal">普通成片</span>
      <span class="pref-opt" data-v="vlog">Vlog 口播</span>
    </div></div>
    <div style="font-size:11px;color:var(--ink-3);margin-top:10px">素材原声「自动」：AI 旁白配音开启时自动关闭原声避免人声打架，其余情况保留</div>
    <div id="modeHint" style="display:none;font-size:11px;color:var(--brand);background:var(--brand-bg);border-radius:6px;padding:8px 10px;margin-top:11px;line-height:1.6">Vlog 口播模式：完整保留口播语音、按叙事顺序编排，成片自动生成字幕并朗读配音（之后可编辑字幕、换音色）</div>
    <div class="pref-row"><span class="pref-lb">素材原声</span><div class="pref-opts" id="prefOv">
      <span class="pref-opt sel" data-v="auto">自动</span>
      <span class="pref-opt" data-v="on">保留</span>
      <span class="pref-opt" data-v="off">关闭</span>
    </div></div>
    <div class="pref-row"><span class="pref-lb">AI 自检</span><div class="pref-opts" id="prefReview">
      <span class="pref-opt sel" data-v="on">开启（不达标自动重剪）</span>
      <span class="pref-opt" data-v="off">关闭</span>
    </div></div>
    <div class="pref-row"><span class="pref-lb">字幕风格</span><div class="pref-opts" id="prefSubStyle">
      <span class="pref-opt sel" data-v="asr">原话字幕</span>
      <span class="pref-opt" data-v="humor">幽默风趣</span>
      <span class="pref-opt" data-v="serious">认真严谨</span>
      <span class="pref-opt" data-v="warm">温暖治愈</span>
      <span class="pref-opt" data-v="literary">文艺清新</span>
    </div></div>
    <div class="pref-row"><span class="pref-lb">目标时长</span><div class="pref-opts" id="prefDur">
      <span class="pref-opt" data-v="45s">45 秒</span>
      <span class="pref-opt sel" data-v="fit">AI 智能适配</span>
      <span class="pref-opt" data-v="full">全长度</span>
    </div></div>
    <div class="pref-row"><span class="pref-lb">画幅比例</span><div class="pref-opts" id="prefAspect">
      <span class="pref-opt" data-v="16:9">16:9</span>
      <span class="pref-opt sel" data-v="9:16">9:16 竖屏</span>
      <span class="pref-opt" data-v="1:1">1:1</span>
    </div></div>
    <div class="pref-row"><span class="pref-lb">转场风格</span><div class="pref-opts" id="prefTrans">
      <span class="pref-opt sel" data-v="gentle">柔和叠化</span>
      <span class="pref-opt" data-v="dynamic">动感推近</span>
      <span class="pref-opt" data-v="minimal">极简硬切</span>
    </div></div>
  </section>`;

  page.innerHTML = html;
  if (anState.prompt) { const ta = $('#aiPrompt'); if (ta) ta.value = anState.prompt; }

  // 触屏兜底：部分手机 webview（尤其微信内置）tap 不合成 click，
  // 用 touchend 短触直触发，click 在 600ms 内去重防止双触发
  bindSceneTaps(page);

  document.querySelectorAll('.pref-opts').forEach(group => {
    group.addEventListener('click', e => {
      if (e.target.classList.contains('pref-opt')) {
        group.querySelectorAll('.pref-opt').forEach(o => o.classList.remove('sel'));
        e.target.classList.add('sel');
        if (group.id === 'prefMode') {
          const h = $('#modeHint');
          if (h) h.style.display = e.target.dataset.v === 'vlog' ? '' : 'none';
        }
      }
    });
  });

  setAnalyzeBar('generate');
}

// ===== 配乐试听 =====
let _audio = null, _audioBtn = null;
function stopMusic() {
  if (_audio) { _audio.pause(); _audio = null; }
  if (_audioBtn) { _audioBtn.innerHTML = svgFill(I.play,12,12); _audioBtn = null; }
}
window.toggleMusic = (mid, url, btn) => {
  if (_audio && _audio.dataset.mid === String(mid)) { stopMusic(); return; }
  stopMusic();
  _audio = new Audio(API + url);
  _audio.dataset.mid = mid;
  _audioBtn = btn;
  btn.innerHTML = svgFill('<rect x="6" y="4" width="4.5" height="16" rx="1.4"/><rect x="13.5" y="4" width="4.5" height="16" rx="1.4"/>',12,12);
  _audio.play().catch(() => { toast('试听失败', true); stopMusic(); });
  _audio.onended = () => stopMusic();
};

// ===== 生成成片（含换个剪法） =====
window.doAutoCut = async (pid, regenEdl = null) => {
  stopMusic();
  let body;
  if (regenEdl) {
    // 换个剪法：保留配乐与偏好（含成片模式），换 seed 重排；素材沿用本版实际用到的子集
    const pref = regenEdl.meta && regenEdl.meta.preference || {};
    body = { seed: Math.floor(Math.random() * 100000),
             preference: { duration: pref.duration || 'fit', aspect: (regenEdl.meta && regenEdl.meta.aspect) || '9:16', transitionStyle: pref.transitionStyle || 'gentle', mode: pref.mode || 'normal', subtitleStyle: pref.subtitleStyle || 'asr' },
             height: 1080, fps: 30, render: true,
             assetIds: [...new Set(regenEdl.clips.map(c => c.assetId))] };
    if (regenEdl.audio && regenEdl.audio.musicId) body.musicId = regenEdl.audio.musicId;
  } else {
    const aspect = $('#prefAspect .sel')?.dataset.v || '9:16';
    const trans = $('#prefTrans .sel')?.dataset.v || 'gentle';
    const dur = $('#prefDur .sel')?.dataset.v || 'fit';
    const mode = $('#prefMode .sel')?.dataset.v || 'normal';
    const prompt = (($('#aiPrompt') && $('#aiPrompt').value) || (anState && anState.prompt) || '').trim();
    const assets = (anState && anState.project && anState.project.assets) || [];
    const selIds = assets.filter(a => !(anState && anState.off && anState.off.has(a.assetId))).map(a => a.assetId);
    if (assets.length && !selIds.length) { toast('至少勾选一段素材参与成片', true); return; }
    const subStyle = $('#prefSubStyle .sel')?.dataset.v || 'asr';
    const review = ($('#prefReview .sel')?.dataset.v || 'on') !== 'off';
    const ov = $('#prefOv .sel')?.dataset.v || 'auto';
    body = { preference: { duration: dur, aspect, transitionStyle: trans, mode, subtitleStyle: subStyle, originalVoice: ov }, height: 1080, fps: 30, render: true, review };
    if (selIds.length && selIds.length < assets.length) body.assetIds = selIds;
    if (prompt) body.prompt = prompt;
    if (anState && anState.selectedMusic) body.musicId = anState.selectedMusic;
  }

  const musicName = regenEdl ? '' : (anState && anState.candidates.find(m => m.musicId === anState.selectedMusic)?.title) || '';
  showSheet(`
    <div class="sheet-grab"></div>
    <div class="sheet-title">正在为你成片</div>
    <div class="sheet-sub">${musicName ? `《${esc(musicName)}》配乐 · ` : ''}AI 正在剪辑与渲染</div>
    <div class="gen-steps" id="genSteps"></div>
    <div class="sheet-btns">
      <button class="btn-main" style="display:none" id="sheetResultBtn">进入成片预览${svg(I.arrowR,15,15)}</button>
      <button class="btn-sheet-ghost" onclick="hideSheet()">先不看了，返回调整</button>
    </div>
  `);
  renderGenSteps(0);

  try {
    const r = await api(`/projects/${pid}/auto-cut`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
    });
    if (r.jobId) pollRender(pid, r.jobId);
    else { hideSheet(); toast('未启动渲染'); }
  } catch(e) { toast(e.message, true); hideSheet(); }
};

function renderGenSteps(pct) {
  const box = $('#genSteps'); if (!box) return;
  const stages = ['精选片段裁剪','叙事排序','匹配转场','配乐节拍对齐','渲染成片','AI 自检审查'];
  const current = Math.min(Math.floor(pct / 100 * stages.length), stages.length - 1);
  // 步骤骨架只建一次；轮询仅切换 data-st 与备注文字，避免重建 DOM 导致转圈动画重启/闪烁
  if (!box.children.length) {
    box.innerHTML = stages.map((name, i) => `
      <div class="gen-step" data-st="wait" data-i="${i}">
        <span class="gs-state">
          <span class="gs-ok">${svg(I.check,10,10)}</span>
          <span class="gs-run"></span>
          <span class="gs-wait"></span>
        </span>
        <span class="gs-name">${name}</span>
        <span class="gs-note">等待中</span>
      </div>`).join('');
  }
  stages.forEach((_, i) => {
    const row = box.children[i]; if (!row) return;
    const st = i < current ? 'ok' : i === current ? 'run' : 'wait';
    const note = i < current ? '已完成' : i === current ? `${pct}%` : '等待中';
    if (row.dataset.st !== st) {
      row.dataset.st = st;
      row.querySelector('.gs-note').classList.toggle('run', st === 'run');
    }
    const noteEl = row.querySelector('.gs-note');
    if (noteEl.textContent !== note) noteEl.textContent = note;
  });
}

async function pollRender(pid, jobId) {
  try {
    const job = await api(`/renders/${jobId}`);
    renderGenSteps(Math.round((job.progress || 0) * 100));
    if (job.status === 'done') {
      clearTimeout(pollTimers.render);
      renderGenSteps(100);
      const note = job.result && job.result.subtitleNote;
      if (note) setTimeout(() => toast(note, true), 600);
      const rv = job.result && job.result.review;
      if (rv) setTimeout(() => toast(`AI 自检：${rv.score} 分 · ${rv.pass ? '通过' : '未达标'} · ${rv.comment}`, !rv.pass), 1400);
      const rnote = job.result && job.result.reviewNote;
      if (rnote) setTimeout(() => toast(rnote, true), 2400);
      const btn = $('#sheetResultBtn');
      if (btn) {
        btn.style.display = '';
        btn.onclick = () => { hideSheet(); goPreview(pid); };
      }
      setTimeout(() => { hideSheet(); goPreview(pid); }, 1000);
    } else if (job.status === 'failed' || job.status === 'error') {
      toast(job.error || '渲染失败', true);
      hideSheet();
    } else {
      pollTimers.render = setTimeout(() => pollRender(pid, jobId), 1500);
    }
  } catch(e) { toast(e.message, true); hideSheet(); }
}

// ============================================================
// 页面 3 · 成片预览
// ============================================================
const TRANS_NAMES = { none: '硬切', dissolve: '叠化', push_in: '推近', iris: '划像', flash: '闪白' };
const TRANS_ICONS = { dissolve: I.transDissolve, push_in: I.transPush, iris: I.transIris, flash: I.transFlash, none: I.transNone };
const ASPECT_LABEL = { '9:16': '竖屏', '16:9': '横屏', '1:1': '方形' };

function edlTotalMs(edl) {
  return edl.clips.reduce((s,c) => s + (c.outMs - c.inMs), 0) -
    edl.transitions.filter(t => t.type !== 'none').reduce((s,t) => s + t.durMs, 0);
}
function edlTransSummary(edl) {
  const cnt = {};
  edl.transitions.forEach(t => { if (t.type !== 'none') cnt[t.type] = (cnt[t.type]||0)+1; });
  return Object.entries(cnt).map(([k,n]) => `${TRANS_NAMES[k]}×${n}`).join(' · ');
}

async function goPreview(pid, version = null, withNav = true, from = null) {
  if (withNav) nav(`#/preview/${pid}${version ? '/' + version : ''}`);
  if (from === 'works') setBackCtx('#/works');
  else if (from === 'folder') setBackCtx(`#/works/${pid}`);
  else if (from === 'project') setBackCtx(`#/project/${pid}`);
  // from 为空（剪辑流程内跳转）：保留已有上下文，如「换个剪法/导出」往返后返回仍回作品页
  clearPolls(); stopMusic();
  render(topbar('成片预览', '分析', `backOr(() => goAnalyze(${pid}))`) +
    `<main class="page-body" id="previewPage"><div style="text-align:center;padding:40px"><div class="spinner" style="margin:0 auto"></div></div></main>`);
  try {
    const [expData, tl, proj, music] = await Promise.all([
      api(`/projects/${pid}/exports`),
      api(`/projects/${pid}/timeline`).catch(() => null),
      api(`/projects/${pid}`),
      api(`/projects/${pid}/music`).catch(() => ({ candidates: [] })),
    ]);
    const e = version ? expData.exports.find(x => x.version === version) : expData.exports[0];
    if (!e) { toast('找不到成片', true); goProject(pid); return; }
    const edl = tl ? tl.edl : null;
    const assets = proj.assets || [];
    const assetMap = {}; assets.forEach(a => assetMap[a.assetId] = a);
    const totalMs = edl ? edlTotalMs(edl) : 0;
    const assetsTotalMs = assets.reduce((s,a) => s + (a.durationMs||0), 0);
    const usedMs = edl ? edl.clips.reduce((s,c) => s + (c.outMs - c.inMs), 0) : 0;
    const trimmedMs = Math.max(0, assetsTotalMs - usedMs);
    const musicId = edl && edl.audio ? edl.audio.musicId : null;
    const musicInfo = musicId ? (music.candidates || []).find(m => m.musicId === musicId) : null;
    const musicName = musicInfo ? musicInfo.title : (musicId ? '已选配乐' : '无配乐');
    const aspect = edl && edl.meta ? (edl.meta.aspect || '9:16') : '9:16';
    const ratioCls = aspect === '9:16' ? 'ratio-916' : aspect === '1:1' ? 'ratio-11' : '';
    const transSummary = edl ? edlTransSummary(edl) : '';
    const firstClip = edl && edl.clips.length ? edl.clips[0] : null;
    const lastClip = edl && edl.clips.length ? edl.clips[edl.clips.length-1] : null;
    const fadeNote = (firstClip && firstClip.fadeInMs) || (lastClip && lastClip.fadeOutMs) ? '首尾淡出' : '';
    const posterUrl = firstClip && assetMap[firstClip.assetId] ? assetMap[firstClip.assetId].thumbUrl : (assets[0] ? assets[0].thumbUrl : null);
    const elapsed = e.elapsedMs ? ` · 用时 ${(e.elapsedMs/1000).toFixed(1)} 秒` : '';

    const page = $('#previewPage'); if (!page) return;
    let html = `
    <div class="done-banner anim">${svg(I.done,16,16)}第 ${e.version} 版成片已生成${elapsed}
      <button class="vbtn" onclick="goAnalyze(${pid})">看生成依据</button>
    </div>

    <section class="player anim d1 ${ratioCls}" id="player">
      <video id="pvVideo" src="${e.url}" playsinline preload="metadata"></video>
      ${posterUrl ? `<img class="poster" id="pvPoster" src="${posterUrl}">` : ''}
      <span class="player-tag">${svg(I.spark,11,11)}AI 剪辑 · ${aspect} ${ASPECT_LABEL[aspect] || ''}</span>
      <button class="play-ctl" id="playBtn" title="播放 / 暂停">
        ${svgFill(I.playBig,24,24).replace('<svg', '<svg class="play-ico"')}
        ${svgFill(I.pauseBig,22,22).replace('<svg', '<svg class="pause-ico"')}
      </button>
      <div class="player-bar">
        <span class="music-chip">${svg(I.music,11,11)}${esc(musicName)}</span>
        <div class="track-line" id="pvTrack"><i id="pvFill"></i></div>
        <span class="track-time" id="pvTime">00:00 / ${fmtDur2(totalMs)}</span>
      </div>
    </section>

    ${(edl && edl.meta && edl.meta.review) ? `
    <section class="card anim d1" style="margin-top:14px">
      <div class="card-head" style="margin-bottom:8px">
        <div class="card-title"><span class="ico">${svg(I.smile,13,13)}</span>AI 自检报告</div>
        <span class="state-chip ${edl.meta.review.pass ? 'done' : 'draft'}">${edl.meta.review.score} 分 · ${edl.meta.review.pass ? '通过' : '未达标'}</span>
      </div>
      <div style="font-size:13px;line-height:1.6">${esc(edl.meta.review.comment || '')}</div>
      ${edl.meta.review.suggestions && edl.meta.review.suggestions.length ? `
      <div style="font-size:11.5px;color:var(--ink-3);margin-top:8px;line-height:1.7">
        ${edl.meta.review.pass ? '审查意见：' : '待改进（可进编辑器手动调整）：'}
        ${edl.meta.review.suggestions.map(x => '· ' + esc(x)).join('<br>')}
      </div>` : ''}
      <div style="font-size:10.5px;color:var(--ink-3);margin-top:8px">共自检 ${edl.meta.review.rounds || 1} 轮${edl.meta.review.pass ? '后达标交付' : '，已达轮数上限，交付最优版'}</div>
    </section>` : ''}

    <section class="card anim d1" style="margin-top:14px">
      <div class="card-head" style="margin-bottom:1px">
        <div class="card-title"><span class="ico">${svg(I.file,13,13)}</span>这版成片的信息</div>
      </div>
      <div class="info-grid">
        <div class="info-cell"><div class="info-lb">总时长</div><div class="info-val">${fmtDur2(totalMs)}</div></div>
        <div class="info-cell"><div class="info-lb">使用片段</div><div class="info-val">${edl ? edl.clips.length : '--'} 段${trimmedMs ? `<small>裁掉 ${fmtDur(trimmedMs)}</small>` : ''}</div></div>
        <div class="info-cell"><div class="info-lb">配乐</div><div class="info-val"><button class="music-link" onclick="goEditor(${pid})">${esc(musicName)}</button>${musicInfo ? `<small>${musicInfo.match}% 匹配</small>` : ''}</div></div>
        <div class="info-cell"><div class="info-lb">转场</div><div class="info-val">${transSummary || '无'}${fadeNote ? `<small>${fadeNote}</small>` : ''}</div></div>
      </div>
    </section>`;

    if (edl) {
      html += `<section class="card anim d2">
        <div class="card-head" style="margin-bottom:0">
          <div class="card-title"><span class="ico">${svg(I.film,13,13)}</span>AI 是这么排的</div>
          <button class="card-more" onclick="goEditor(${pid})">调整顺序</button>
        </div>
        <div class="clip-strip">
        ${edl.clips.map((c, i) => {
          const a = assetMap[c.assetId] || {};
          const t = edl.transitions.find(t => t.afterClip === i + 1);
          const mark = (t && t.type !== 'none' && i < edl.clips.length - 1)
            ? `<div class="trans-mark"><span class="t-dot">${svg(TRANS_ICONS[t.type] || I.transDissolve,12,12)}</span>${TRANS_NAMES[t.type]}</div>` : '';
          return `<div class="clip-cell">
              <div class="clip-ph">${a.thumbUrl ? `<img src="${a.thumbUrl}">` : ''}
                <span class="clip-no">${i+1}</span>
                <span class="clip-dur">${fmtDur2(c.outMs - c.inMs)}</span>
              </div>
              <div class="clip-name">${esc(stem(a.fileName))}</div>
              <div class="clip-sub">${esc(c.note || '')}</div>
            </div>${mark}`;
        }).join('')}
        </div>
      </section>`;
    }

    html += `<div class="tips-row anim d2">
      <button class="tip-item act" id="tipRegen">
        <div class="t-title">${svg(I.refresh,13,13)}不满意？</div>
        <div class="t-desc">点这里换个剪法：保留配乐，重新排片段与节奏</div>
      </button>
      <button class="tip-item act" id="tipEdit">
        <div class="t-title">${svg(I.edit,13,13)}想自己改？</div>
        <div class="t-desc">进编辑器可裁片段、调顺序、换音乐、改转场</div>
      </button>
    </div>`;

    page.innerHTML = html;

    // 提示卡可点：换剪法 / 进编辑器
    $('#tipRegen').onclick = () => { if (edl) doAutoCut(pid, edl); else toast('还没有剪辑方案', true); };
    $('#tipEdit').onclick = () => goEditor(pid);

    // 顶栏加「换个剪法」
    const regen = document.createElement('button');
    regen.className = 'regen-btn';
    regen.title = '换个剪法重新生成';
    regen.innerHTML = `${svg(I.regen,14,14)}换个剪法`;
    regen.onclick = () => { if (edl) doAutoCut(pid, edl); else toast('还没有剪辑方案', true); };
    $('#app .topbar').appendChild(regen);

    if (!$('#previewBar')) {
      const bar = el('footer', 'action-bar'); bar.id = 'previewBar';
      bar.innerHTML = `
        <button class="btn-main wide" onclick="goEditor(${pid})">${svg(I.edit,16,16)}继续手动调整</button>
        <button class="btn-sub" onclick="goExport(${pid}, ${e.version})">${svg(I.download,16,16)}直接导出</button>`;
      $('#app').appendChild(bar);
    }

    // 播放器交互
    const v = $('#pvVideo'), player = $('#player'), fill = $('#pvFill'), timeLb = $('#pvTime'), track = $('#pvTrack');
    const upd = () => {
      if (!v.duration) return;
      fill.style.width = (v.currentTime / v.duration * 100) + '%';
      timeLb.textContent = `${fmtDur2(v.currentTime*1000)} / ${fmtDur2(v.duration*1000)}`;
    };
    // 按视频真实比例自适应播放器，避免黑边
    v.addEventListener('loadedmetadata', () => {
      if (v.videoWidth && v.videoHeight) {
        player.classList.remove('ratio-916', 'ratio-11');
        const availW = player.parentElement.clientWidth;
        const maxH = 460;
        const ratio = v.videoWidth / v.videoHeight;
        let w = availW, h = availW / ratio;
        if (h > maxH) { h = maxH; w = maxH * ratio; }
        player.style.aspectRatio = 'auto';
        player.style.width = w + 'px';
        player.style.height = h + 'px';
        player.style.margin = w < availW ? '0 auto' : '';
      }
      upd();
    });
    $('#playBtn').onclick = () => {
      if (v.paused) { v.play(); player.classList.add('playing'); }
      else { v.pause(); player.classList.remove('playing'); }
    };
    v.onclick = () => $('#playBtn').onclick();
    v.addEventListener('play', () => { const p = $('#pvPoster'); if (p) p.style.display = 'none'; });
    v.addEventListener('timeupdate', upd);
    v.addEventListener('ended', () => { player.classList.remove('playing'); });
    track.onclick = ev => {
      const r = track.getBoundingClientRect();
      if (v.duration) v.currentTime = v.duration * Math.max(0, Math.min(1, (ev.clientX - r.left) / r.width));
    };
  } catch(e) { toast(e.message, true); }
}

// ============================================================
// 页面 4 · 手动编辑器（深色）
// ============================================================
let tlState = null;

async function goEditor(pid, withNav = true) {
  if (withNav) nav(`#/editor/${pid}`);
  clearPolls(); stopMusic();
  render(`<div class="topbar">
      <button class="icon-btn" onclick="edClose()">${svg(I.x,18,18)}</button>
      <div class="topbar-title">编辑成片<span class="unsaved-dot" id="unsavedDot"></span></div>
      <button class="icon-btn" title="撤销" disabled>${svg(I.undo,17,17)}</button>
      <button class="save-btn" onclick="tlSave()">保存</button>
    </div>` +
    `<main class="page-body" id="editorPage"><div style="text-align:center;padding:40px"><div class="spinner" style="margin:0 auto"></div></div></main>`, 'dark');
  try {
    const [tl, proj, music] = await Promise.all([
      api(`/projects/${pid}/timeline`),
      api(`/projects/${pid}`),
      api(`/projects/${pid}/music`).catch(() => ({ candidates: [] })),
    ]);
    tlState = {
      pid, edl: tl.edl, assets: proj.assets,
      musicList: music.candidates || [],
      hasExports: !!(proj.exports && proj.exports.length),
      selected: 0, tab: 'paneClip', trimOpen: -1, splitMode: null,
      dirty: false, captionStash: [],
    };
    renderEditor();
    const bar = el('footer', 'action-bar'); bar.id = 'editorBar';
    bar.innerHTML = `
      <button class="btn-ghost" onclick="edClose()">${svg(I.arrowL,14,14)}返回预览</button>
      <button class="btn-main" onclick="tlSaveRender()">${svg(I.done,15,15)}完成编辑，去预览</button>`;
    $('#app').appendChild(bar);
    // 时间轴 dock
    const dock = el('div', 'timeline-dock'); dock.id = 'editorDock';
    $('#app').appendChild(dock);
    renderDock();
  } catch(e) { toast(e.message, true); goProject(pid); }
}

function tlClipDur(c) { return c.outMs - c.inMs; }
function tlTotalMs() { return edlTotalMs(tlState.edl); }
function tlStartOf(i) {
  const e = tlState.edl;
  let s = 0;
  for (let k = 0; k < i; k++) {
    s += tlClipDur(e.clips[k]);
    const t = e.transitions.find(t => t.afterClip === k+1);
    if (t && t.type !== 'none') s -= t.durMs;
  }
  return s;
}
function tlAsset(id) { return tlState.assets.find(a => a.assetId === id || a.id === id) || {}; }
function tlMusicInfo(id) { return tlState.musicList.find(m => m.musicId === id); }
function markDirty() { tlState.dirty = true; const d = $('#unsavedDot'); if (d) d.classList.add('show'); }
window.edClose = () => {
  if (tlState && tlState.dirty && !confirm('有未保存修改，确定离开？')) return;
  if (tlState && tlState.hasExports) goPreview(tlState.pid); else if (tlState) goProject(tlState.pid); else goProjects();
};

function renderEditor() {
  const page = $('#editorPage'); if (!page || !tlState) return;
  const e = tlState.edl;
  const total = tlTotalMs();
  const i = tlState.selected;
  const c = e.clips[i] || e.clips[0];
  const a = tlAsset(c.assetId);
  const titleCap = e.captions.find(cp => cp.style === 'title');

  // ===== 预览区 =====
  let html = `
  <section class="preview-wrap anim">
    <div class="preview-frame">
      ${a.proxyUrl ? `<video id="edVideo" src="${a.proxyUrl}" playsinline preload="metadata"></video>` : (a.thumbUrl ? `<img class="pv-img" src="${a.thumbUrl}">` : '')}
      <span class="clip-badge">片段 ${i+1}/${e.clips.length} · ${esc(stem(a.fileName))}</span>
      ${titleCap ? `<div class="frame-text">${esc(titleCap.text)}</div>` : ''}
      <div class="pv-ctl">
        <button class="pv-play" id="edPlay" title="播放">${svgFill(I.play,11,11)}</button>
        <div class="pv-track" id="edTrack"><i id="edFill"></i></div>
        <span class="pv-time" id="edTime">00:00 / ${fmtDur2(tlClipDur(c))}</span>
      </div>
    </div>
  </section>

  <nav class="tool-tabs">
    <button class="tool-tab ${tlState.tab==='paneClip'?'active':''}" data-pane="paneClip">${svg(I.film,17,17)}片段</button>
    <button class="tool-tab ${tlState.tab==='paneTrans'?'active':''}" data-pane="paneTrans">${svg(I.swapH,17,17)}转场</button>
    <button class="tool-tab ${tlState.tab==='paneMusic'?'active':''}" data-pane="paneMusic">${svg(I.music,17,17)}音频</button>
    <button class="tool-tab ${tlState.tab==='paneText'?'active':''}" data-pane="paneText">${svg(I.type,17,17)}文字</button>
  </nav>`;

  // ===== 片段面板 =====
  html += `<section class="pane ${tlState.tab==='paneClip'?'active':''}" id="paneClip">`;
  e.clips.forEach((cl, idx) => {
    const aa = tlAsset(cl.assetId);
    const sel = idx === tlState.selected;
    const trimming = sel && tlState.trimOpen === idx;
    html += `<div class="clip-row ${sel ? 'sel' : ''}" data-idx="${idx}">
      <div class="clip-row-head" onclick="tlSelect(${idx})">
        <div class="clip-thumb">${aa.thumbUrl ? `<img src="${aa.thumbUrl}">` : ''}<span class="clip-order">${idx+1}</span></div>
        <div class="clip-info">
          <div class="clip-name">${esc(stem(aa.fileName))}</div>
          <div class="clip-meta">成片内 ${fmtDur2(tlClipDur(cl))} · ${trimming ? '<span class="cut">正在裁剪</span>' : `原素材 ${fmtDur2(aa.durationMs)}`}</div>
        </div>
        <div class="clip-ops" onclick="event.stopPropagation()">
          <button class="op-btn" title="上移" onclick="tlMove(${idx},-1)" ${idx===0?'disabled':''}>${svg(I.up,14,14)}</button>
          <button class="op-btn" title="下移" onclick="tlMove(${idx},1)" ${idx===e.clips.length-1?'disabled':''}>${svg(I.down,14,14)}</button>
          <button class="op-btn ${trimming?'hot':''}" title="裁剪" onclick="tlTrimToggle(${idx})">${svg(I.scissors,14,14)}</button>
        </div>
      </div>
      ${trimming ? trimBoxHtml(cl, aa, idx) : ''}
    </div>`;
  });
  html += '</section>';

  // ===== 转场面板 =====
  html += `<section class="pane ${tlState.tab==='paneTrans'?'active':''}" id="paneTrans">`;
  if (e.clips.length < 2) {
    html += `<div class="trans-row" style="text-align:center;color:var(--t3);font-size:12px">仅一个片段，无剪辑点</div>`;
  }
  for (let k = 1; k < e.clips.length; k++) {
    const t = e.transitions.find(t => t.afterClip === k);
    const cur = t ? t.type : 'none';
    const posMs = tlStartOf(k);
    const nameA = stem(tlAsset(e.clips[k-1].assetId).fileName);
    const nameB = stem(tlAsset(e.clips[k].assetId).fileName);
    const chip = cur === 'none' ? '<span class="cur-chip none">当前：硬切</span>'
      : `<span class="cur-chip">当前：${TRANS_NAMES[cur]} ${(t.durMs/1000).toFixed(1)}s</span>`;
    html += `<div class="trans-row">
      <div class="trans-head">
        <div class="trans-pos">
          <div class="p1">${esc(nameA)} → ${esc(nameB)}</div>
          <div class="p2">位置 ${fmtDur2(posMs)}${t && t.beatAligned ? ' · 已对齐节拍' : ''}</div>
        </div>
        ${chip}
      </div>
      <div class="trans-opts">
        ${[['dissolve','叠化'],['push_in','推近'],['iris','划像'],['flash','闪白'],['none','无转场']].map(([v,n]) =>
          `<button class="trans-opt ${cur===v?'sel':''}" onclick="tlSetTrans(${k},'${v}')">${svg(TRANS_ICONS[v],15,15)}${n}</button>`).join('')}
      </div>
    </div>`;
  }
  html += '</section>';

  // ===== 配乐面板 =====
  const au = e.audio;
  const curM = au.musicId ? tlMusicInfo(au.musicId) : null;
  html += `<section class="pane ${tlState.tab==='paneMusic'?'active':''}" id="paneMusic">
    <div class="cur-music ${au.musicId ? '' : 'off'}">
      <div class="cm-cover ${au.musicId ? '' : 'none'}">${svg(au.musicId ? I.music : I.x,18,18)}</div>
      <div class="cm-main">
        <div class="cm-name">${curM ? esc(curM.title) : au.musicId ? '已选配乐' : '不使用配乐'}${au.musicId ? '<span class="using">使用中</span>' : ''}</div>
        <div class="cm-sub">${curM ? `${esc(curM.artist || '本机曲库')} · ${fmtDur2(curM.durationMs)}${au.offsetMs ? ` · 从 ${Math.round(au.offsetMs/1000)} 秒处对齐节拍` : ''}` : '只保留素材原声'}</div>
      </div>
    </div>
    <div class="vol-box">
      <div class="vol-head"><span>配乐音量</span><b id="volMusicVal">${Math.round(au.volume*100)}%</b></div>
      <div class="vol-slider" id="volMusic" data-v="${au.volume}">
        <span class="fill" style="width:${au.volume*100}%"></span>
        <span class="knob" style="left:${au.volume*100}%"></span>
      </div>
      <div class="vol-marks"><span>仅人声时压低</span><span>100%</span></div>
    </div>
    <div class="vol-box">
      <div class="vol-head"><span>素材原声</span><b id="volOrigVal">${au.keepOriginal !== false ? Math.round((au.originalVolume ?? 1)*100)+'%' : '关闭'}</b></div>
      <div class="vol-slider" id="volOrig" data-v="${au.originalVolume ?? 1}">
        <span class="fill" style="width:${(au.originalVolume ?? 1)*100}%"></span>
        <span class="knob" style="left:${(au.originalVolume ?? 1)*100}%"></span>
      </div>
      <div class="vol-marks"><span>拖动调音量</span><span onclick="tlToggleOriginal()" style="cursor:pointer;color:${au.keepOriginal !== false ? 'var(--brand)' : 'var(--t2)'}">${au.keepOriginal !== false ? '点击关闭原声' : '点击开启原声'}</span></div>
    </div>
    <div class="vol-box">
      <div class="vol-head">
        <span>字幕配音（朗读字幕）</span>
        <button class="toggle ${au.ttsEnabled ? '' : 'off'}" title="开关注幕配音" onclick="tlToggleTts()"></button>
      </div>
      <div style="font-size:10.5px;color:var(--t3);margin:2px 0 9px">开启后成片时把「文字」页的字幕朗读出来；语音比画面长会自动加速贴合</div>
      <select id="ttsVoice" onchange="tlSetVoice(this.value)" style="width:100%;height:34px;background:#191B20;border:1px solid var(--d-line);border-radius:7px;color:var(--t1);font-size:11.5px;padding:0 8px">
        <option value="">加载音色…</option>
      </select>
      <div class="vol-head" style="margin-top:11px"><span>语速</span><b id="ttsRateVal">${(au.ttsRate ?? 1).toFixed(1)}x</b></div>
      <div class="vol-slider" id="ttsRate">
        <span class="fill" style="width:${(((au.ttsRate ?? 1) - 0.7) / 0.8 * 100).toFixed(0)}%"></span>
        <span class="knob" style="left:${(((au.ttsRate ?? 1) - 0.7) / 0.8 * 100).toFixed(0)}%"></span>
      </div>
      <div class="vol-marks"><span>0.7x 慢</span><span>1.0x</span><span>1.5x 快</span></div>
      <div class="vol-head" style="margin-top:11px">
        <span>配音时压低配乐</span>
        <button class="toggle ${au.ducking === false ? 'off' : ''}" title="显式开关 ducking" onclick="tlToggleDucking()"></button>
      </div>
      <div style="font-size:10.5px;color:var(--t3);margin:2px 0 2px">朗读字幕时配乐自动降到约三成并缓入缓出，人声更清楚</div>
    </div>
    <div class="alt-title">换成这几首也不错</div>
    ${tlState.musicList.filter(m => m.musicId !== au.musicId).map((m, idx) => `
      <div class="alt-item">
        <div class="alt-cover a${(idx%4)+1}">${svg(I.music,15,15)}</div>
        <div class="alt-main">
          <div class="alt-name">${esc(m.title)}</div>
          <div class="alt-sub">${esc(m.artist || '本机曲库')} · ${m.match}% 匹配 · ${fmtDur2(m.durationMs)}</div>
        </div>
        <button class="swap-btn" onclick="tlSwapMusic(${m.musicId})">换这首</button>
      </div>`).join('')}
    ${au.musicId ? `<div class="alt-item">
      <div class="alt-cover none">${svg(I.x,15,15)}</div>
      <div class="alt-main"><div class="alt-name">不使用配乐</div><div class="alt-sub">只保留素材原声</div></div>
      <button class="swap-btn" onclick="tlSwapMusic(null)">移除配乐</button>
    </div>` : ''}
  </section>`;

  // ===== 文字面板（字幕管理 + 片头/片尾开关） =====
  html += `<section class="pane ${tlState.tab==='paneText'?'active':''}" id="paneText">
    <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px">
      <button class="trim-act hot" style="flex:1" onclick="edGenSubtitles()">${svg(I.spark,13,13)}AI 识别字幕</button>
      <button class="trim-act" style="flex:1" onclick="edAddSubtitle()">${svg(I.plus,13,13)}添加字幕</button>
    </div>
    <div style="display:flex;align-items:center;gap:7px;margin-bottom:10px">
      <select id="narStyle" style="flex:1;height:34px;background:#191B20;border:1px solid var(--d-line);border-radius:7px;color:var(--t1);font-size:11.5px;padding:0 8px">
        <option value="humor">幽默风趣</option>
        <option value="serious">认真严谨</option>
        <option value="warm">温暖治愈</option>
        <option value="literary">文艺清新</option>
        <option value="custom">自定义风格…</option>
      </select>
      <button class="trim-act hot" style="flex:1.2" onclick="edGenNarration()">${svg(I.edit,12,12)}AI 生成文案</button>
    </div>
    <input id="narCustom" placeholder="描述你想要的风格，如：东北唠嗑风、热血解说" style="display:none;width:100%;height:34px;background:#191B20;border:1px solid var(--d-line);border-radius:7px;color:var(--t1);font-size:11.5px;padding:0 10px;margin-bottom:10px;box-sizing:border-box">
    <div id="asrState" style="font-size:10.5px;color:var(--t3);margin-bottom:10px;display:none"></div>`;
  const capStyle = { title: '片头标题', ending_credit: '片尾署名', subtitle: '字幕' };
  const subs = [], others = [];
  e.captions.forEach((cp, ci) => {
    if (cp.style === 'subtitle') subs.push({ cp, ci });
    else others.push({ cp, on: true, key: 'on' + ci });
  });
  tlState.captionStash.forEach(s => others.push({ cp: s.cap, on: false, key: 'off' + s.idx }));
  subs.sort((a, b) => a.cp.startMs - b.cp.startMs);

  html += `<div class="alt-title">字幕 ${subs.length} 条 · 点条目编辑${subs.length ? '，保存并渲染后烧进画面' : '，或点上方「AI 识别字幕」自动生成'}</div>`;
  if (subs.length) {
    const total = tlTotalMs();
    html += `<div class="cap-lane" id="capLane"></div>
      <div class="cap-scale"><span>00:00</span><span>${fmtDur2(Math.round(total / 2))}</span><span>${fmtDur2(total)}</span></div>
      <div style="font-size:10px;color:var(--t3);margin:0 0 12px">左右拖动字幕条调整出现时间 · 拖两端调长短 · 点按改文字</div>`;
  }
  html += subs.map(({ cp, ci }) => `
    <div class="sub-row" onclick="edEditSubtitle(${ci})">
      <span class="sub-time">${fmtDur2(cp.startMs)}–${fmtDur2(cp.endMs)}</span>
      <span class="sub-text">${esc(cp.text)}</span>
    </div>`).join('');

  others.forEach(({ cp, on, key }) => {
    html += `<div class="text-card" style="margin-top:${cp.style === 'title' && subs.length ? '13px' : '9px'}">
      <div class="text-head">
        <span class="text-type">${capStyle[cp.style] || '字幕'}</span>
        <span class="text-content">${esc(cp.text)}</span>
        <button class="toggle ${on ? '' : 'off'}" title="显示 / 隐藏" onclick="tlToggleCaption('${key}')"></button>
      </div>
      <div class="text-meta">
        <span>显示 ${fmtDur2(cp.startMs)} – ${fmtDur2(cp.endMs)}</span>
        ${cp.style === 'title' ? '<span>已加缓入动画</span>' : cp.style === 'ending_credit' ? '<span>随片尾淡出</span>' : ''}
      </div>
    </div>`;
  });
  html += '</section>';

  page.innerHTML = html;

  // tab 切换
  page.querySelectorAll('.tool-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      tlState.tab = tab.dataset.pane;
      page.querySelectorAll('.tool-tab').forEach(t => t.classList.remove('active'));
      page.querySelectorAll('.pane').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      const p = $('#' + tab.dataset.pane); if (p) p.classList.add('active');
    });
  });

  bindEditorPreview();
  bindTrimBar();
  bindCapTrack();
  bindVolSlider('volMusic', v => { tlState.edl.audio.volume = v; $('#volMusicVal').textContent = Math.round(v*100)+'%'; markDirty(); });
  bindVolSlider('volOrig', v => { tlState.edl.audio.originalVolume = v; tlState.edl.audio.keepOriginal = v > 0; $('#volOrigVal').textContent = Math.round(v*100)+'%'; markDirty(); });
  ensureTtsVoices();
  bindVolSlider('ttsRate', v => {
    tlState.edl.audio.ttsRate = Math.round((0.7 + v * 0.8) * 10) / 10;
    const lb = $('#ttsRateVal'); if (lb) lb.textContent = tlState.edl.audio.ttsRate.toFixed(1) + 'x';
    markDirty();
  });
  const narSel = $('#narStyle');
  if (narSel) narSel.addEventListener('change', () => {
    const c = $('#narCustom'); if (c) c.style.display = narSel.value === 'custom' ? '' : 'none';
  });
}

function trimBoxHtml(cl, aa, idx) {
  const assetMs = aa.durationMs || cl.outMs;
  const lPct = (cl.inMs / assetMs * 100).toFixed(1);
  const rPct = (cl.outMs / assetMs * 100).toFixed(1);
  const positions = ['left', 'center', 'right'];
  return `<div class="trim-box">
    <div class="trim-lbs"><span>入点 <b id="trimIn">${fmtT(cl.inMs)}</b></span><span>出点 <b id="trimOut">${fmtT(cl.outMs)}</b></span></div>
    <div class="trim-bar ${tlState.splitMode === idx ? 'splitting' : ''}" id="trimBar" data-asset="${assetMs}">
      ${positions.map(p => `<div class="seg">${aa.thumbUrl ? `<img src="${aa.thumbUrl}" style="object-position:${p}">` : ''}</div>`).join('')}
      <span class="keep-mark" id="keepMark" style="left:${lPct}%;right:${(100-rPct).toFixed(1)}%"></span>
      <span class="handle l" id="handleL" style="left:calc(${lPct}% - 6px)"></span>
      <span class="handle r" id="handleR" style="left:calc(${rPct}% - 6px)"></span>
    </div>
    <div class="trim-note">保留区间 <b id="trimKeep">${((tlClipDur(cl))/1000).toFixed(1)}</b> 秒 · <b>拖动两端手柄微调</b>${tlState.splitMode === idx ? ' · 点击画面条选择截断位置' : ''}</div>
    <div class="trim-actions">
      <button class="trim-act ${tlState.splitMode === idx ? 'hot' : ''}" onclick="tlSplitMode(${idx})">${svg(I.scissors,12,12)}${tlState.splitMode === idx ? '取消截断' : '截断片段'}</button>
      <button class="trim-act danger" onclick="tlDelete(${idx})">${svg(I.trash,12,12)}删除片段</button>
    </div>
  </div>`;
}

// ===== 编辑器预览播放（片段级） =====
function bindEditorPreview() {
  const v = $('#edVideo'); if (!v || !tlState) return;
  const i = tlState.selected;
  const c = tlState.edl.clips[i];
  const inS = c.inMs / 1000, outS = c.outMs / 1000;
  const fill = $('#edFill'), timeLb = $('#edTime'), track = $('#edTrack'), playBtn = $('#edPlay');
  const durMs = tlClipDur(c);
  const upd = () => {
    const cur = Math.max(0, Math.min(v.currentTime - inS, durMs / 1000));
    fill.style.width = (cur / (durMs/1000) * 100) + '%';
    timeLb.textContent = `${fmtDur2(cur*1000)} / ${fmtDur2(durMs)}`;
    if (v.currentTime >= outS - 0.05) {
      v.pause();
      playBtn.innerHTML = svgFill(I.play,11,11);
      v.currentTime = inS;
    }
  };
  v.addEventListener('loadedmetadata', () => { v.currentTime = inS; upd(); });
  v.addEventListener('timeupdate', upd);
  playBtn.onclick = () => {
    if (v.paused) {
      if (v.currentTime < inS || v.currentTime >= outS - 0.05) v.currentTime = inS;
      v.play();
      playBtn.innerHTML = svgFill(I.pauseBig,10,10);
    } else {
      v.pause();
      playBtn.innerHTML = svgFill(I.play,11,11);
    }
  };
  track.onclick = ev => {
    const r = track.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (ev.clientX - r.left) / r.width));
    v.currentTime = inS + ratio * (durMs / 1000);
    upd();
  };
}

// ===== 字幕时间轴（拖拽微调） =====
function bindCapTrack() {
  const lane = $('#capLane'); if (!lane || !tlState) return;
  const total = Math.max(tlTotalMs(), 1);
  const e = tlState.edl;
  const items = e.captions.map((cp, ci) => ({ cp, ci })).filter(x => x.cp.style === 'subtitle');
  // 百分比定位：面板未激活（display:none）时没有宽度也能正确布局
  lane.innerHTML = items.map(({ cp, ci }) => `
    <div class="cap-chip" data-ci="${ci}"
         style="left:${(cp.startMs / total * 100).toFixed(2)}%;width:${(((cp.endMs - cp.startMs) / total * 100) || 1.5).toFixed(2)}%">
      <span class="h" data-m="l"></span><span class="cap-chip-txt">${esc(cp.text)}</span><span class="h" data-m="r"></span>
    </div>`).join('');

  let drag = null;   // { chip, cap, mode, x0, s0, e0, moved, pxms }
  lane.addEventListener('pointerdown', ev => {
    const chip = ev.target.closest('.cap-chip'); if (!chip) return;
    const cap = e.captions[+chip.dataset.ci]; if (!cap) return;
    drag = { chip, cap, mode: ev.target.dataset.m === 'l' ? 'l' : ev.target.dataset.m === 'r' ? 'r' : 'm',
             x0: ev.clientX, s0: cap.startMs, e0: cap.endMs, moved: false,
             pxms: lane.clientWidth / total };   // 交互瞬间面板必然可见，此时宽度可信
    drag.chip.setPointerCapture(ev.pointerId);
    ev.preventDefault();
  });
  lane.addEventListener('pointermove', ev => {
    if (!drag) return;
    const dms = (ev.clientX - drag.x0) / drag.pxms;
    if (Math.abs(ev.clientX - drag.x0) > 4) drag.moved = true;
    const minLen = 300;
    if (drag.mode === 'm') {
      const len = drag.e0 - drag.s0;
      const s = Math.max(0, Math.min(drag.s0 + dms, total - len));
      drag.cap.startMs = Math.round(s / 100) * 100;
      drag.cap.endMs = drag.cap.startMs + len;
    } else if (drag.mode === 'l') {
      drag.cap.startMs = Math.round(Math.max(0, Math.min(drag.s0 + dms, drag.e0 - minLen)) / 100) * 100;
    } else {
      drag.cap.endMs = Math.round(Math.max(Math.min(total, drag.e0 + dms), drag.cap.startMs + minLen) / 100) * 100;
    }
    drag.chip.style.left = (drag.cap.startMs / total * 100).toFixed(2) + '%';
    drag.chip.style.width = (((drag.cap.endMs - drag.cap.startMs) / total * 100) || 1.5).toFixed(2) + '%';
  });
  const finish = () => {
    if (!drag) return;
    const wasTap = !drag.moved && drag.mode === 'm';
    const ci = +drag.chip.dataset.ci;
    drag.chip.classList.remove('drag'); drag = null;
    if (wasTap) { edEditSubtitle(ci); return; }
    markDirty();
    renderEditor();   // 拖拽已结束，整页刷新同步列表时间
  };
  lane.addEventListener('pointerup', finish);
  lane.addEventListener('pointercancel', () => { if (drag) { drag.chip.classList.remove('drag'); drag = null; } });
}

// ===== 裁剪手柄 =====
function bindTrimBar() {
  const bar = $('#trimBar'); if (!bar || !tlState) return;
  const i = tlState.selected;
  const c = tlState.edl.clips[i];
  const assetMs = +bar.dataset.asset;
  const km = $('#keepMark'), hl = $('#handleL'), hr = $('#handleR');

  const paint = () => {
    const lPct = c.inMs / assetMs * 100, rPct = c.outMs / assetMs * 100;
    km.style.left = lPct + '%'; km.style.right = (100 - rPct) + '%';
    hl.style.left = `calc(${lPct}% - 6px)`; hr.style.left = `calc(${rPct}% - 6px)`;
    $('#trimIn').textContent = fmtT(c.inMs); $('#trimOut').textContent = fmtT(c.outMs);
    $('#trimKeep').textContent = (tlClipDur(c)/1000).toFixed(1);
  };

  const drag = (handle, side) => {
    handle.addEventListener('pointerdown', ev => {
      ev.stopPropagation(); ev.preventDefault();
      handle.setPointerCapture(ev.pointerId);
      const rect = bar.getBoundingClientRect();
      const move = e2 => {
        const pct = Math.max(0, Math.min(1, (e2.clientX - rect.left) / rect.width));
        const ms = Math.round(pct * assetMs);
        if (side === 'l') c.inMs = Math.max(0, Math.min(ms, c.outMs - 500));
        else c.outMs = Math.min(assetMs, Math.max(ms, c.inMs + 500));
        paint();
      };
      const up = () => {
        handle.removeEventListener('pointermove', move);
        handle.removeEventListener('pointerup', up);
        markDirty(); renderDock();
      };
      handle.addEventListener('pointermove', move);
      handle.addEventListener('pointerup', up);
    });
  };
  drag(hl, 'l'); drag(hr, 'r');

  // 截断模式：点击画面条选择截断点
  bar.addEventListener('click', ev => {
    if (tlState.splitMode !== i) return;
    if (ev.target.classList.contains('handle')) return;
    const rect = bar.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (ev.clientX - rect.left) / rect.width));
    const cutMs = Math.round(c.inMs + ratio * tlClipDur(c));
    tlSplitAt(i, cutMs);
  });
}

// ===== 音量滑条 =====
function bindVolSlider(id, cb) {
  const s = $('#' + id); if (!s) return;
  const fill = s.querySelector('.fill'), knob = s.querySelector('.knob');
  const set = ratio => {
    ratio = Math.max(0, Math.min(1, ratio));
    fill.style.width = ratio*100 + '%';
    knob.style.left = ratio*100 + '%';
    cb(ratio);
  };
  const onMove = ev => {
    const rect = s.getBoundingClientRect();
    set((ev.clientX - rect.left) / rect.width);
  };
  s.addEventListener('pointerdown', ev => {
    ev.preventDefault();
    s.setPointerCapture(ev.pointerId);
    onMove(ev);
    const move = e2 => onMove(e2);
    const up = () => { s.removeEventListener('pointermove', move); s.removeEventListener('pointerup', up); };
    s.addEventListener('pointermove', move);
    s.addEventListener('pointerup', up);
  });
}

// ===== 片段操作 =====
window.tlSelect = i => {
  tlState.selected = i;
  if (tlState.trimOpen !== -1 && tlState.trimOpen !== i) tlState.trimOpen = -1;
  renderEditor(); renderDock();
};
window.tlTrimToggle = i => {
  tlState.selected = i;
  tlState.trimOpen = tlState.trimOpen === i ? -1 : i;
  tlState.splitMode = null;
  renderEditor(); renderDock();
};
window.tlSplitMode = i => {
  tlState.splitMode = tlState.splitMode === i ? null : i;
  renderEditor();
  if (tlState.splitMode === i) toast('截断模式：点击画面条选择截断位置');
};
window.tlSplitAt = (i, cutMs) => {
  const e = tlState.edl;
  const c = e.clips[i];
  if (cutMs - c.inMs < 400 || c.outMs - cutMs < 400) { toast('距离片段边缘太近，无法截断', true); return; }
  const c2 = { ...c, inMs: cutMs };
  e.clips.splice(i + 1, 0, c2);
  c.outMs = cutMs;
  e.transitions = e.transitions.map(t => t.afterClip > i ? { ...t, afterClip: t.afterClip + 1 } : t);
  e.transitions.push({ afterClip: i + 1, type: 'none', durMs: 400, beatAligned: false });
  tlState.splitMode = null;
  tlState.selected = i + 1;
  tlState.trimOpen = -1;
  markDirty(); renderEditor(); renderDock();
  toast('已截断为两段（衔接处为硬切）');
};
window.tlMove = (i, dir) => {
  const clips = tlState.edl.clips;
  const j = i + dir;
  [clips[i], clips[j]] = [clips[j], clips[i]];
  tlState.selected = j;
  tlState.trimOpen = -1;
  markDirty(); renderEditor(); renderDock();
};
window.tlDelete = i => {
  const e = tlState.edl;
  if (e.clips.length <= 1) { toast('至少保留一个片段', true); return; }
  e.clips.splice(i, 1);
  e.transitions = e.transitions.filter(t => t.afterClip !== i && t.afterClip !== i + 1)
    .map(t => t.afterClip > i + 1 ? { ...t, afterClip: t.afterClip - 1 } : t);
  tlState.selected = Math.max(0, i - 1);
  tlState.trimOpen = -1;
  markDirty(); renderEditor(); renderDock();
};
window.tlSetTrans = (afterClip, type) => {
  const e = tlState.edl;
  let t = e.transitions.find(t => t.afterClip === afterClip);
  if (t) t.type = type;
  else e.transitions.push({ afterClip, type, durMs: 600, beatAligned: false });
  markDirty(); renderEditor(); renderDock();
};
window.tlSwapMusic = mid => {
  const au = tlState.edl.audio;
  au.musicId = mid;
  const m = mid ? tlMusicInfo(mid) : null;
  au.offsetMs = m && m.chorusMs ? m.chorusMs : 0;
  markDirty(); renderEditor(); renderDock();
  toast(mid ? `已换成《${m ? m.title : '配乐'}》` : '已移除配乐');
};
window.tlToggleOriginal = () => {
  const au = tlState.edl.audio;
  au.keepOriginal = au.keepOriginal === false;
  markDirty(); renderEditor();
};
window.tlToggleCaption = key => {
  const e = tlState.edl;
  if (key.startsWith('on')) {
    const ci = +key.slice(2);
    const cap = e.captions[ci];
    if (!cap) return;
    e.captions.splice(ci, 1);
    tlState.captionStash.push({ cap, idx: ci });
  } else {
    const si = tlState.captionStash.findIndex(s => 'off' + s.idx === key);
    if (si === -1) return;
    const s = tlState.captionStash.splice(si, 1)[0];
    e.captions.splice(Math.min(s.idx, e.captions.length), 0, s.cap);
  }
  markDirty(); renderEditor();
};

// ===== 风格文案 / 字幕配音 =====
window.edGenNarration = async () => {
  const styleSel = $('#narStyle');
  const style = styleSel ? styleSel.value : 'humor';
  const custom = style === 'custom' ? (($('#narCustom') || {}).value || '').trim() : '';
  if (style === 'custom' && !custom) { toast('先描述一下你想要的风格', true); return; }
  const st = $('#asrState');
  if (st) { st.style.display = ''; st.textContent = 'AI 正在撰写风格文案…'; }
  try {
    const r = await api(`/projects/${tlState.pid}/narration`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ style, custom })
    });
    const poll = async () => {
      try {
        const j = await api(`/renders/${r.jobId}`);
        if (j.status === 'done') {
          const subs = (j.result && j.result.subtitles) || [];
          tlState.edl.captions = tlState.edl.captions.filter(c => c.style !== 'subtitle')
            .concat(subs.map(x => ({ text: x.text, startMs: x.startMs, endMs: x.endMs, style: 'subtitle' })));
          markDirty(); renderEditor();
          toast(subs.length ? `已生成 ${subs.length} 条文案，记得保存` : '没有生成文案，可重试或手写');
        } else if (j.status === 'error') {
          toast(j.error || '文案生成失败', true);
          const s2 = $('#asrState'); if (s2) { s2.style.display = 'none'; s2.textContent = ''; }
        } else {
          const s2 = $('#asrState'); if (s2) s2.textContent = j.message || '生成中…';
          pollTimers.nar = setTimeout(poll, 1500);
        }
      } catch(err) { toast(err.message, true); const s2 = $('#asrState'); if (s2) s2.style.display = 'none'; }
    };
    poll();
  } catch(e) { toast(e.message, true); if (st) st.style.display = 'none'; }
};
window.tlToggleTts = () => {
  tlState.edl.audio.ttsEnabled = !tlState.edl.audio.ttsEnabled;
  markDirty(); renderEditor();
};
window.tlToggleDucking = () => {
  tlState.edl.audio.ducking = !(tlState.edl.audio.ducking !== false);
  markDirty(); renderEditor();
};
window.tlSetVoice = v => { tlState.edl.audio.ttsVoice = v; markDirty(); };
async function ensureTtsVoices() {
  const sel = $('#ttsVoice'); if (!sel) return;
  if (!window._ttsVoices) {
    try {
      const r = await api('/tts/voices');
      window._ttsVoices = r;
    } catch { window._ttsVoices = { voices: [], default: '' }; }
  }
  const { voices, default: dft } = window._ttsVoices;
  const cur = tlState.edl.audio.ttsVoice || dft || '';
  sel.innerHTML = (voices.length ? voices : [{ name: dft || '', comment: '默认中文音色' }])
    .map(v => `<option value="${esc(v.name)}" ${v.name === cur ? 'selected' : ''}>${esc(v.name)}${v.comment ? ' · ' + esc(v.comment.slice(0, 12)) : ''}</option>`).join('');
}

// ===== 字幕：AI 识别 / 编辑 / 添加 / 删除 =====
window.edGenSubtitles = async () => {
  const st = $('#asrState');
  if (st) { st.style.display = ''; st.textContent = '正在识别语音…（首次使用需下载语音模型，请稍候）'; }
  try {
    const r = await api(`/projects/${tlState.pid}/subtitles`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}'
    });
    const poll = async () => {
      try {
        const j = await api(`/renders/${r.jobId}`);
        if (j.status === 'done') {
          const subs = (j.result && j.result.subtitles) || [];
          tlState.edl.captions = tlState.edl.captions.filter(c => c.style !== 'subtitle')
            .concat(subs.map(s => ({ text: s.text, startMs: s.startMs, endMs: s.endMs, style: 'subtitle' })));
          markDirty(); renderEditor();
          toast(subs.length ? `识别到 ${subs.length} 条字幕，记得保存` : '没识别到语音，可手动添加字幕');
        } else if (j.status === 'error') {
          toast(j.error || '识别失败', true);
          const s2 = $('#asrState'); if (s2) { s2.style.display = 'none'; s2.textContent = ''; }
        } else {
          const s2 = $('#asrState');
          if (s2) s2.textContent = j.message || '识别中…';
          pollTimers.asr = setTimeout(poll, 1500);
        }
      } catch(err) {
        toast(err.message, true);
        const s2 = $('#asrState'); if (s2) s2.style.display = 'none';
      }
    };
    poll();
  } catch(e) {
    toast(e.message, true);
    if (st) st.style.display = 'none';
  }
};
window.edAddSubtitle = () => {
  const base = tlState.selected >= 0 ? tlStartOf(tlState.selected) : 0;
  tlState.edl.captions.push({ text: '新字幕', startMs: base, endMs: base + 2000, style: 'subtitle' });
  markDirty(); renderEditor();
  edEditSubtitle(tlState.edl.captions.length - 1);
};
window.edEditSubtitle = ci => {
  const cap = tlState.edl.captions[ci]; if (!cap || cap.style !== 'subtitle') return;
  showSheet(`
    <div class="sheet-grab"></div>
    <div class="sheet-title">编辑字幕</div>
    <div style="padding:10px 0 4px">
      <textarea id="subText" rows="3" style="width:100%;box-sizing:border-box;border:1px solid #E4E6EB;border-radius:8px;padding:10px;font-size:14px;resize:vertical">${esc(cap.text)}</textarea>
      <div style="display:flex;gap:12px;margin-top:12px;align-items:center;font-size:12px;color:var(--ink-2);flex-wrap:wrap">
        <span>开始</span><input type="number" id="subStart" step="0.1" min="0" value="${(cap.startMs/1000).toFixed(1)}" style="width:72px;height:34px;border:1px solid #E4E6EB;border-radius:7px;padding:0 8px;font-size:13px"> s
        <span>结束</span><input type="number" id="subEnd" step="0.1" min="0" value="${(cap.endMs/1000).toFixed(1)}" style="width:72px;height:34px;border:1px solid #E4E6EB;border-radius:7px;padding:0 8px;font-size:13px"> s
      </div>
      <div style="font-size:10.5px;color:var(--ink-3);margin-top:6px">时间是成片里的秒数（如 3.5 = 第 3.5 秒出现）</div>
    </div>
    <div class="sheet-btns">
      <button class="btn-main" onclick="edSaveSubtitle(${ci})">保存</button>
      <button class="btn-sheet-ghost" style="color:#DC2626" onclick="edDeleteSubtitle(${ci})">删除这条字幕</button>
    </div>
  `);
};
window.edSaveSubtitle = ci => {
  const cap = tlState.edl.captions[ci]; if (!cap) return;
  const text = ($('#subText').value || '').trim();
  const s = Math.round(Math.max(0, parseFloat($('#subStart').value) || 0) * 1000);
  const en = Math.round(Math.max(0, parseFloat($('#subEnd').value) || 0) * 1000);
  if (!text) { toast('字幕内容不能为空', true); return; }
  if (en - s < 300) { toast('结束时间要晚于开始时间', true); return; }
  cap.text = text; cap.startMs = s; cap.endMs = en;
  hideSheet(); markDirty(); renderEditor();
  toast('字幕已更新，记得保存');
};
window.edDeleteSubtitle = ci => {
  tlState.edl.captions.splice(ci, 1);
  hideSheet(); markDirty(); renderEditor();
};

// ===== 时间轴 dock =====
function renderDock() {
  const dock = $('#editorDock'); if (!dock || !tlState) return;
  const e = tlState.edl;
  const total = tlTotalMs();
  const availW = Math.min(window.innerWidth, 414) - 24;
  const pxPerMs = Math.max(0.045, availW / Math.max(total, 1));
  const contentW = Math.max(availW, total * pxPerMs);

  // 刻度 5 个
  let ruler = '';
  for (let k = 0; k <= 4; k++) {
    const t = Math.round(total * k / 4);
    ruler += `<span style="left:${t * pxPerMs}px">${fmtDur2(t)}</span>`;
  }

  let clips = '';
  e.clips.forEach((c, i) => {
    const w = Math.max(36, tlClipDur(c) * pxPerMs - 3);
    const left = tlStartOf(i) * pxPerMs;
    const a = tlAsset(c.assetId);
    clips += `<div class="tld-clip ${tlState.selected === i ? 'now' : ''}" style="width:${w}px;left:${left}px" onclick="tlSelect(${i})">
      ${a.thumbUrl ? `<img src="${a.thumbUrl}">` : ''}
      <span class="tld-dur">${Math.round(tlClipDur(c)/1000)}s</span>
    </div>`;
    const t = e.transitions.find(t => t.afterClip === i + 1);
    if (t && t.type !== 'none' && i < e.clips.length - 1) {
      const bx = (tlStartOf(i) + tlClipDur(c) - t.durMs / 2) * pxPerMs;
      clips += `<span class="tld-trans" style="left:${bx}px" title="${TRANS_NAMES[t.type]}">${svg(t.type === 'push_in' ? I.transPush : I.transDissolveS,10,10)}</span>`;
    }
  });

  const au = e.audio;
  const m = au.musicId ? tlMusicInfo(au.musicId) : null;
  const musicName = m ? m.title : au.musicId ? '已选配乐' : null;

  dock.innerHTML = `
    <div class="tld-scroll">
      <div class="tld-ruler" style="width:${contentW}px">${ruler}</div>
      <div class="tld-video" style="width:${contentW}px">${clips}</div>
    </div>
    <div class="tld-audio">
      <span class="tld-audio-label ${musicName ? '' : 'off'}">${svg(I.music,9,9)}${musicName ? esc(musicName) : '无配乐'}</span>
      <div class="wave ${musicName ? '' : 'off'}">${musicName ? `<svg viewBox="0 0 300 26" preserveAspectRatio="none"><path d="M0 13 L6 13 L9 7 L12 19 L15 10 L18 16 L21 5 L24 20 L27 12 L30 14 L33 8 L36 17 L40 11 L44 15 L47 6 L50 21 L54 13 L58 13 L62 9 L66 18 L70 12 L74 14 L78 7 L82 19 L86 13 L90 13 L94 10 L98 16 L102 8 L106 18 L110 13 L114 13 L118 6 L122 20 L126 12 L130 15 L134 9 L138 17 L142 13 L146 13 L150 11 L154 16 L158 7 L162 19 L166 13 L170 13 L174 8 L178 18 L182 12 L186 14 L190 6 L194 21 L198 13 L202 13 L206 10 L210 17 L214 9 L218 16 L222 13 L226 13 L230 7 L234 19 L238 12 L242 14 L246 8 L250 18 L254 13 L258 13 L262 10 L266 16 L270 6 L274 20 L278 13 L282 13 L286 9 L290 17 L294 13 L300 13" fill="none" stroke="#5FBFA3" stroke-width="1.6"/></svg>` : ''}</div>
    </div>`;
}

// ===== 保存 / 渲染 =====
window.tlSave = async () => {
  if (!tlState) return;
  const { pid, edl } = tlState;
  try {
    const body = { ...edl };
    delete body.version;
    await api(`/projects/${pid}/timeline`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
    });
    tlState.dirty = false;
    const d = $('#unsavedDot'); if (d) d.classList.remove('show');
    toast('已保存');
  } catch(e) { toast(e.message, true); }
};

window.tlSaveRender = async () => {
  if (!tlState) return;
  const { pid, edl } = tlState;
  try {
    const body = { ...edl };
    delete body.version;
    const r = await api(`/projects/${pid}/timeline`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
    });
    tlState.dirty = false;
    const job = await api(`/projects/${pid}/render`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ edlVersion: r.version, height: 1080, fps: 30 })
    });
    showSheet(`
      <div class="sheet-grab"></div>
      <div class="sheet-title">正在重新渲染</div>
      <div class="sheet-sub">按你调整的时间线生成新版本</div>
      <div class="gen-steps" id="genSteps"></div>
      <div class="sheet-btns">
        <button class="btn-main" style="display:none" id="sheetResultBtn">进入成片预览${svg(I.arrowR,15,15)}</button>
        <button class="btn-sheet-ghost" onclick="hideSheet()">继续在编辑器等待</button>
      </div>
    `);
    renderGenSteps(0);
    pollRender(pid, job.jobId);
  } catch(e) { toast(e.message, true); }
};

// ============================================================
// 页面 5 · 导出与分享
// ============================================================
async function goExport(pid, version = null, withNav = true) {
  if (withNav) nav(`#/export/${pid}${version ? '/' + version : ''}`);
  clearPolls(); stopMusic();
  render(topbar('导出与分享', '预览', `goPreview(${pid}${version ? ', ' + version : ''})`) +
    `<main class="page-body pb-export" id="exportPage"><div style="text-align:center;padding:40px"><div class="spinner" style="margin:0 auto"></div></div></main>`);
  try {
    const [expData, tl, proj] = await Promise.all([
      api(`/projects/${pid}/exports`),
      api(`/projects/${pid}/timeline`).catch(() => null),
      api(`/projects/${pid}`),
    ]);
    const e = version ? expData.exports.find(x => x.version === version) : expData.exports[0];
    if (!e) { toast('找不到成片', true); goProject(pid); return; }
    const edl = tl ? tl.edl : null;
    const totalMs = edl ? edlTotalMs(edl) : 0;
    const aspect = edl && edl.meta ? (edl.meta.aspect || '9:16') : '9:16';
    const hasWatermark = edl ? edl.captions.some(c => c.style === 'ending_credit') : true;
    const posterUrl = proj.assets && proj.assets[0] ? proj.assets[0].thumbUrl : null;
    const resH = e.resolution && e.resolution.includes('720') ? 720 : e.resolution && e.resolution.includes('2160') ? 2160 : 1080;

    const page = $('#exportPage'); if (!page) return;
    page.innerHTML = `
    <section class="export-card anim">
      <div class="ec-poster">
        <video src="${e.url}" ${posterUrl ? `poster="${posterUrl}"` : ''} playsinline preload="metadata" muted></video>
        <span class="ec-done">${svg(I.done,13,13)}导出完成${e.savedToAlbum ? ' · 已存入相册' : ''}</span>
      </div>
      <div class="ec-body">
        <div class="ec-name">${esc(e.fileName)}</div>
        <div class="ec-spec">${fmtDur2(totalMs)} · ${aspect} ${ASPECT_LABEL[aspect] || ''} · ${e.resolution || '--'}/${e.fps || 30}fps · ${fmtSize(e.sizeBytes)} · ${(e.createdAt||'').slice(5,16)}</div>
        <div class="ec-progress">
          <div class="ec-bar"><i></i></div>
          <div class="ec-bar-note">
            <span>${e.elapsedMs ? `导出用时 ${(e.elapsedMs/1000).toFixed(1)} 秒` : '导出完成'}</span>
            <b>${fmtSize(e.sizeBytes)} · 100%</b>
          </div>
        </div>
      </div>
    </section>

    <section class="card anim d1">
      <div class="card-title" style="margin-bottom:5px"><span class="ico">${svg(I.sliders,13,13)}</span>导出设置</div>
      <div class="card-tip">调整后会重新导出新版本，旧版本不会被覆盖</div>
      <div class="set-row">
        <span class="set-lb">分辨率</span>
        <div class="set-opts" id="expRes">
          <span class="set-opt ${resH===720?'sel':''}" data-v="720">720P</span>
          <span class="set-opt ${resH===1080?'sel':''}" data-v="1080">1080P</span>
          <span class="set-opt ${resH===2160?'sel':''}" data-v="2160">4K</span>
        </div>
      </div>
      <div class="set-row">
        <span class="set-lb">帧率</span>
        <div class="set-opts" id="expFps">
          <span class="set-opt ${(e.fps||30)===30?'sel':''}" data-v="30">30fps</span>
          <span class="set-opt ${e.fps===60?'sel':''}" data-v="60">60fps</span>
        </div>
      </div>
      <div class="set-row">
        <div>
          <span class="set-lb">片尾署名水印</span>
          <span class="set-lb"><small>「${esc(proj.title)} · 闪剪AI」随片尾淡出</small></span>
        </div>
        <button class="toggle ${hasWatermark ? 'on' : ''}" id="expWm" title="开关水印"></button>
      </div>
    </section>

    <section class="card anim d2">
      <div class="card-title" style="margin-bottom:5px"><span class="ico">${svg(I.share,13,13)}</span>分享给朋友</div>
      <div class="card-tip">竖屏成片将自动适配各平台发布规格</div>
      <div class="share-grid">
        <button class="share-item share-btn" data-ch="微信好友" data-url="${e.url}" data-name="${esc(e.fileName)}"><span class="share-ico wx">${svg(I.wx,21,21)}</span><span class="share-name">微信好友</span></button>
        <button class="share-item share-btn" data-ch="朋友圈" data-url="${e.url}" data-name="${esc(e.fileName)}"><span class="share-ico pyq">${svg(I.pyq,21,21)}</span><span class="share-name">朋友圈</span></button>
        <button class="share-item share-btn" data-ch="小红书" data-url="${e.url}" data-name="${esc(e.fileName)}"><span class="share-ico xhs">${svg(I.xhs,21,21)}</span><span class="share-name">小红书</span></button>
        <button class="share-item share-btn" data-ch="抖音" data-url="${e.url}" data-name="${esc(e.fileName)}"><span class="share-ico dy">${svg(I.music,21,21)}</span><span class="share-name">抖音</span></button>
      </div>
    </section>

    <div class="note-bar anim d2">
      ${svg(I.info,15,15)}
      回到编辑器再改一版，导出会生成 v${e.version + 1} 文件，旧版本不会被覆盖。
    </div>`;

    if (!$('#exportBar')) {
      const bar = el('footer', 'action-bar'); bar.id = 'exportBar';
      bar.innerHTML = `
        <button class="btn-main wide" onclick="expSaveAlbum('${e.url}','${esc(e.fileName)}')">${svg(I.download,16,16)}保存到相册</button>
        <button class="btn-sub" onclick="goPreview(${pid}, ${e.version})">${svg(I.arrowL,16,16)}回预览</button>`;
      $('#app').appendChild(bar);
    }

    // 导出设置变更 → 重新渲染
    page.querySelectorAll('.share-btn').forEach(b => {
      b.addEventListener('click', () => shareOut(b.dataset.ch, b.dataset.url, b.dataset.name));
    });
    $('#expRes').addEventListener('click', ev => {
      if (!ev.target.classList.contains('set-opt')) return;
      const h = +ev.target.dataset.v;
      if (h !== resH) reExport(pid, { height: h });
    });
    $('#expFps').addEventListener('click', ev => {
      if (!ev.target.classList.contains('set-opt')) return;
      const f = +ev.target.dataset.v;
      if (f !== (e.fps || 30)) reExport(pid, { fps: f });
    });
    $('#expWm').addEventListener('click', () => {
      reExport(pid, { watermark: !hasWatermark });
    });
  } catch(e) { toast(e.message, true); }
}

async function reExport(pid, opt) {
  try {
    const tl = await api(`/projects/${pid}/timeline`);
    const edl = tl.edl;
    delete edl.version;
    let changed = false;
    if (opt.watermark !== undefined) {
      const has = edl.captions.some(c => c.style === 'ending_credit');
      if (opt.watermark && !has) {
        const totalMs = edlTotalMs(edl);
        edl.captions.push({ text: `${edl.meta.title || '闪剪'} · 闪剪AI`, startMs: Math.max(totalMs - 3000, 0), endMs: totalMs, style: 'ending_credit' });
        changed = true;
      } else if (!opt.watermark && has) {
        edl.captions = edl.captions.filter(c => c.style !== 'ending_credit');
        changed = true;
      }
    }
    let edlVersion = tl.version;
    if (changed) {
      const r = await api(`/projects/${pid}/timeline`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(edl)
      });
      edlVersion = r.version;
    }
    showSheet(`
      <div class="sheet-grab"></div>
      <div class="sheet-title">正在重新导出</div>
      <div class="sheet-sub">按新的导出设置生成新版本</div>
      <div class="gen-steps" id="genSteps"></div>
      <div class="sheet-btns"><button class="btn-sheet-ghost" onclick="hideSheet()">后台继续</button></div>
    `);
    renderGenSteps(0);
    const job = await api(`/projects/${pid}/render`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ edlVersion, height: opt.height || 1080, fps: opt.fps || 30 })
    });
    // 轮询完成后跳到新版本的导出页
    const poll = async () => {
      try {
        const j = await api(`/renders/${job.jobId}`);
        renderGenSteps(Math.round((j.progress || 0) * 100));
        if (j.status === 'done') {
          hideSheet();
          const expData = await api(`/projects/${pid}/exports`);
          const latest = expData.exports[0];
          goExport(pid, latest ? latest.version : null);
        } else if (j.status === 'failed' || j.status === 'error') {
          toast(j.error || '导出失败', true); hideSheet();
        } else pollTimers.export = setTimeout(poll, 1500);
      } catch(err) { toast(err.message, true); hideSheet(); }
    };
    poll();
  } catch(e) { toast(e.message, true); }
}

window.shareOut = async (channel, url, name) => {
  const full = location.origin + url;
  if (navigator.share) {
    try { await navigator.share({ title: name, url: full }); } catch {}
  } else {
    try {
      await navigator.clipboard.writeText(full);
      toast(`链接已复制，粘贴到${channel}分享`);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = full; document.body.appendChild(ta); ta.select();
      document.execCommand('copy'); ta.remove();
      toast(`链接已复制，粘贴到${channel}分享`);
    }
  }
};

// 相册直存：Web Share 文件方向可用（HTTPS/PWA 环境）直接调系统分享面板「存储到相册」；
// 局域网 HTTP 下多数浏览器不支持 → 退回下载并提示手动转存
window.expSaveAlbum = async (url, name) => {
  try {
    const r = await fetch(url);
    const blob = await r.blob();
    const file = new File([blob], name, { type: blob.type || 'video/mp4' });
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      await navigator.share({ files: [file], title: name });
      toast('已调起系统分享，选择「存储到相册」即可');
      return;
    }
  } catch (e) {
    if (e && e.name === 'AbortError') return;   // 用户取消了分享面板
  }
  const a = document.createElement('a');
  a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
  toast('当前环境不支持直存相册：已开始下载，在「文件」里选中视频 → 分享 → 存储到相册', true);
};

// ============================================================
// 设置页（保持原功能）
// ============================================================
async function goSettings(withNav = true) {
  if (withNav) nav('#/settings');
  clearPolls(); stopMusic();
  render(topbar('AI 模型设置', '我的', 'goMe()') + `<main class="page-body" id="settingsPage"><div style="text-align:center;padding:40px"><div class="spinner" style="margin:0 auto"></div></div></main>`);
  await loadSettings();
}

async function loadSettings() {
  try {
    const [data, usage] = await Promise.all([
      api('/settings/model'),
      api('/settings/usage').catch(() => null)
    ]);
    const page = $('#settingsPage');
    if (!page) return;
    window._models = data.models || [];
    window._tasks = data.tasks || {};
    window._taskModels = data.taskModels || {};
    window._fallback = data.fallback || '';
    const modelOpts = sel => window._models.map(m =>
      `<option value="${m.id}" ${sel === m.id ? 'selected' : ''}>${esc(m.name)} · ${esc(m.provider)}</option>`).join('');
    const taskRows = Object.entries(window._tasks).map(([t, desc]) => `
      <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:9px">
        <span style="font-size:12.5px;color:var(--ink-2);white-space:nowrap">${esc(desc)}</span>
        <select id="task_${esc(t)}" class="model-select" style="flex:1;max-width:200px">
          <option value="">继承当前模型</option>
          ${modelOpts(window._taskModels[t])}
        </select>
      </div>`).join('');
    const usageBox = usage
      ? `<div style="display:flex;gap:8px;text-align:center">
           <div style="flex:1;background:#FAFAFB;border-radius:10px;padding:11px 4px">
             <div style="font-size:19px;font-weight:600">${usage.calls}</div>
             <div style="font-size:10.5px;color:var(--ink-3);margin-top:2px">调用次数${usage.failed ? ` · 失败 ${usage.failed}` : ''}</div>
           </div>
           <div style="flex:1;background:#FAFAFB;border-radius:10px;padding:11px 4px">
             <div style="font-size:19px;font-weight:600">${fmtTokens(usage.tokens_in)}</div>
             <div style="font-size:10.5px;color:var(--ink-3);margin-top:2px">输入 tokens</div>
           </div>
           <div style="flex:1;background:#FAFAFB;border-radius:10px;padding:11px 4px">
             <div style="font-size:19px;font-weight:600">${fmtTokens(usage.tokens_out)}</div>
             <div style="font-size:10.5px;color:var(--ink-3);margin-top:2px">输出 tokens</div>
           </div>
         </div>`
      : '<div style="font-size:12px;color:var(--ink-3)">暂无数据</div>';
    page.innerHTML = `
    <div class="hello anim"><h1>AI 模型设置</h1><p>选择模型、填入密钥，用于分析场景与生成剪辑方案</p></div>
    <section class="card anim d1">
      <div class="set-lb" style="margin-bottom:9px">模型</div>
      <select id="modelSel" class="model-select">
        ${window._models.map(m => `<option value="${m.id}" ${m.current ? 'selected' : ''}>${esc(m.name)} · ${esc(m.provider)}</option>`).join('')}
      </select>
      <div id="modelStatus" style="margin-top:10px;display:flex;align-items:center;gap:7px"></div>
      <div class="set-lb" style="margin:16px 0 9px">API Key</div>
      <input class="model-key-input" style="width:100%" type="password" id="apiKeyInput" placeholder="粘贴 API Key（只保存在这台电脑）">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px">
        <a id="getKeyLink" class="model-link" style="margin-top:0" target="_blank" href="#">获取密钥 →</a>
        <span id="quotaLb" style="font-size:11px;color:var(--ink-3)"></span>
      </div>
      <div style="display:flex;gap:10px;margin-top:14px">
        <button class="btn-sub" style="flex:1;height:44px" id="testBtn" onclick="testModel()">测试连接</button>
        <button class="btn-main" style="flex:1;height:44px" id="saveBtn" onclick="saveModel()">保存并启用</button>
      </div>
      <div id="testResult" style="margin-top:10px"></div>
    </section>
    <section class="card anim d2">
      <div class="set-lb" style="margin-bottom:2px">任务分配</div>
      <div style="font-size:11px;color:var(--ink-3);line-height:1.6">默认都用上面的当前模型；某项想固定用别的模型时单独选。</div>
      ${taskRows}
      <div class="set-lb" style="margin:16px 0 0">备用模型</div>
      <div style="font-size:11px;color:var(--ink-3);line-height:1.6;margin-bottom:9px">当前模型调用失败时自动改用它重试。</div>
      <select id="fallbackSel" class="model-select" style="width:100%">
        <option value="">不设备用（失败直接报错）</option>
        ${modelOpts(window._fallback)}
      </select>
      <button class="btn-main" style="width:100%;height:44px;margin-top:14px" id="saveTasksBtn" onclick="saveTaskModels()">保存任务分配</button>
    </section>
    <section class="card anim d3">
      <div class="set-lb" style="margin-bottom:10px">本月用量</div>
      ${usageBox}
    </section>
    <div style="margin-top:14px;padding:13px 15px;background:#FAFAFB;border-radius:10px;font-size:11.5px;color:var(--ink-3);line-height:1.8">
      · 「保存并启用」会先真实调用一次模型验证，通过才保存<br>
      · 模型、密钥与任务分配都跟着你的账号走，家人各配各的<br>
      · 未配置密钥时自动使用本地规则引擎（无 AI 视觉分析）
    </div>`;
    $('#modelSel').addEventListener('change', renderModelState);
    renderModelState();
  } catch(e) { toast(e.message, true); }
}

function fmtTokens(n) {
  n = Number(n) || 0;
  return n >= 10000 ? (n / 10000).toFixed(1) + '万' : String(n);
}

window.saveTaskModels = async () => {
  const taskModels = {};
  Object.keys(window._tasks || {}).forEach(t => {
    const sel = $('#task_' + t);
    if (sel && sel.value) taskModels[t] = sel.value;
  });
  const fallback = ($('#fallbackSel') || {}).value || '';
  const btn = $('#saveTasksBtn'); btn.disabled = true; btn.textContent = '保存中…';
  try {
    await api('/settings/model/tasks', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ taskModels, fallback })
    });
    toast('任务分配已保存');
  } catch(e) { toast(e.message, true); }
  btn.disabled = false; btn.textContent = '保存任务分配';
};

function renderModelState() {
  const m = (window._models || []).find(x => x.id === ($('#modelSel') || {}).value) || (window._models || [])[0];
  if (!m) return;
  const st = $('#modelStatus'), link = $('#getKeyLink'), quota = $('#quotaLb'), res = $('#testResult');
  if (st) {
    if (m.current) st.innerHTML = `<span class="model-badge cur">当前使用</span><span style="font-size:11px;color:var(--ink-3)">已验证可用</span>`;
    else if (m.verified) st.innerHTML = `<span class="model-badge on">已验证</span><button class="sec-link" style="font-size:11px;color:var(--brand)" onclick="enableModel('${m.id}')">启用此模型 →</button>`;
    else if (m.configured) st.innerHTML = `<span class="model-badge off">密钥未验证</span><span style="font-size:11px;color:var(--ink-3)">填入密钥验证后启用</span>`;
    else st.innerHTML = `<span class="model-badge off">未配置</span>`;
  }
  if (link) link.href = m.get_key_url || '#';
  if (quota) quota.textContent = m.free_quota ? `免费额度：${m.free_quota}` : '';
  if (res) res.innerHTML = m.config_note ? `<div style="font-size:11px;color:var(--ink-3);line-height:1.6;background:#FAFAFB;border-radius:8px;padding:8px 10px">${m.config_note}</div>` : '';
}

window.enableModel = async id => {
  try {
    await api('/settings/model', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ modelId: id, switch: true })
    });
    toast('已启用');
    await loadSettings();
  } catch(e) { toast(e.message, true); }
};

window.testModel = async () => {
  const modelId = ($('#modelSel') || {}).value;
  const apiKey = ($('#apiKeyInput') || {}).value ? $('#apiKeyInput').value.trim() : '';
  const res = $('#testResult');
  if (!apiKey) { toast('请先粘贴 API Key', true); return; }
  const btn = $('#testBtn'); btn.disabled = true; btn.textContent = '测试中…';
  res.innerHTML = '<div style="font-size:12px;color:var(--ink-3)">正在调用模型验证…</div>';
  try {
    const r = await api('/settings/model/test', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ modelId, apiKey })
    });
    res.innerHTML = r.ok
      ? `<div class="model-test-result ok">${svg(I.check,12,12)} 连接成功，模型可用${r.response ? ' · ' + esc(String(r.response).slice(0, 60)) : ''}</div>`
      : `<div class="model-test-result fail">${svg(I.x,12,12)} ${esc(r.error)}</div>`;
  } catch(e) {
    res.innerHTML = `<div class="model-test-result fail">${svg(I.x,12,12)} ${esc(e.message)}</div>`;
  }
  btn.disabled = false; btn.textContent = '测试连接';
};

window.saveModel = async () => {
  const modelId = ($('#modelSel') || {}).value;
  const input = $('#apiKeyInput');
  const apiKey = input ? input.value.trim() : '';
  if (!apiKey) { toast('请先粘贴 API Key', true); return; }
  const btn = $('#saveBtn'); btn.disabled = true; btn.textContent = '验证并保存…';
  try {
    await api('/settings/model', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ modelId, apiKey, switch: true })
    });
    toast('密钥验证通过，已保存并启用');
    await loadSettings();
  } catch(e) {
    $('#testResult').innerHTML = `<div class="model-test-result fail">${svg(I.x,12,12)} ${esc(e.message)}</div>`;
    toast('密钥不可用，未保存', true);
  }
  btn.disabled = false; btn.textContent = '保存并启用';
};

// Init：走 hash 路由，刷新保持当前页
route();
