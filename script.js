// api.js is loaded before this file via <script src="api.js">

let PROJECTS = [];       // project names for picker — populated from API
const DAY_SHORT = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

let monthData        = [];  // array of week objects; index 0 = current displayed week
let currentWeekIndex = 0;
let _projectsById    = {}; // { id: name }
let _currentMonday   = null;
let _timesheetId     = null;
let _weekCache       = {}; // isoDate -> weekObj (avoids re-fetching)

// ─── API: load and transform a week ──────────────────────────────────────────

async function _fetchProjects() {
  if (PROJECTS.length > 0) return;
  try {
    const projs = await apiFetch('/projects/');
    if (!projs) return;
    PROJECTS.length = 0;
    projs.forEach(p => {
      _projectsById[p.id] = p.name;
      PROJECTS.push(p.name);
    });
  } catch (e) { console.warn('Projects load failed', e); }
}

async function _loadWeek(monday) {
  const iso = isoDate(monday);
  if (!_weekCache[iso]) {
    const data = await apiFetch(`/timesheets/?week_start=${iso}`);
    if (!data) return null;
    _weekCache[iso] = _transformTs(monday, data);
  }
  const weekObj = _weekCache[iso];
  monthData[0]  = weekObj;
  _timesheetId  = weekObj.id;
  _currentMonday = monday;
  return weekObj;
}

function _transformTs(monday, data) {
  const rowMap = new Map();
  (data.entries || []).forEach(entry => {
    const projName = _projectsById[entry.project_id] || `Project ${entry.project_id}`;
    const key = `${entry.project_id}::${entry.task || ''}`;
    if (!rowMap.has(key)) {
      rowMap.set(key, {
        project:   projName,
        projectId: entry.project_id,
        task:      entry.task || '',
        billable:  entry.billable,
        hours:     [0,0,0,0,0,0,0],
        notes:     ['','','','','','',''],
        entryIds:  {}
      });
    }
    const row = rowMap.get(key);
    const di  = dayIndex(entry.date);
    row.hours[di]   += entry.hours;
    row.notes[di]    = entry.notes || '';
    row.entryIds[di] = entry.id;
  });

  const sm = { draft: 'Draft', submitted: 'Pending', approved: 'Approved', rejected: 'Draft' };

  return {
    id:         data.id,
    label:      weekLabel(monday),
    startYear:  monday.getFullYear(),
    startMonth: monday.getMonth(),
    startDay:   monday.getDate(),
    weekStart:  isoDate(monday),
    status:     sm[data.status] || 'Draft',
    apiStatus:  data.status,
    rows:       [...rowMap.values()]
  };
}

// ─── Init ─────────────────────────────────────────────────────────────────────

async function initTimesheet() {
  if (!requireAuth()) return;

  await _fetchProjects();
  const monday = mondayOf();
  await _loadWeek(monday);
  renderTimesheetGrid(0);
  saveWeeksToStorage();
}

// ─── Render timesheet grid ────────────────────────────────────────────────────

function renderTimesheetGrid(weekIndex) {
  const week  = monthData[weekIndex];
  if (!week) return;
  const tbody = document.getElementById('ts-body');
  if (!tbody) return;
  tbody.innerHTML = '';

  const MONTH_SHORT = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const _wkStart    = new Date(week.startYear, week.startMonth, week.startDay);
  DAY_SHORT.forEach((d, i) => {
    const nameEl = document.getElementById(`ts-hdr-name-${i}`);
    const dateEl = document.getElementById(`ts-hdr-date-${i}`);
    if (nameEl) nameEl.textContent = d;
    if (dateEl) {
      const dd = new Date(_wkStart); dd.setDate(_wkStart.getDate() + i);
      dateEl.textContent = MONTH_SHORT[dd.getMonth()] + ' ' + dd.getDate();
    }
  });

  week.rows.forEach(row => appendRow(row));
  updateTotalsAndStats();

  const label = document.getElementById('week-label');
  if (label) label.textContent = week.label;

  const badge = document.getElementById('ts-status-badge');
  if (badge) {
    const map = { Approved: ['Approved', 'status-approved'], Pending: ['Pending Approval', 'status-pending'], Draft: ['Not Submitted', 'status-draft'] };
    const [text, cls] = map[week.status] || ['Not Submitted', 'status-draft'];
    badge.textContent = text;
    badge.className   = `status-pill ${cls}`;
  }
}

