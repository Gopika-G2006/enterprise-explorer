/* ═══════════════════════════════════════════════════════════════
   Enterprise Intelligence Explorer - Main App Logic
═══════════════════════════════════════════════════════════════ */

const API = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && window.location.port !== '8000'
  ? `http://127.0.0.1:8000/api`
  : `/api`;

// ── State ────────────────────────────────────────────────────────
let state = {
  page: 1,
  limit: 25,
  search: '',
  category: '',
  district: '',
  pincode: '',
  nic_code: '',
  place: '',
  totalPages: 1,
  charts: {},
};

// ── DOM shortcuts ─────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const $q = sel => document.querySelector(sel);

// ── NAV switching ─────────────────────────────────────────────────
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    const target = link.dataset.page;
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    link.classList.add('active');
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    $(`page-${target}`).classList.add('active');
    if (target === 'analytics') loadAnalytics();
  });
});

// ── Utility: build API query string ──────────────────────────────
function buildQuery(extra = {}) {
  const params = {
    page: state.page,
    limit: state.limit,
    search: state.search || undefined,
    category: state.category || undefined,
    district: state.district || undefined,
    pincode: state.pincode || undefined,
    nic_code: state.nic_code || undefined,
    place: state.place || undefined,
    ...extra,
  };
  return '?' + Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join('&');
}

// ── Category badge helper ─────────────────────────────────────────
function renderTags(categories) {
  if (!categories) return '';
  return categories.split(',')
    .map(c => c.trim())
    .filter(Boolean)
    .map(c => `<span class="tag tag-${c}">${c}</span>`)
    .join('');
}

// ── Load Enterprises ──────────────────────────────────────────────
async function loadEnterprises() {
  const tbody = $('table-body');
  tbody.innerHTML = `<tr><td colspan="6" class="loading-cell"><div class="spinner"></div> Loading...</td></tr>`;

  try {
    const res = await fetch(`${API}/enterprises${buildQuery()}`);
    const data = await res.json();

    $('results-meta').textContent =
      `Showing ${(state.page - 1) * state.limit + 1}–${Math.min(state.page * state.limit, data.total)} of ${data.total.toLocaleString()} enterprises`;
    $('filter-result-count').textContent = `${data.total.toLocaleString()} results`;
    $('hero-count').textContent = data.total.toLocaleString();

    state.totalPages = data.pages;

    if (data.data.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="loading-cell">No enterprises found</td></tr>`;
      $('pagination').innerHTML = '';
      return;
    }

    tbody.innerHTML = data.data.map((e, i) => `
      <tr data-id="${e.id}">
        <td>${(state.page - 1) * state.limit + i + 1}</td>
        <td class="td-name">${escHtml(e.enterprise_name)}</td>
        <td>${escHtml(e.district || '—')}</td>
        <td>${escHtml(e.pincode || '—')}</td>
        <td class="td-desc" title="${escHtml(e.description || '')}">${escHtml(truncate(e.description, 70))}</td>
        <td><div class="tag-list">${renderTags(e.categories)}</div></td>
      </tr>
    `).join('');

    // Row click
    tbody.querySelectorAll('tr[data-id]').forEach(row => {
      row.addEventListener('click', () => openDetail(parseInt(row.dataset.id)));
    });

    renderPagination(data.total, data.pages);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="loading-cell">⚠️ Could not connect to backend. Make sure it's running on port 8000.<br><small>${err.message}</small></td></tr>`;
  }
}

// ── Pagination ────────────────────────────────────────────────────
function renderPagination(total, pages) {
  const pg = $('pagination');
  if (pages <= 1) { pg.innerHTML = ''; return; }

  const btns = [];

  // Prev
  if (state.page > 1)
    btns.push(btn('‹ Prev', state.page - 1));

  // Pages: always show first, last, current ±2
  const visible = new Set([1, pages]);
  for (let p = Math.max(1, state.page - 2); p <= Math.min(pages, state.page + 2); p++) visible.add(p);

  let last = 0;
  [...visible].sort((a, b) => a - b).forEach(p => {
    if (last && p - last > 1) btns.push('<span class="page-btn" disabled>…</span>');
    btns.push(btn(p, p, p === state.page));
    last = p;
  });

  // Next
  if (state.page < pages)
    btns.push(btn('Next ›', state.page + 1));

  pg.innerHTML = btns.join('');
  pg.querySelectorAll('.page-btn:not([disabled])').forEach(b => {
    b.addEventListener('click', () => {
      state.page = parseInt(b.dataset.p);
      loadEnterprises();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  });
}

function btn(label, p, active = false) {
  return `<button class="page-btn${active ? ' active' : ''}" data-p="${p}">${label}</button>`;
}

// ── Search & Filters ──────────────────────────────────────────────
let searchTimer;
$('main-search').addEventListener('input', e => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.search = e.target.value.trim();
    state.page = 1;
    loadEnterprises();
  }, 350);
});

