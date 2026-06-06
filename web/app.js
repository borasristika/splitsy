// web/app.js — Expense Splitter client
const api = {
  async state() { return (await fetch('/api/state')).json(); },
  async saveExpenses(expenses) {
    return (await fetch('/api/expenses', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({expenses})})).json();
  },
  async saveRules(rules) {
    return (await fetch('/api/rules', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({rules})})).json();
  },
  async saveSettings(settings) {
    return (await fetch('/api/settings', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({settings})})).json();
  },
  async upload(file) {
    const fd = new FormData(); fd.append('file', file);
    return (await fetch('/api/upload', {method:'POST', body: fd})).json();
  },
};

const state = { expenses: [], rules: {}, settings: {people: []}, totals: {} };
const CATEGORY_ORDER = ["Coffee","Grocery","Restaurants","Beauty","Shopping","Transport","Subscriptions","Miscellaneous"];

function personName(id) {
  const p = (state.settings.people || []).find(p => p.id === id);
  return p ? p.name : id;
}

async function refresh() {
  Object.assign(state, await api.state());
  render();
}

async function persistExpenses() {
  const res = await api.saveExpenses(state.expenses);
  state.totals = res.totals;
  render();
}

// ---------- rendering ----------
function render() {
  renderGroups();
  renderTotals();
  renderSettings();
}

function categoryRank(cat) {
  const i = CATEGORY_ORDER.indexOf(cat);
  return i === -1 ? CATEGORY_ORDER.length - 0.5 : i; // unknowns just before Miscellaneous
}

function renderGroups() {
  const container = document.getElementById('groups');
  container.innerHTML = '';
  const byCat = {};
  for (const e of state.expenses) (byCat[e.category] = byCat[e.category] || []).push(e);
  const cats = Object.keys(byCat).sort((a,b) => categoryRank(a) - categoryRank(b));
  for (const cat of cats) {
    const group = document.createElement('div');
    group.className = 'group';
    group.innerHTML = `<h3>${cat}</h3>`;
    for (const e of byCat[cat]) group.appendChild(rowEl(e));
    container.appendChild(group);
  }
  if (!state.expenses.length) {
    container.innerHTML = '<p>No expenses yet. Upload a statement PDF above, or run the Claude Code harness.</p>';
  }
}

function rowEl(e) {
  const row = document.createElement('div');
  row.className = 'row' + (e.status === 'personal' ? ' personal' : '');
  const splitInfo = e.status === 'split'
    ? `split: ${e.split.participants.map(personName).join(', ') || '(no one)'}`
    : 'personal';
  row.innerHTML = `
    <span>${e.date}</span>
    <span>${e.merchant} <small>${splitInfo}</small></span>
    <span class="amount">$${e.amount.toFixed(2)}</span>
    <span class="actions"></span>`;
  const actions = row.querySelector('.actions');
  actions.appendChild(btn('Personal', e.status==='personal', () => setPersonal(e, false)));
  actions.appendChild(btn('Always personal', false, () => setPersonal(e, true)));
  actions.appendChild(btn('Split…', e.status==='split', () => openSplit(e)));
  actions.appendChild(btn('Always split', false, () => setAlwaysSplit(e)));
  return row;
}

function btn(label, on, fn) {
  const b = document.createElement('button');
  b.textContent = label; if (on) b.classList.add('on');
  b.onclick = fn; return b;
}

// ---------- actions ----------
async function setPersonal(e, always) {
  e.status = 'personal';
  if (always) await saveRule(e.matchKey, {handling: 'personal'});
  await persistExpenses();
}

async function setAlwaysSplit(e) {
  e.status = 'split';
  await saveRule(e.matchKey, {handling: 'split'});
  await persistExpenses();
}

async function saveRule(matchKey, patch) {
  const existing = state.rules[matchKey] || {matchKey, handling: null, category: null};
  state.rules[matchKey] = {...existing, ...patch};
  await api.saveRules(state.rules);
}