function appendRow(rowData) {
  const tbody = document.getElementById('ts-body');
  const tr    = document.createElement('tr');
  tr.className = 'ts-row';

  let html = `
    <td class="ts-project-cell">
      <button class="ts-project-btn" onclick="openProjectPicker(this)">${rowData.project}</button>
      <label class="ts-billable-label">
        <input type="checkbox" class="ts-billable-check" ${rowData.billable ? 'checked' : ''} onchange="updateTotalsAndStats()" />
        <span>Billable</span>
      </label>
    </td>`;

  rowData.hours.forEach((h, di) => {
    const noteText = rowData.notes?.[di] || '';
    const display  = h > 0 ? h + 'h' : '—';
    const hasnote  = noteText ? ' ts-cell-has-note' : '';
    html += `<td class="ts-hours-cell${di >= 5 ? ' ts-weekend' : ''}${hasnote}"
               data-day-idx="${di}"
               onclick="openCellPopover(this)" title="${noteText.replace(/"/g, '&quot;')}">
      <span class="ts-cell-display">${display}</span>
      ${noteText ? '<span class="ts-note-dot"></span>' : ''}
    </td>`;
  });

  const rowTotal = rowData.hours.reduce((s, h) => s + (h || 0), 0);
  html += `<td class="ts-row-total">${rowTotal > 0 ? rowTotal.toFixed(1) + 'h' : '—'}</td>`;
  html += `<td class="ts-delete-cell"><button class="ts-delete-btn" onclick="deleteRow(this)" title="Remove row">×</button></td>`;

  tr.innerHTML = html;
  tbody.appendChild(tr);
}

// ─── Totals & stats ───────────────────────────────────────────────────────────

function updateTotalsAndStats() {
  let grandTotal   = 0;
  let billableTotal = 0;
  const week = monthData[currentWeekIndex];
  if (!week) return;

  document.querySelectorAll('#ts-body tr.ts-row').forEach((tr, ri) => {
    const row = week.rows[ri];
    if (!row) return;
    const isBillable = tr.querySelector('.ts-billable-check')?.checked ?? true;
    const rowTotal   = row.hours.reduce((s, h) => s + (h || 0), 0);
    const totalCell  = tr.querySelector('.ts-row-total');
    if (totalCell) totalCell.textContent = rowTotal > 0 ? rowTotal.toFixed(1) + 'h' : '—';
    grandTotal += rowTotal;
    if (isBillable) billableTotal += rowTotal;
  });

  for (let di = 0; di < 7; di++) {
    const colTotal = week.rows.reduce((s, r) => s + (r.hours[di] || 0), 0);
    const el = document.getElementById(`ts-col-total-${di}`);
    if (el) el.textContent = colTotal > 0 ? colTotal.toFixed(1) + 'h' : '—';
  }

  const grandEl = document.getElementById('ts-grand-total');
  if (grandEl) grandEl.textContent = grandTotal > 0 ? grandTotal.toFixed(1) + 'h' : '—';

  const nonBillable = grandTotal - billableTotal;
  const utilPct     = grandTotal > 0 ? Math.round((billableTotal / grandTotal) * 100) : 0;

  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  set('ts-stat-billable',    billableTotal > 0 ? billableTotal.toFixed(1) + 'h' : '—');
  set('ts-stat-nonbillable', nonBillable   > 0 ? nonBillable.toFixed(1)   + 'h' : '—');
  set('ts-stat-total',       grandTotal    > 0 ? grandTotal.toFixed(1)    + 'h' : '—');
  set('ts-stat-util',        grandTotal    > 0 ? utilPct + '%'            : '—');
  set('sidebar-billable',    billableTotal > 0 ? billableTotal.toFixed(1) + 'h' : '—');
  set('sidebar-util',        grandTotal    > 0 ? utilPct + '%'            : '—');

  const barEl = document.getElementById('ts-bar-billable');
  if (barEl) barEl.style.width = utilPct + '%';

  const countEl = document.getElementById('ts-submit-count');
  if (countEl) {
    countEl.textContent = document.querySelectorAll('#ts-body tr.ts-row').length;
  }
}

// ─── Add / delete / copy ─────────────────────────────────────────────────────

