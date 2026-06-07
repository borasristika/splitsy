/* ============================================================
   Splitsy client — mockup design wired to the real backend.
   Loaded as a classic script so inline onclick handlers resolve
   against these top-level (global) functions.
   ============================================================ */

/* ---------- API ---------- */
const api = {
  async state(){ return (await fetch('/api/state')).json(); },
  async saveExpenses(expenses){
    return (await fetch('/api/expenses',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({expenses})})).json();
  },
  async saveRules(rules){
    return (await fetch('/api/rules',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({rules})})).json();
  },
  async saveSettings(settings){
    return (await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({settings})})).json();
  },
  async upload(file){ const fd=new FormData(); fd.append('file',file);
    return (await fetch('/api/upload',{method:'POST',body:fd})).json(); },
  async swConnect(token){
    return (await fetch('/api/splitwise/connect',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({token})})).json();
  },
  async swPush(personId,groupId){
    return (await fetch('/api/splitwise/push',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({personId,groupId})})).json();
  },
};

/* ---------- state ---------- */
let state = { expenses:[], rules:{}, settings:{people:[]}, totals:{} };
let lastReport = null;
let bannerDismissed = false;

/* ---------- category + people metadata ---------- */
const CAT_META = {
  'Coffee':{key:'coffee',emoji:'☕'}, 'Grocery':{key:'grocery',emoji:'🛒'},
  'Restaurants':{key:'restaurants',emoji:'🍽️'}, 'Beauty':{key:'beauty',emoji:'💄'},
  'Shopping':{key:'shopping',emoji:'🛍️'}, 'Transport':{key:'transport',emoji:'🚗'},
  'Subscriptions':{key:'subscriptions',emoji:'🔁'}, 'Miscellaneous':{key:'misc',emoji:'🧩'},
};
const CAT_RANK = ['Coffee','Grocery','Restaurants','Beauty','Shopping','Transport','Subscriptions'];
const PALETTE = ['--shopping','--restaurants','--subscriptions','--grocery','--coffee','--transport','--beauty'];
const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

const $ = s => document.querySelector(s);
const money = n => '$' + Number(n||0).toFixed(2);
const personById = id => (state.settings.people||[]).find(p=>p.id===id);
const initial = name => (name||'?').trim().charAt(0).toUpperCase() || '?';
function catMeta(name){ return CAT_META[name] || {key:'misc', emoji:'🧩'}; }
function catRank(name){ if(name==='Miscellaneous') return 999; const i=CAT_RANK.indexOf(name); return i===-1?500:i; }
function personColor(id){ const i=(state.settings.people||[]).findIndex(p=>p.id===id); return PALETTE[(i<0?0:i)%PALETTE.length]; }
function fmtDate(iso){ if(!iso||iso.indexOf('-')<0) return iso||''; const [y,m,d]=iso.split('-'); return (MONTHS[(+m)-1]||'')+' '+d; }
function ruleFor(e){ const r=state.rules[e.matchKey]; return r?r.handling:null; }

function nameList(ids){
  const names = ids.map(id => (personById(id)||{}).name).filter(Boolean);
  if(names.length===0) return '';
  if(names.length===1) return names[0];
  if(names.length===2) return names[0]+' & '+names[1];
  return names.slice(0,-1).join(', ')+' & '+names[names.length-1];
}
function splitSubtitle(e){
  if(e.status==='personal') return {txt:'🔒 Just yours', cls:'personal-txt'};
  const ids = (e.split&&e.split.participants)||[];
  if(ids.length===0) return {txt:'👥 Split — pick people', cls:''};
  return {txt:'👥 Split with '+nameList(ids), cls:''};
}

/* ---------- load + persist ---------- */
async function refresh(){ Object.assign(state, await api.state()); renderAll(); }
async function persistExpenses(){ const r=await api.saveExpenses(state.expenses); state.totals=r.totals; renderAll(); }
async function saveRule(matchKey, patch){
  const existing = state.rules[matchKey] || {matchKey, handling:null, category:null};
  state.rules[matchKey] = {...existing, ...patch};
  await api.saveRules(state.rules);
}
function renderAll(){ renderBanner(); renderReview(); renderTotals(); renderPeople(); renderSplitwise(); }