// ---------- split editor ----------
let editing = null;
function openSplit(e) {
  editing = e;
  const dlg = document.getElementById('splitDialog');
  document.getElementById('splitTitle').textContent = `Split: ${e.merchant} ($${e.amount.toFixed(2)})`;
  const people = state.settings.people || [];
  const box = document.getElementById('splitPeople');
  box.innerHTML = people.map(p =>
    `<label><input type="checkbox" value="${p.id}" ${e.split.participants.includes(p.id)?'checked':''}> ${p.name}</label>`
  ).join('') || '<em>Add people in Settings first.</em>';
  document.getElementById('includeSelf').checked = e.split.includeSelf;
  dlg.showModal();
}

document.getElementById('splitForm').addEventListener('submit', async (ev) => {
  if (ev.submitter && ev.submitter.value === 'cancel') return;
  const checked = [...document.querySelectorAll('#splitPeople input:checked')].map(i => i.value);
  editing.status = 'split';
  editing.split.participants = checked;
  editing.split.includeSelf = document.getElementById('includeSelf').checked;
  editing.split.shares = 'equal';
  await persistExpenses();
});

// ---------- totals + exports ----------
function renderTotals() {
  const t = document.getElementById('totalsTable');
  const rows = Object.entries(state.totals)
    .map(([pid, amt]) => `<tr><td>${personName(pid)}</td><td>$${amt.toFixed(2)}</td></tr>`).join('');
  t.innerHTML = `<tr><th>Person</th><th>Owes you</th></tr>${rows || '<tr><td colspan="2">No split expenses yet.</td></tr>'}`;
  const box = document.getElementById('perPersonExports');
  box.innerHTML = '';
  for (const p of (state.settings.people || [])) {
    const wrap = document.createElement('div');
    wrap.className = 'person-export';
    const a = document.createElement('a');
    a.href = `/api/export/person.csv?id=${encodeURIComponent(p.id)}`;
    a.textContent = `Download ${p.name}'s CSV`;
    a.className = 'filebtn';
    wrap.appendChild(a);

    // Splitwise push (only if connected)
    if (state.settings.splitwiseToken) {
      const groups = state.settings.splitwiseGroups || [];
      const sel = document.createElement('select');
      sel.innerHTML = '<option value="0">No group (direct)</option>' +
        groups.map(g => `<option value="${g.id}">${g.name}</option>`).join('');
      const push = document.createElement('button');
      push.textContent = `Push ${p.name} to Splitwise`;
      push.onclick = () => pushToSplitwise(p, sel.value);
      wrap.appendChild(sel);
      wrap.appendChild(push);
    }
    box.appendChild(wrap);
  }
}

async function pushToSplitwise(person, groupId) {
  if (!person.splitwiseUserId) {
    alert(`Map ${person.name} to a Splitwise friend in Settings first.`);
    return;
  }
  const res = await (await fetch('/api/splitwise/push', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({personId: person.id, groupId: Number(groupId)})
  })).json();
  if (res.error) { alert('Push failed: ' + res.error); return; }
  let msg = `Pushed ${res.pushed}, skipped ${res.skipped} already-sent.`;
  if (res.errors && res.errors.length) {
    msg += `\nErrors:\n` + res.errors.map(e => `${e.merchant}: ${e.error}`).join('\n');
  }
  alert(msg);
  await refresh();
}

// ---------- settings ----------
function renderSettings() {
  const list = document.getElementById('peopleList');
  list.innerHTML = (state.settings.people || [])
    .map(p => `<li>${p.name} <button data-del="${p.id}">remove</button></li>`).join('');
  list.querySelectorAll('button[data-del]').forEach(b =>
    b.onclick = () => removePerson(b.dataset.del));
  const sel = document.getElementById('defaultPartner');
  sel.innerHTML = '<option value="">(none)</option>' +
    (state.settings.people || []).map(p =>
      `<option value="${p.id}" ${state.settings.defaultPartnerId===p.id?'selected':''}>${p.name}</option>`).join('');
  document.getElementById('statementFolder').value = state.settings.statementFolder || '';
  renderSplitwiseMapping();
}