function addTimeRow() {
  const firstProjName = PROJECTS[0] || '';
  const firstProjId   = parseInt(Object.keys(_projectsById).find(id => _projectsById[id] === firstProjName)) || null;
  const newRow = {
    project: firstProjName, projectId: firstProjId,
    task: '', billable: true,
    hours: [0,0,0,0,0,0,0], notes: ['','','','','','',''], entryIds: {}
  };
  monthData[currentWeekIndex].rows.push(newRow);
  appendRow(newRow);
  updateTotalsAndStats();
}

function deleteRow(btn) {
  const tr      = btn.closest('tr');
  const allRows = document.querySelectorAll('#ts-body tr.ts-row');
  const idx     = Array.from(allRows).indexOf(tr);
  if (idx >= 0) {
    const row = monthData[currentWeekIndex].rows[idx];
    if (row?.entryIds) {
      Object.values(row.entryIds).forEach(id => {
        apiFetch(`/timesheets/entries/${id}`, { method: 'DELETE' }).catch(console.error);
      });
    }
    monthData[currentWeekIndex].rows.splice(idx, 1);
    delete _weekCache[monthData[currentWeekIndex]?.weekStart];
  }
  tr.remove();
  updateTotalsAndStats();
}

function copyLastWeek() {
  // load previous week from API and copy project/task structure
  const prevMonday = new Date(_currentMonday);
  prevMonday.setDate(prevMonday.getDate() - 7);
  _loadWeekForCopy(prevMonday);
}

async function _loadWeekForCopy(prevMonday) {
  const iso  = isoDate(prevMonday);
  let prev   = _weekCache[iso];
  if (!prev) {
    const data = await apiFetch(`/timesheets/?week_start=${iso}`);
    if (!data) return;
    prev = _transformTs(prevMonday, data);
  }
  prev.rows.forEach(r => {
    const copy = {
      project: r.project, projectId: r.projectId,
      task: r.task, billable: r.billable,
      hours: [0,0,0,0,0,0,0], notes: ['','','','','','',''], entryIds: {}
    };
    monthData[currentWeekIndex].rows.push(copy);
    appendRow(copy);
  });
  updateTotalsAndStats();
}

// ─── Submit timesheet ─────────────────────────────────────────────────────────

async function submitTimesheet() {
  if (!_timesheetId) return;
  const week = monthData[currentWeekIndex];
  if (week?.apiStatus === 'submitted' || week?.apiStatus === 'approved') {
    alert('Timesheet is already submitted.');
    return;
  }
  try {
    await apiFetch(`/timesheets/${_timesheetId}/submit`, { method: 'POST' });
    week.status    = 'Pending';
    week.apiStatus = 'submitted';
    delete _weekCache[week.weekStart];
    const badge = document.getElementById('ts-status-badge');
    if (badge) { badge.textContent = 'Pending Approval'; badge.className = 'status-pill status-pending'; }
  } catch (e) {
    alert('Could not submit: ' + e.message);
  }
}

// ─── View switching (Week / Month) ───────────────────────────────────────────

function switchView(view, btn) {
  const gridView  = document.getElementById('ts-grid-view');
  const monthView = document.getElementById('ts-month-view');
  const weekNav   = document.getElementById('week-nav');

  if (view === 'week') {
    if (gridView)  gridView.style.display  = '';
    if (monthView) monthView.style.display = 'none';
    if (weekNav)   weekNav.style.display   = '';
    renderTimesheetGrid(currentWeekIndex);
  } else {
    if (gridView)  gridView.style.display  = 'none';
    if (monthView) monthView.style.display = '';
    if (weekNav)   weekNav.style.display   = 'none';
    renderMonthView();
  }
  document.querySelectorAll('.view-tab').forEach(t => t.classList.remove('active'));
  if (btn) btn.classList.add('active');
}

