const API = (location.hostname === 'localhost' || location.hostname === '127.0.0.1')
  ? 'http://localhost:8000'
  : 'https://timeflow-production-9cb4.up.railway.app';

// ─── Auth storage ─────────────────────────────────────────────────────────────
function getToken()  { return localStorage.getItem('tf_token'); }
function setToken(t) { localStorage.setItem('tf_token', t); }
function clearToken(){ localStorage.removeItem('tf_token'); }
function getUser()   { try { return JSON.parse(localStorage.getItem('tf_user')); } catch { return null; } }
function setUser(u)  { localStorage.setItem('tf_user', JSON.stringify(u)); }

function requireAuth() {
  if (!getToken()) { window.location.href = 'login.html'; return false; }
  const u = getUser();
  if (u && u.name) {
    document.querySelectorAll('.js-user-name').forEach(el => el.textContent = u.name);
  }
  return true;
}

function requireManagerAuth() {
  if (!getToken()) { window.location.href = 'login.html'; return false; }
  const u = getUser();
  if (!u || u.role !== 'manager') { window.location.href = 'dashboard.html'; return false; }
  loadNavBadge();
  return true;
}

async function loadNavBadge() {
  const badge = document.getElementById('nav-pending-count');
  if (!badge) return;
  try {
    const team = await apiFetch(`/timesheets/team?week_start=${isoDate(mondayOf())}`);
    const n = (team || []).filter(m => m.status === 'submitted').length;
    badge.textContent = n;
    badge.style.display = n === 0 ? 'none' : '';
  } catch (_) {}
}

function signOut() {
  clearToken();
  localStorage.removeItem('tf_user');
  window.location.href = 'login.html';
}

// ─── API fetch wrapper ────────────────────────────────────────────────────────
async function apiFetch(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json' };
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  Object.assign(headers, opts.headers || {});

  const res = await fetch(API + path, {
    ...opts,
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });

  if (res.status === 401) { clearToken(); window.location.href = 'login.html'; return null; }
  if (!res.ok) throw new Error(await res.text());
  if (res.status === 204) return null;
  return res.json();
}

// ─── Date helpers ─────────────────────────────────────────────────────────────
function mondayOf(date = new Date()) {
  const d = new Date(date);
  const dow = d.getDay();
  d.setDate(d.getDate() - (dow === 0 ? 6 : dow - 1));
  d.setHours(0, 0, 0, 0);
  return d;
}

function isoDate(d) {
  const p = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

function weekLabel(monday) {
  const MS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const end = new Date(monday); end.setDate(monday.getDate() + 6);
  return `${MS[monday.getMonth()]} ${monday.getDate()} − ${MS[end.getMonth()]} ${end.getDate()}`;
}

// day index: Mon=0 … Sun=6
function dayIndex(dateStr) {
  return (new Date(dateStr + 'T12:00:00').getDay() + 6) % 7;
}