/* ---------- banner ---------- */
function renderBanner(){
  const slot = $('#bannerSlot');
  if(!lastReport || bannerDismissed){ slot.innerHTML=''; return; }
  const r = lastReport;
  if(r.reconciles){
    slot.innerHTML = `<div class="banner ok">
      <span class="bi">✓</span>
      <div><b>${r.source}</b> — ${r.count} transactions, <span class="mono">${money(r.sumOfTransactions)}</span> · reconciles with your statement 🎉</div>
      <button class="x" aria-label="Dismiss" onclick="bannerDismissed=true;renderBanner()">×</button>
    </div>`;
  } else {
    slot.innerHTML = `<div class="banner warn">
      <span class="bi">!</span>
      <div><b>Heads up</b> — parsed total <span class="mono">${money(r.sumOfTransactions)}</span> doesn't match the statement's <span class="mono">${r.reportedTotal!=null?money(r.reportedTotal):'—'}</span>. Take a look before you split.</div>
      <button class="x" aria-label="Dismiss" onclick="bannerDismissed=true;renderBanner()">×</button>
    </div>`;
  }
}

/* ---------- review ---------- */
function renderReview(){
  const host = $('#reviewList');
  if(!state.expenses.length){
    host.innerHTML = `<div class="empty-note">No expenses yet. Upload a statement PDF above, or run the Claude Code companion (LAUNCH.md).</div>`;
    return;
  }
  const cats = [...new Set(state.expenses.map(e=>e.category))]
    .sort((a,b)=> catRank(a)-catRank(b) || a.localeCompare(b));
  let html='';
  for(const cat of cats){
    const rows = state.expenses.filter(e=>e.category===cat);
    const meta = catMeta(cat);
    const subtotal = rows.reduce((s,e)=>s+e.amount,0);
    html += `<section class="group">
      <div class="ghead" style="background:var(--${meta.key}-t)">
        <span class="cat-badge" style="color:var(--${meta.key})">${meta.emoji}</span>
        <span class="gname" style="color:var(--${meta.key})">${cat}</span>
        <span class="count-pill">${rows.length} item${rows.length>1?'s':''}</span>
        <span class="gsub mono" style="color:var(--${meta.key})">${money(subtotal)}</span>
      </div>
      ${rows.map(rowHTML).join('')}
    </section>`;
  }
  host.innerHTML = html;
}
function rowHTML(e){
  const meta = catMeta(e.category);
  const sub = splitSubtitle(e);
  const personal = e.status==='personal';
  const rule = ruleFor(e);
  return `<div class="row ${personal?'personal':''}" data-id="${e.id}">
    <div class="r-main">
      <span class="date mono">${fmtDate(e.date)}</span>
      <span class="merch" title="${(e.rawDescription||e.merchant||'').replace(/"/g,'&quot;')}">${e.merchant||''}</span>
      <span class="chip" style="background:var(--${meta.key}-t);color:var(--${meta.key})"><i style="background:var(--${meta.key})"></i>${e.category}</span>
    </div>
    <span class="amt">${money(e.amount)}</span>
    <div class="r-foot">
      <span class="split-sub ${sub.cls}">${sub.txt}</span>
      <div class="acts">
        <button class="act ${personal&&rule!=='personal'?'on mine':''}" data-act="personal">Personal</button>
        <button class="act rule ${rule==='personal'?'on mine':''}" data-act="always-personal">Always mine</button>
        <button class="act ${!personal?'on':''}" data-act="split">Split…</button>
        <button class="act rule ${rule==='split'?'on':''}" data-act="always-split">Always split</button>
      </div>
    </div>
  </div>`;
}

$('#reviewList').addEventListener('click', async ev=>{
  const btn = ev.target.closest('.act'); if(!btn) return;
  const id = ev.target.closest('.row').dataset.id;
  const e = state.expenses.find(x=>x.id===id); if(!e) return;
  const act = btn.dataset.act;
  if(act==='personal'){
    e.status='personal'; await persistExpenses();
  } else if(act==='always-personal'){
    e.status='personal'; await saveRule(e.matchKey,{handling:'personal'});
    await persistExpenses(); toast(`Got it — "${e.merchant}" will always be yours 🔒`);
  } else if(act==='split'){
    openSplit(id);
  } else if(act==='always-split'){
    e.status='split';
    if(!e.split.participants.length && state.settings.defaultPartnerId) e.split.participants=[state.settings.defaultPartnerId];
    await saveRule(e.matchKey,{handling:'split'});
    await persistExpenses(); toast(`Nice — "${e.merchant}" will always be split ✨`);
  }
});