function renderMonthView() {
  const tbody = document.getElementById('month-body');
  if (!tbody) return;
  tbody.innerHTML = '';
  const sc = { Approved: 'status-approved', Pending: 'status-pending', Draft: 'status-draft' };

  const cached = Object.values(_weekCache).sort((a, b) => a.weekStart < b.weekStart ? 1 : -1);
  if (cached.length === 0) {
    tbody.innerHTML = '<tr><td colspan="10" style="color:var(--muted);padding:16px;">No weeks loaded yet.</td></tr>';
    return;
  }

  cached.forEach(week => {
    const wi = monthData.indexOf(week);
    const tr = document.createElement('tr');
    if (week.weekStart === isoDate(_currentMonday)) tr.classList.add('row-current-week');

    const dayTotals = [0,1,2,3,4,5,6].map(di => week.rows.reduce((s, r) => s + (r.hours[di] || 0), 0));
    const total     = dayTotals.reduce((s, h) => s + h, 0);
    const dayCells  = dayTotals.map(h => `<td>${h > 0 ? h.toFixed(1) + 'h' : '—'}</td>`).join('');

    tr.innerHTML = `
      <td><strong>${week.label}</strong></td>
      ${dayCells}
      <td><strong>${total.toFixed(1)}h</strong></td>
      <td><span class="status-pill ${sc[week.status] || 'status-draft'}">${week.status}</span></td>
      <td><button class="button btn-week-view" onclick="jumpToWeek('${week.weekStart}')">View</button></td>`;
    tbody.appendChild(tr);
  });
}

// ─── Week navigation ─────────────────────────────────────────────────────────

async function changeWeek(dir) {
  const next = new Date(_currentMonday);
  next.setDate(next.getDate() + dir * 7);
  await _loadWeek(next);
  renderTimesheetGrid(0);
}

async function jumpToWeek(isoStr) {
  const [y, m, d] = isoStr.split('-').map(Number);
  const monday = new Date(y, m - 1, d);
  await _loadWeek(monday);
  switchView('week');
  document.querySelectorAll('.view-tab').forEach((t, i) => t.classList.toggle('active', i === 0));
}

// ─── Project picker ───────────────────────────────────────────────────────────

let _activeProjectBtn = null;

function openProjectPicker(btn) {
  const picker = document.getElementById('ts-project-picker');
  if (!picker) return;
  if (_activeProjectBtn === btn && picker.style.display === 'block') {
    closeProjectPicker(); return;
  }
  _activeProjectBtn = btn;
  const current = btn.textContent.trim();
  picker.innerHTML = PROJECTS.map(p => `
    <button class="ts-picker-item${p === current ? ' ts-picker-active' : ''}"
            onclick="selectProject('${p.replace(/'/g,"\\'")}')">
      ${p}${p === current ? '<span class="ts-picker-check">✓</span>' : ''}
    </button>`).join('');

  const rect = btn.getBoundingClientRect();
  picker.style.display = 'block';
  const w = 200;
  let left = Math.max(8, Math.min(rect.left, window.innerWidth - w - 8));
  picker.style.left  = left + 'px';
  picker.style.top   = (rect.bottom + window.scrollY + 6) + 'px';
  picker.style.width = w + 'px';
}

function selectProject(name) {
  if (_activeProjectBtn) {
    _activeProjectBtn.textContent = name;
    const tr      = _activeProjectBtn.closest('tr');
    const allRows = document.querySelectorAll('#ts-body tr.ts-row');
    const rowIdx  = Array.from(allRows).indexOf(tr);
    if (rowIdx >= 0) {
      const row      = monthData[currentWeekIndex].rows[rowIdx];
      row.project    = name;
      row.projectId  = parseInt(Object.keys(_projectsById).find(id => _projectsById[id] === name)) || null;
    }
  }
  closeProjectPicker();
}

function closeProjectPicker() {
  const picker = document.getElementById('ts-project-picker');
  if (picker) picker.style.display = 'none';
  _activeProjectBtn = null;
}

document.addEventListener('click', e => {
  const picker = document.getElementById('ts-project-picker');
  if (!picker || picker.style.display === 'none') return;
  if (picker.contains(e.target)) return;
  if (e.target.classList.contains('ts-project-btn')) return;
  closeProjectPicker();
});

// ─── Cell notes popover ───────────────────────────────────────────────────────

let _activeTd = null;