$('clear-search').addEventListener('click', () => {
  $('main-search').value = '';
  state.search = '';
  state.page = 1;
  loadEnterprises();
});

$('apply-filters').addEventListener('click', () => {
  state.category = $('filter-category').value;
  state.district = $('filter-district').value;
  state.pincode = $('filter-pincode').value;
  state.place = $('filter-place').value.trim();
  state.nic_code = $('filter-nic').value.trim();
  state.page = 1;
  loadEnterprises();
});

$('clear-filters').addEventListener('click', () => {
  $('filter-category').value = '';
  $('filter-district').value = '';
  $('filter-pincode').value = '';
  $('filter-place').value = '';
  $('filter-nic').value = '';
  state.category = state.district = state.pincode = state.place = state.nic_code = '';
  $('main-search').value = '';
  state.search = '';
  state.page = 1;
  loadEnterprises();
});

// ── Populate filter dropdowns ────────────────────────────────────
async function loadFilters() {
  try {
    const res = await fetch(`${API}/filters`);
    const f = await res.json();

    populateSelect('filter-category', f.categories);
    populateSelect('filter-district', f.districts);
    populateSelect('filter-pincode', f.pincodes);
  } catch (e) {
    console.warn('Could not load filters:', e);
  }
}

function populateSelect(id, items) {
  const sel = $(id);
  const first = sel.options[0];
  sel.innerHTML = '';
  sel.appendChild(first);
  items.forEach(v => {
    const opt = document.createElement('option');
    opt.value = v; opt.textContent = v;
    sel.appendChild(opt);
  });
}

// ── Export CSV ────────────────────────────────────────────────────
$('export-btn').addEventListener('click', () => {
  const url = `${API}/export${buildQuery({ page: undefined, limit: undefined })}`;
  const a = document.createElement('a');
  a.href = url; a.download = 'enterprises.csv';
  a.click();
});