/* ---------- split modal ---------- */
let modalDraft = null;
function openSplit(id){
  const e = state.expenses.find(x=>x.id===id); if(!e) return;
  const start = (e.split.participants&&e.split.participants.length) ? e.split.participants
              : (state.settings.defaultPartnerId ? [state.settings.defaultPartnerId] : []);
  modalDraft = { id, sel:new Set(start), includeMe: e.split.includeSelf!==false };
  renderModal();
}
function closeModal(){ $('#modalMount').innerHTML=''; modalDraft=null; }
function renderModal(){
  const e = state.expenses.find(x=>x.id===modalDraft.id);
  const meta = catMeta(e.category);
  const count = modalDraft.sel.size + (modalDraft.includeMe?1:0);
  const each = count>0 ? e.amount/count : 0;
  const people = state.settings.people||[];
  const peopleHTML = people.length ? people.map(p=>`
      <div class="pcheck ${modalDraft.sel.has(p.id)?'sel':''}" onclick="toggleSplitPerson('${p.id}')">
        <span class="avatar" style="background:var(${personColor(p.id)})">${initial(p.name)}</span>
        <span class="pname">${p.name}</span>
        <span class="box">${modalDraft.sel.has(p.id)?'✓':''}</span>
      </div>`).join('')
    : `<div class="split-result empty"><span>🙋</span><span>Add people in Settings first.</span></div>`;
  const result = count>0
    ? `<div class="split-result"><span>👏</span><span>${count} way${count>1?'s':''} — about <b>${money(each)}</b> each</span></div>`
    : `<div class="split-result empty"><span>🤔</span><span>Pick at least one person (or include yourself).</span></div>`;
  $('#modalMount').innerHTML = `
  <div class="overlay" onclick="if(event.target===this)closeModal()">
    <div class="modal" role="dialog" aria-modal="true" aria-label="Split expense">
      <h2>Split: ${e.merchant}</h2>
      <div class="m-amt">Total <b>${money(e.amount)}</b> · ${meta.emoji} ${e.category}</div>
      <div class="people-check">${peopleHTML}</div>
      <div class="includeme">
        <span class="avatar" style="background:var(--primary);width:30px;height:30px;font-size:12px;">Y</span>
        <div><div class="pname">Include me</div><div class="hint">Count yourself as one of the ways</div></div>
        <button class="toggle ${modalDraft.includeMe?'on':''}" aria-label="Include me" onclick="modalDraft.includeMe=!modalDraft.includeMe;renderModal()"></button>
      </div>
      ${result}
      <div class="modal-actions">
        <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
        <button class="btn btn-primary" onclick="saveSplit()">Save split</button>
      </div>
    </div>
  </div>`;
}
function toggleSplitPerson(pid){
  modalDraft.sel.has(pid) ? modalDraft.sel.delete(pid) : modalDraft.sel.add(pid);
  renderModal();
}
async function saveSplit(){
  const e = state.expenses.find(x=>x.id===modalDraft.id);
  e.status='split';
  e.split.participants=[...modalDraft.sel];
  e.split.includeSelf=modalDraft.includeMe;
  e.split.shares='equal';
  closeModal();
  await persistExpenses();
  const ids=e.split.participants;
  toast(ids.length? `Split saved — ${nameList(ids)} ${ids.length>1?'are':'is'} in ✨` : 'Saved as just yours');
}