function openCellPopover(target) {
  const cell = target.closest('.ts-hours-cell');
  if (!cell) return;
  const pop = document.getElementById('ts-cell-popover');
  if (pop && pop.style.display !== 'none' && _activeTd && _activeTd !== cell) closeCellPopover();

  const tr      = cell.closest('tr');
  const allRows = document.querySelectorAll('#ts-body tr.ts-row');
  const rowIdx  = Array.from(allRows).indexOf(tr);
  const dayIdx  = parseInt(cell.dataset.dayIdx);
  if (rowIdx < 0 || isNaN(dayIdx)) return;

  _activeTd = cell;
  const row     = monthData[currentWeekIndex].rows[rowIdx];
  const week    = monthData[currentWeekIndex];
  const hours   = row?.hours?.[dayIdx] || 0;
  const notes   = row?.notes?.[dayIdx] || '';
  const project = row?.project || '';
  const MS      = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const ds      = new Date(week.startYear, week.startMonth, week.startDay);
  const dd      = new Date(ds); dd.setDate(ds.getDate() + dayIdx);
  const day     = `${MS[dd.getMonth()]} ${dd.getDate()}`;

  document.getElementById('ts-pop-label').textContent = `${project} · ${day}`;
  document.getElementById('ts-pop-hours').value       = hours > 0 ? hours : '';
  document.getElementById('ts-pop-notes').value       = notes;

  const rect   = cell.getBoundingClientRect();
  const popW   = 260, popH = 180;
  let left     = Math.max(8, Math.min(rect.left + rect.width / 2 - popW / 2, window.innerWidth - popW - 8));
  const spaceBelow = window.innerHeight - rect.bottom;
  const top    = spaceBelow >= popH + 10 ? rect.bottom + window.scrollY + 10 : rect.top + window.scrollY - popH - 10;
  pop.style.left = left + 'px';
  pop.style.top  = top + 'px';
  pop.style.display = 'block';
  pop.dataset.rowIdx = rowIdx;
  pop.dataset.dayIdx = dayIdx;
  requestAnimationFrame(() => document.getElementById('ts-pop-hours')?.focus());
}

function closeCellPopover() {
  const pop = document.getElementById('ts-cell-popover');
  if (!pop || pop.style.display === 'none') return;

  const rowIdx = parseInt(pop.dataset.rowIdx);
  const dayIdx = parseInt(pop.dataset.dayIdx);
  const hours  = parseFloat(document.getElementById('ts-pop-hours')?.value) || 0;
  const notes  = document.getElementById('ts-pop-notes')?.value.trim() || '';

  const row = monthData[currentWeekIndex].rows[rowIdx];
  if (row) {
    const prevHours = row.hours[dayIdx];
    row.hours[dayIdx] = hours;
    if (!row.notes) row.notes = ['','','','','','',''];
    row.notes[dayIdx] = notes;
    // Save to API (fire-and-forget)
    _saveEntry(row, dayIdx, hours, notes, prevHours, monthData[currentWeekIndex]);
  }

  if (_activeTd) {
    _activeTd.querySelector('.ts-cell-display').textContent = hours > 0 ? hours + 'h' : '—';
    _activeTd.querySelector('.ts-note-dot')?.remove();
    _activeTd.classList.toggle('ts-cell-has-note', !!notes);
    _activeTd.title = notes;
    if (notes) {
      const dot = document.createElement('span');
      dot.className = 'ts-note-dot';
      _activeTd.appendChild(dot);
    }
  }
  updateTotalsAndStats();
  pop.style.display = 'none';
  _activeTd = null;
}

async function _saveEntry(row, dayIdx, hours, notes, prevHours, weekData) {
  const entryId = row.entryIds?.[dayIdx];
  const monday  = new Date(weekData.startYear, weekData.startMonth, weekData.startDay);
  const d       = new Date(monday); d.setDate(monday.getDate() + dayIdx);
  const dateIso = isoDate(d);

  try {
    if (hours > 0) {
      if (entryId) {
        await apiFetch(`/timesheets/entries/${entryId}`, {
          method: 'PATCH',
          body: { hours, notes: notes || null }
        });
      } else if (row.projectId) {
        const entry = await apiFetch('/timesheets/entries', {
          method: 'POST',
          body: {
            project_id: row.projectId,
            task: row.task || null,
            date: dateIso,
            hours,
            billable: row.billable,
            notes: notes || null
          }
        });
        if (entry) {
          if (!row.entryIds) row.entryIds = {};
          row.entryIds[dayIdx] = entry.id;
        }
      }
    } else if (entryId && prevHours > 0) {
      await apiFetch(`/timesheets/entries/${entryId}`, { method: 'DELETE' });
      delete row.entryIds[dayIdx];
    }
    delete _weekCache[weekData.weekStart];
  } catch (e) { console.error('Save entry failed:', e); }
}