// ── Enterprise Detail Modal ───────────────────────────────────────
async function openDetail(id) {
  const overlay = $('modal-overlay');
  const body = $('modal-body');
  overlay.classList.add('open');
  body.innerHTML = `<div style="text-align:center;padding:3rem"><div class="spinner"></div></div>`;

  try {
    const [detRes, simRes] = await Promise.all([
      fetch(`${API}/enterprises/${id}`),
      fetch(`${API}/enterprises/${id}/similar?limit=4`),
    ]);
    const detail = await detRes.json();
    const similar = await simRes.json();

    body.innerHTML = `
      <div class="detail-header">
        <div class="detail-name">${escHtml(detail.enterprise_name)}</div>
        <div class="detail-meta">
          ${detail.district ? `<span>📍 ${escHtml(detail.district)}</span>` : ''}
          ${detail.pincode ? `<span>📮 ${escHtml(detail.pincode)}</span>` : ''}
          ${detail.registration_date ? `<span>📅 ${escHtml(detail.registration_date)}</span>` : ''}
          ${detail.sector ? `<span>🏭 ${escHtml(detail.sector)}</span>` : ''}
        </div>
      </div>

      ${detail.categories ? `
        <div class="detail-section">
          <h4>Industry Categories</h4>
          <div class="tag-list">${renderTags(detail.categories)}</div>
        </div>` : ''}

      ${detail.description ? `
        <div class="detail-section">
          <h4>Primary Activity</h4>
          <div class="detail-desc">${escHtml(detail.description)}</div>
        </div>` : ''}

      ${detail.address ? `
        <div class="detail-section">
          <h4>Address</h4>
          <div class="detail-desc" style="font-size:0.83rem">${escHtml(detail.address)}</div>
        </div>` : ''}

      ${detail.activities && detail.activities.length ? `
        <div class="detail-section">
          <h4>All NIC Activities (${detail.activities.length})</h4>
          <table class="activities-table">
            <thead><tr><th>NIC Code</th><th>Description</th></tr></thead>
            <tbody>
              ${detail.activities.map(a => `
                <tr>
                  <td>${escHtml(a.nic_code)}</td>
                  <td>${escHtml(a.nic_description)}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>` : ''}

      ${similar && similar.length ? `
        <div class="detail-section">
          <h4>Similar Enterprises</h4>
          <div class="similar-grid">
            ${similar.map(s => `
              <div class="similar-card" data-id="${s.id}">
                <div class="similar-name">${escHtml(s.enterprise_name)}</div>
                <div class="similar-desc">${escHtml(s.description || '')}</div>
                <div style="margin-top:6px">${renderTags(s.categories)}</div>
              </div>
            `).join('')}
          </div>
        </div>` : ''}
    `;

    // Similar card clicks
    body.querySelectorAll('.similar-card[data-id]').forEach(card => {
      card.addEventListener('click', () => openDetail(parseInt(card.dataset.id)));
    });

  } catch (err) {
    body.innerHTML = `<p style="color:var(--danger)">⚠️ Failed to load enterprise details: ${err.message}</p>`;
  }
}

$('modal-close').addEventListener('click', () => $('modal-overlay').classList.remove('open'));
$('modal-overlay').addEventListener('click', e => {
  if (e.target === $('modal-overlay')) $('modal-overlay').classList.remove('open');
});

// ── Analytics Page ────────────────────────────────────────────────
let analyticsLoaded = false;

async function loadAnalytics() {
  if (analyticsLoaded) return;
  analyticsLoaded = true;

  try {
    const res = await fetch(`${API}/stats`);
    const stats = await res.json();

    $('analytics-count').textContent = stats.total_enterprises.toLocaleString();

    // Stat cards
    $('stat-grid').innerHTML = `
      <div class="stat-card">
        <div class="stat-label">Total Enterprises</div>
        <div class="stat-value">${stats.total_enterprises.toLocaleString()}</div>
        <div class="stat-sub">Registered MSMEs in Kerala</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Districts</div>
        <div class="stat-value">${stats.total_districts}</div>
        <div class="stat-sub">Across the state</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Unique Pincodes</div>
        <div class="stat-value">${stats.total_pincodes}</div>
        <div class="stat-sub">Geographic coverage</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">NIC Activity Codes</div>
        <div class="stat-value">${stats.total_nic_codes}</div>
        <div class="stat-sub">Distinct NIC 5-digit codes</div>
      </div>
    `;

    // Chart palette
    const PALETTE = [
      '#6366f1', '#22d3ee', '#f59e0b', '#10b981', '#ef4444',
      '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#84cc16',
    ];

    const chartDefaults = {
      plugins: { legend: { labels: { color: '#94a3b8', font: { family: 'Inter' } } } },
      scales: {
        x: { ticks: { color: '#94a3b8', font: { family: 'Inter', size: 11 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
        y: { ticks: { color: '#94a3b8', font: { family: 'Inter', size: 11 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
      }
    };

    // Destroy old charts if reloading
    Object.values(state.charts).forEach(c => c.destroy());
    state.charts = {};

    // Pie – Categories
    const catKeys = Object.keys(stats.by_category).slice(0, 10);
    const catVals = catKeys.map(k => stats.by_category[k]);
    state.charts.pie = new Chart($('pie-category'), {
      type: 'doughnut',
      data: {
        labels: catKeys,
        datasets: [{
          data: catVals,
          backgroundColor: PALETTE,
          borderWidth: 2,
          borderColor: '#111827',
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        cutout: '60%',
        plugins: {
          legend: {
            position: 'right',
            labels: { color: '#94a3b8', font: { family: 'Inter', size: 12 }, padding: 14 }
          }
        }
      }
    });

    // Bar – Top pincodes
    const pinKeys = Object.keys(stats.by_pincode).slice(0, 10);
    const pinVals = pinKeys.map(k => stats.by_pincode[k]);
    state.charts.barPin = new Chart($('bar-pincode'), {
      type: 'bar',
      data: {
        labels: pinKeys,
        datasets: [{
          label: 'Enterprises',
          data: pinVals,
          backgroundColor: PALETTE.map(c => c + 'cc'),
          borderColor: PALETTE,
          borderWidth: 1, borderRadius: 4,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false, ...chartDefaults,
        plugins: { legend: { display: false } }
      }
    });

    // Bar – Sectors
    const secKeys = Object.keys(stats.by_sector);
    const secVals = secKeys.map(k => stats.by_sector[k]);
    state.charts.barSec = new Chart($('bar-sector'), {
      type: 'bar',
      data: {
        labels: secKeys,
        datasets: [{
          label: 'Enterprises',
          data: secVals,
          backgroundColor: '#6366f1cc',
          borderColor: '#6366f1',
          borderWidth: 1, borderRadius: 4,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false, ...chartDefaults,
        plugins: { legend: { display: false } },
        indexAxis: 'y',
      }
    });

  } catch (err) {
    $('stat-grid').innerHTML = `<p style="color:var(--danger);padding:1rem">⚠️ Could not load stats: ${err.message}</p>`;
  }
}

// ── Helpers ───────────────────────────────────────────────────────
function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function truncate(str, n) {
  if (!str) return '';
  return str.length > n ? str.slice(0, n) + '…' : str;
}

// ── Chatbot Logic ───────────────────────────────────────────────
const chatToggle = $('chat-toggle');
const chatWindow = $('chat-window');
const chatClose = $('chat-close');
const chatInput = $('chat-input');
const chatSend = $('chat-send');
const chatMessages = $('chat-messages');

chatToggle.addEventListener('click', () => chatWindow.classList.toggle('open'));
chatClose.addEventListener('click', () => chatWindow.classList.remove('open'));

async function sendChatMessage() {
  const text = chatInput.value.trim();
  if (!text) return;

  // Add user message
  appendMessage(text, 'user');
  chatInput.value = '';

  // Show typing or loading
  const loadingId = 'msg-' + Date.now();
  const loadingMsg = document.createElement('div');
  loadingMsg.className = 'msg bot loading';
  loadingMsg.id = loadingId;
  loadingMsg.textContent = '...';
  chatMessages.appendChild(loadingMsg);
  chatMessages.scrollTop = chatMessages.scrollHeight;

  try {
    const res = await fetch(`${API}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text })
    });
    const data = await res.json();

    loadingMsg.remove();
    appendMessage(data.response, 'bot');
  } catch (err) {
    loadingMsg.textContent = '⚠️ Sorry, I could not connect.';
  }
}

function appendMessage(text, type) {
  const div = document.createElement('div');
  div.className = `msg ${type}`;
  div.textContent = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

chatSend.addEventListener('click', sendChatMessage);
chatInput.addEventListener('keypress', e => {
  if (e.key === 'Enter') sendChatMessage();
});

// ── Boot ──────────────────────────────────────────────────────────
(async function init() {
  await Promise.all([loadFilters(), loadEnterprises()]);
})();