/* ---------- totals ---------- */
function renderTotals(){
  const owedEntries = Object.entries(state.totals||{});
  const totalOwed = owedEntries.reduce((s,[,v])=>s+v,0);
  const splitCount = state.expenses.filter(e=>e.status==='split' && e.split.participants.length).length;
  const cel = $('#celebrate');
  cel.innerHTML = `<span class="em">${owedEntries.length?'✨':'🫙'}</span>
    <div>
      <h2>${owedEntries.length?'Nice — that all adds up':'Nothing to split yet'}</h2>
      <p>${owedEntries.length
          ? `${owedEntries.length} ${owedEntries.length>1?'people':'person'} owe you across ${splitCount} split expense${splitCount!==1?'s':''}.`
          : 'Tag some expenses as split on the Review tab.'}</p>
    </div>
    <div class="tot"><div class="big mono">${money(totalOwed)}</div><div class="lbl">Total owed to you</div></div>`;

  const host = $('#totalsList');
  const people = state.settings.people||[];
  if(!people.length){ host.innerHTML = `<p class="sub">Add people in Settings to see who owes you.</p>`; return; }
  const groups = [{id:0,name:'No group (direct)'}].concat(state.settings.splitwiseGroups||[]);
  host.innerHTML = people.map(p=>{
    const owe = state.totals[p.id] || 0;
    const swBlock = state.settings.splitwiseToken ? `
        <div class="field-inline"><span>Splitwise:</span>
          <select class="select" id="grp-${p.id}">${groups.map(g=>`<option value="${g.id}">${g.name}</option>`).join('')}</select>
        </div>
        <button class="btn btn-sw" onclick="pushSplitwise('${p.id}')">↗ Push ${p.name} to Splitwise</button>` : '';
    return `<div class="owe-card">
      <span class="avatar" style="background:var(${personColor(p.id)})">${initial(p.name)}</span>
      <div class="who">${p.name}</div>
      <div class="who-sub">owes you for their share of split expenses</div>
      <div class="owe-amt"><div class="big">${money(owe)}</div><div class="lbl">owes you</div></div>
      <div class="owe-tools">
        <button class="btn btn-ghost" onclick="location.href='/api/export/person.csv?id=${encodeURIComponent(p.id)}'">⬇︎ Download CSV</button>
        ${swBlock}
      </div>
    </div>`;
  }).join('');
}

async function pushSplitwise(pid){
  const p = personById(pid);
  if(!state.settings.splitwiseToken){ toast('Connect Splitwise first (People & Settings) 🔌'); showScreen('settings'); return; }
  if(!p.splitwiseUserId){ toast(`Map ${p.name} to a Splitwise friend in Settings first`); showScreen('settings'); return; }
  const groupId = Number((document.getElementById('grp-'+pid)||{}).value || 0);
  toast(`Pushing ${p.name}'s expenses…`);
  const res = await api.swPush(pid, groupId);
  if(res.error){ toast('Push failed: '+res.error); return; }
  toast(`Pushed ${res.pushed} to ${p.name}, skipped ${res.skipped} already sent ✅`,'good');
  if(res.errors && res.errors.length){
    alert('Some expenses could not be pushed:\n'+res.errors.map(e=>`• ${e.merchant}: ${e.error}`).join('\n'));
  }
  await refresh();
}

/* ---------- people & settings ---------- */
function renderPeople(){
  $('#peopleList').innerHTML = (state.settings.people||[]).map(p=>`
    <div class="person-row">
      <span class="avatar" style="background:var(${personColor(p.id)})">${initial(p.name)}</span>
      <span class="pname">${p.name}</span>
      ${p.id===state.settings.defaultPartnerId?'<span class="tag">Default</span>':''}
      <button class="x-btn" aria-label="Remove ${p.name}" onclick="removePerson('${p.id}')">×</button>
    </div>`).join('') || `<p class="desc">No people yet — add someone below.</p>`;
  const sel = $('#defPartner');
  sel.innerHTML = '<option value="">(none)</option>' + (state.settings.people||[]).map(p=>
    `<option value="${p.id}" ${p.id===state.settings.defaultPartnerId?'selected':''}>${p.name}</option>`).join('');
  $('#folder').value = state.settings.statementFolder || '';
}
async function addPerson(){
  const input = $('#newPerson');
  const name = input.value.trim(); if(!name) return;
  const id = 'p'+Date.now();
  state.settings.people.push({id, name});
  if(!state.settings.defaultPartnerId) state.settings.defaultPartnerId = id;
  input.value='';
  await api.saveSettings(state.settings); await refresh();
  toast(`Added ${name} 👋`);
}
async function removePerson(pid){
  state.settings.people = state.settings.people.filter(p=>p.id!==pid);
  if(state.settings.defaultPartnerId===pid) state.settings.defaultPartnerId = (state.settings.people[0]||{}).id || null;
  await api.saveSettings(state.settings); await refresh();
}
async function setDefaultPartner(pid){ state.settings.defaultPartnerId = pid||null; await api.saveSettings(state.settings); await refresh(); }
async function saveFolder(val){ state.settings.statementFolder = val.trim()||null; await api.saveSettings(state.settings); toast('Statement folder saved'); }