document.addEventListener('click', e => {
  const pop = document.getElementById('ts-cell-popover');
  if (!pop || pop.style.display === 'none') return;
  if (pop.contains(e.target)) return;
  if (e.target.closest('.ts-hours-cell')) return;
  closeCellPopover();
});

// ─── Calendar dropdown ────────────────────────────────────────────────────────

let calMonth = new Date().getMonth(), calYear = new Date().getFullYear();

function buildCalendar() {
  const drop = document.getElementById('week-cal-drop');
  if (!drop) return;
  const DAYS   = ['Mo','Tu','We','Th','Fr','Sa','Su'];
  const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  const firstDow    = (new Date(calYear, calMonth, 1).getDay() + 6) % 7;
  const daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();

  function isoForDay(y, m, d) {
    const p = n => String(n).padStart(2, '0');
    return `${y}-${p(m + 1)}-${p(d)}`;
  }
  function weekStartFor(y, m, d) {
    const dt   = new Date(y, m, d);
    const dow  = dt.getDay();
    dt.setDate(dt.getDate() - (dow === 0 ? 6 : dow - 1));
    return isoDate(dt);
  }

  const curMonIso = _currentMonday ? isoDate(_currentMonday) : '';
  let cells = '';
  for (let i = 0; i < firstDow; i++) cells += `<div class="week-cal-cell empty"></div>`;
  for (let d = 1; d <= daysInMonth; d++) {
    const wiso = weekStartFor(calYear, calMonth, d);
    const sel  = wiso === curMonIso ? ' week-selected' : '';
    cells += `<div class="week-cal-cell${sel}" data-wiso="${wiso}">${d}</div>`;
  }
  drop.innerHTML = `
    <div class="week-cal-header">
      <button class="week-cal-nav" onclick="calNavMonth(event,-1)">&#8249;</button>
      <span>${MONTHS[calMonth]} ${calYear}</span>
      <button class="week-cal-nav" onclick="calNavMonth(event,1)">&#8250;</button>
    </div>
    <div class="week-cal-day-hdrs">${DAYS.map(d=>`<div class="week-cal-day-hdr">${d}</div>`).join('')}</div>
    <div class="week-cal-grid">${cells}</div>`;

  drop.querySelectorAll('.week-cal-cell[data-wiso]').forEach(cell => {
    cell.addEventListener('mouseenter', () => {
      drop.querySelectorAll(`.week-cal-cell[data-wiso="${cell.dataset.wiso}"]`).forEach(c => { if (!c.classList.contains('week-selected')) c.classList.add('week-hover'); });
    });
    cell.addEventListener('mouseleave', () => { drop.querySelectorAll('.week-cal-cell.week-hover').forEach(c => c.classList.remove('week-hover')); });
    cell.addEventListener('click', async e => {
      e.stopPropagation();
      const [y, m, d] = cell.dataset.wiso.split('-').map(Number);
      await jumpToWeek(cell.dataset.wiso);
      drop.style.display = 'none';
      document.removeEventListener('click', closeCal);
    });
  });
}

function calNavMonth(e, dir) {
  e.stopPropagation();
  calMonth += dir;
  if (calMonth < 0)  { calMonth = 11; calYear--; }
  if (calMonth > 11) { calMonth = 0;  calYear++; }
  buildCalendar();
}

function toggleCalendar(e) {
  e.stopPropagation();
  const drop = document.getElementById('week-cal-drop');
  if (drop.style.display === 'none') {
    if (_currentMonday) { calMonth = _currentMonday.getMonth(); calYear = _currentMonday.getFullYear(); }
    buildCalendar(); drop.style.display = '';
    setTimeout(() => document.addEventListener('click', closeCal), 0);
  } else { drop.style.display = 'none'; document.removeEventListener('click', closeCal); }
}

function closeCal(e) {
  const drop = document.getElementById('week-cal-drop');
  if (drop && !drop.contains(e.target) && e.target.id !== 'cal-btn') {
    drop.style.display = 'none'; document.removeEventListener('click', closeCal);
  }
}

// ─── Week storage (kept for compatibility) ────────────────────────────────────

function saveWeeksToStorage() {
  try { localStorage.setItem('timeflow_current_week', _currentMonday ? isoDate(_currentMonday) : ''); } catch(e) {}
}

// ─── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => { initTimesheet(); });