function renderSplitwiseMapping() {
  const status = document.getElementById('swStatus');
  const box = document.getElementById('swMapping');
  const friends = state.settings.splitwiseFriends || [];
  if (!state.settings.splitwiseToken) {
    status.textContent = 'Not connected.';
    box.innerHTML = '';
    return;
  }
  status.textContent = `Connected ✓ (${friends.length} friends, ${(state.settings.splitwiseGroups||[]).length} groups). Map each person:`;
  box.innerHTML = '';
  for (const p of (state.settings.people || [])) {
    const row = document.createElement('div');
    row.className = 'map-row';
    const sel = document.createElement('select');
    sel.innerHTML = '<option value="">(not mapped)</option>' +
      friends.map(f => `<option value="${f.id}" ${p.splitwiseUserId===f.id?'selected':''}>${f.name}</option>`).join('');
    sel.onchange = async () => {
      p.splitwiseUserId = sel.value ? Number(sel.value) : null;
      await api.saveSettings(state.settings); await refresh();
    };
    row.innerHTML = `<span>${p.name} →</span>`;
    row.appendChild(sel);
    box.appendChild(row);
  }
}

document.getElementById('swConnectForm').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const token = document.getElementById('swToken').value.trim();
  if (!token) return;
  document.getElementById('swStatus').textContent = 'Connecting…';
  const res = await (await fetch('/api/splitwise/connect', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({token})
  })).json();
  if (res.error) {
    document.getElementById('swStatus').textContent = 'Connection failed: ' + res.error;
    return;
  }
  document.getElementById('swToken').value = '';  // don't keep the secret in the field
  await refresh();
});

async function removePerson(id) {
  state.settings.people = state.settings.people.filter(p => p.id !== id);
  if (state.settings.defaultPartnerId === id) state.settings.defaultPartnerId = null;
  await api.saveSettings(state.settings); await refresh();
}

document.getElementById('addPersonForm').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const name = document.getElementById('personName').value.trim();
  if (!name) return;
  const id = 'p' + Date.now();
  state.settings.people.push({id, name});
  document.getElementById('personName').value = '';
  await api.saveSettings(state.settings); await refresh();
});

document.getElementById('saveSettings').addEventListener('click', async () => {
  state.settings.defaultPartnerId = document.getElementById('defaultPartner').value || null;
  state.settings.statementFolder = document.getElementById('statementFolder').value.trim() || null;
  await api.saveSettings(state.settings); await refresh();
});

// ---------- upload ----------
document.getElementById('pdfInput').addEventListener('change', async (ev) => {
  const file = ev.target.files[0]; if (!file) return;
  document.getElementById('uploadStatus').textContent = 'Reading…';
  const res = await api.upload(file);
  showReport(res.report);
  await refresh();
  document.getElementById('uploadStatus').textContent =
    `Added ${res.report.added} of ${res.report.count} transactions.`;
});

function showReport(report) {
  const el = document.getElementById('report');
  el.classList.remove('hidden', 'bad');
  if (!report.reconciles) el.classList.add('bad');
  el.textContent = report.reconciles
    ? `✓ ${report.source}: ${report.count} transactions, total $${report.sumOfTransactions} reconciles with statement.`
    : `⚠ ${report.source}: parsed total $${report.sumOfTransactions} does NOT match statement total $${report.reportedTotal}. Review carefully.`;
}

// ---------- nav ----------
document.querySelectorAll('nav button').forEach(b => b.onclick = () => {
  document.querySelectorAll('nav button').forEach(x => x.classList.remove('active'));
  b.classList.add('active');
  document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
  document.getElementById('view-' + b.dataset.view).classList.remove('hidden');
});
document.getElementById('exportCombined').onclick =
  () => location.href = '/api/export/combined.csv';

refresh();