function renderSplitwise(){
  const host = $('#swArea');
  if(!state.settings.splitwiseToken){
    host.innerHTML = `
      <div class="sw-status off"><span class="sw-dot">○</span>Not connected</div>
      <div class="field">
        <label for="swKey">API key</label>
        <div class="connect-row">
          <input class="input" id="swKey" type="password" placeholder="Paste your Splitwise API key" />
          <button class="btn btn-primary" onclick="connectSw()">Connect</button>
        </div>
        <div class="help">Stored locally on this device — never committed or uploaded anywhere except Splitwise's own API.</div>
      </div>`;
    return;
  }
  const friends = state.settings.splitwiseFriends||[];
  host.innerHTML = `
    <div class="sw-status on"><span class="sw-dot">✓</span>Connected
      <button class="btn btn-ghost" style="margin-left:auto;padding:7px 13px;font-size:13px;" onclick="disconnectSw()">Disconnect</button>
    </div>
    <p class="desc" style="margin-bottom:10px">Match each person to their Splitwise friend.</p>
    ${(state.settings.people||[]).map(p=>`
      <div class="map-row">
        <span class="who"><span class="avatar" style="background:var(${personColor(p.id)});width:28px;height:28px;font-size:12px;">${initial(p.name)}</span>${p.name}</span>
        <select class="select" onchange="setSwMap('${p.id}', this.value)">
          <option value="">(not mapped)</option>
          ${friends.map(f=>`<option value="${f.id}" ${p.splitwiseUserId===f.id?'selected':''}>${f.name}</option>`).join('')}
        </select>
      </div>`).join('') || `<p class="desc">Add people first to map them.</p>`}`;
}
async function connectSw(){
  const token = ($('#swKey').value||'').trim(); if(!token){ toast('Paste your API key first'); return; }
  toast('Connecting to Splitwise…');
  const res = await api.swConnect(token);
  if(res.error){ toast('Connection failed: '+res.error); return; }
  await refresh();
  toast('Connected to Splitwise ✅','good');
}
async function disconnectSw(){
  state.settings.splitwiseToken=null; state.settings.splitwiseUserId=null;
  state.settings.splitwiseFriends=[]; state.settings.splitwiseGroups=[];
  await api.saveSettings(state.settings); await refresh();
}
async function setSwMap(pid, val){
  const p = personById(pid); if(!p) return;
  p.splitwiseUserId = val ? Number(val) : null;
  await api.saveSettings(state.settings); await refresh();
}

/* ---------- upload ---------- */
async function handleFile(file){
  if(!file) return;
  toast('Reading '+file.name+'…');
  const res = await api.upload(file);
  if(res.error){ toast('Upload failed: '+res.error); return; }
  lastReport = res.report; bannerDismissed = false;
  await refresh(); showScreen('review');
  toast(`Added ${res.report.added} of ${res.report.count} transactions`, res.report.reconciles?'good':undefined);
}
$('#pdfInput').addEventListener('change', e=>handleFile(e.target.files[0]));
$('#uploadBtn').addEventListener('click', ()=>$('#pdfInput').click());
const uz = $('#uploadZone');
['dragover','dragenter'].forEach(ev=>uz.addEventListener(ev,e=>{e.preventDefault();uz.style.borderColor='var(--primary)';}));
['dragleave','dragend'].forEach(ev=>uz.addEventListener(ev,e=>{e.preventDefault();uz.style.borderColor='';}));
uz.addEventListener('drop',e=>{ e.preventDefault(); uz.style.borderColor='';
  const f=[...e.dataTransfer.files].find(f=>f.type==='application/pdf'||f.name.toLowerCase().endsWith('.pdf')); handleFile(f); });

/* ---------- tabs + toast ---------- */
function showScreen(name){
  ['review','totals','settings'].forEach(s=> $('#screen-'+s).classList.toggle('hidden', s!==name));
  document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('on', t.dataset.screen===name));
  window.scrollTo({top:0});
}
document.querySelectorAll('.tab').forEach(t=>t.addEventListener('click',()=>showScreen(t.dataset.screen)));
$('#combinedBtn').addEventListener('click', ()=>location.href='/api/export/combined.csv');

function toast(msg, kind){
  const wrap = $('#toastWrap');
  const el = document.createElement('div');
  el.className = 'toast'+(kind==='good'?' good':'');
  el.textContent = (kind==='good'?'✅ ':'')+msg;
  wrap.appendChild(el);
  setTimeout(()=>{ el.style.transition='.25s'; el.style.opacity='0'; el.style.transform='translateY(10px)'; setTimeout(()=>el.remove(),260); }, 2600);
}
document.addEventListener('keydown', e=>{ if(e.key==='Escape' && modalDraft) closeModal(); });

/* ---------- init ---------- */
refresh();
