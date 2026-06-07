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
let state = { expenses:[], rules:{}, settings:{people:[]}, totals:{}, you:0, spent:0 };
let lastReport = null;
let bannerDismissed = false;
let stmtFilter = localStorage.getItem('stmtFilter') || 'ALL';  // which statement is in view

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
// Sum charges in integer cents (exact to 2 decimals) — works even if the server
// is an older process that doesn't send a 'spent' field.
const spentOf = list => list.reduce((c,e)=>c+Math.round((e.amount||0)*100),0)/100;
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
async function refresh(){ Object.assign(state, await api.state()); await syncScopedTotals(); renderAll(); }
async function persistExpenses(){
  const r=await api.saveExpenses(state.expenses); state.totals=r.totals; state.you=r.you; state.spent=r.spent;
  await syncScopedTotals(); renderAll();
}
async function saveRule(matchKey, patch){
  const existing = state.rules[matchKey] || {matchKey, handling:null, category:null};
  state.rules[matchKey] = {...existing, ...patch};
  await api.saveRules(state.rules);
}
function renderAll(){ renderBanner(); renderReview(); renderLiveBar(); renderTotals(); renderPeople(); renderSplitwise(); }

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
const escAttr = s => String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;');
function statementSources(){ return [...new Set(state.expenses.map(e=>e.source))]; }
function visibleExpenses(){ return stmtFilter==='ALL' ? state.expenses : state.expenses.filter(e=>e.source===stmtFilter); }
function setStmtFilter(src){ stmtFilter=src; localStorage.setItem('stmtFilter',src); renderReview(); }

function renderReview(){
  const host = $('#reviewList');
  if(!state.expenses.length){
    host.innerHTML = `<div class="empty-note">No expenses yet. Upload a statement PDF above, or run the Claude Code companion (LAUNCH.md).</div>`;
    return;
  }
  const srcs = statementSources();
  if(stmtFilter!=='ALL' && !srcs.includes(stmtFilter)) stmtFilter='ALL';
  let bar = '';
  if(srcs.length){
    bar = `<div class="filters"><span class="flabel">Statement:</span>
      <button class="fpill ${stmtFilter==='ALL'?'on':''}" data-src="ALL">All (${state.expenses.length})</button>
      ${srcs.map(s=>`<button class="fpill ${stmtFilter===s?'on':''}" data-src="${escAttr(s)}">${s} (${state.expenses.filter(e=>e.source===s).length})</button>`).join('')}
    </div>`;
  }
  const list = visibleExpenses();
  const cats = [...new Set(list.map(e=>e.category))]
    .sort((a,b)=> catRank(a)-catRank(b) || a.localeCompare(b));
  let html = bar;

  const unassigned = list.filter(e=>e.status==='split' && !e.split.participants.length);
  if(unassigned.length){
    const dp = state.settings.defaultPartnerId ? personById(state.settings.defaultPartnerId) : null;
    html += `<div class="assign-note">
      <span>🤝 <b>${unassigned.length}</b> split ${unassigned.length!==1?'expenses have':'expense has'} nobody selected${dp?`, so ${dp.name} isn't being charged for ${unassigned.length!==1?'them':'it'}.`:'.'}</span>
      ${dp ? `<button class="btn btn-primary" onclick="assignDefaultToUnassigned()">Add ${dp.name} to ${unassigned.length}</button>`
           : `<button class="btn btn-ghost" onclick="showScreen('settings')">Set a default partner first</button>`}
    </div>`;
  }
  for(const cat of cats){
    const rows = list.filter(e=>e.category===cat);
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

function renderLiveBar(){
  const host = $('#liveBar'); if(!host) return;
  if(!state.expenses.length){ host.innerHTML=''; return; }
  const people = state.settings.people||[];
  // Always the grand totals across ALL statements, straight from the server (exact cents).
  const chips = [
    `<span class="live-chip spent"><span class="dot" style="background:var(--ink)"></span>Total spent <span class="amt2 mono">${money(spentOf(state.expenses))}</span></span>`
  ].concat(people.map(p=>
    `<span class="live-chip"><span class="dot" style="background:var(${personColor(p.id)})"></span>${p.name} owes <span class="amt2 mono">${money((state.totals||{})[p.id]||0)}</span></span>`
  ));
  host.innerHTML = `<div class="livebar">
    <div class="live-head">Running totals<span class="live-scope">all statements</span></div>
    <div class="live-chips">${chips.join('')}</div>
    <button class="btn btn-primary" onclick="showScreen('totals')">See Totals &amp; export →</button>
  </div>`;
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
      ${stmtFilter==='ALL' ? `<span class="src-tag">${e.source}</span>` : ''}
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
  const fp = ev.target.closest('.fpill');
  if(fp){ setStmtFilter(fp.dataset.src); return; }
  const btn = ev.target.closest('.act'); if(!btn) return;
  const id = ev.target.closest('.row').dataset.id;
  const e = state.expenses.find(x=>x.id===id); if(!e) return;
  const act = btn.dataset.act;
  if(act==='personal'){
    e.status='personal'; await persistExpenses();
  } else if(act==='always-personal'){
    const n=applyHandlingToMerchant(e.matchKey,'personal');
    await saveRule(e.matchKey,{handling:'personal'});
    await persistExpenses(); toast(`"${e.merchant}" is now personal on all ${n} ${n!==1?'expenses':'expense'} 🔒`);
  } else if(act==='split'){
    openSplit(id);
  } else if(act==='always-split'){
    const n=applyHandlingToMerchant(e.matchKey,'split');
    await saveRule(e.matchKey,{handling:'split'});
    await persistExpenses(); toast(`"${e.merchant}" is now split on all ${n} ${n!==1?'expenses':'expense'} ✨`);
  }
});

// Apply a handling ('personal'/'split') to EVERY existing expense of this merchant.
function applyHandlingToMerchant(matchKey, handling){
  const dp = state.settings.defaultPartnerId;
  let n=0;
  state.expenses.forEach(e=>{
    if(e.matchKey!==matchKey) return;
    n++;
    if(handling==='personal'){ e.status='personal'; }
    else { e.status='split'; e.split.shares='equal'; e.split.includeSelf=true;
           if(!e.split.participants.length && dp) e.split.participants=[dp]; }
  });
  return n;
}

async function assignDefaultToUnassigned(){
  const dp = state.settings.defaultPartnerId;
  if(!dp){ toast('Set a default partner in Settings first'); showScreen('settings'); return; }
  const list = visibleExpenses().filter(e=>e.status==='split' && !e.split.participants.length);
  list.forEach(e=>{ e.split.participants=[dp]; e.split.includeSelf=true; e.split.shares='equal'; });
  await persistExpenses();
  toast(`Added ${(personById(dp)||{}).name} to ${list.length} expense${list.length!==1?'s':''} ✨`,'good');
}

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
let totalsScope = 'ALL';     // 'ALL' or a statement source
let scopedTotals = null;     // server-computed totals for the scoped statement
let scopedYou = null;        // owner share for the scoped statement
let scopedSpent = null;      // total spent for the scoped statement
async function syncScopedTotals(){
  if(totalsScope==='ALL'){ scopedTotals=null; scopedYou=null; scopedSpent=null; return; }
  if(!statementSources().includes(totalsScope)){ totalsScope='ALL'; scopedTotals=null; scopedYou=null; scopedSpent=null; return; }
  const r = await (await fetch('/api/totals?source='+encodeURIComponent(totalsScope))).json();
  scopedTotals = r.totals; scopedYou = r.you; scopedSpent = r.spent;
}
async function setTotalsScope(src){ totalsScope=src; await syncScopedTotals(); renderTotals(); }
function srcQuery(){ return totalsScope==='ALL' ? '' : ('&source='+encodeURIComponent(totalsScope)); }

function renderTotals(){
  const srcs = statementSources();
  $('#scopeBar').innerHTML = srcs.length ? `<div class="filters" style="margin-bottom:6px">
      <span class="flabel">Export scope:</span>
      <button class="fpill ${totalsScope==='ALL'?'on':''}" data-tscope="ALL">All statements</button>
      ${srcs.map(s=>`<button class="fpill ${totalsScope===s?'on':''}" data-tscope="${escAttr(s)}">${s}</button>`).join('')}
    </div>` : '';

  const displayTotals = (totalsScope==='ALL') ? (state.totals||{}) : (scopedTotals||{});
  const scopeExp = (totalsScope==='ALL') ? state.expenses : state.expenses.filter(e=>e.source===totalsScope);
  const owedEntries = Object.entries(displayTotals);
  const totalOwed = owedEntries.reduce((s,[,v])=>s+v,0);
  const splitCount = scopeExp.filter(e=>e.status==='split' && e.split.participants.length).length;

  $('#celebrate').innerHTML = `<span class="em">${owedEntries.length?'✨':'🫙'}</span>
    <div>
      <h2>${owedEntries.length?'Nice — that all adds up':'Nothing to split yet'}</h2>
      <p>${owedEntries.length
          ? `${owedEntries.length} ${owedEntries.length>1?'people':'person'} owe you across ${splitCount} split expense${splitCount!==1?'s':''}${totalsScope!=='ALL'?' in '+totalsScope:''}.`
          : 'Tag some expenses as split on the Review tab.'}</p>
    </div>
    <div class="tot"><div class="big mono">${money(totalOwed)}</div><div class="lbl">Total owed to you</div></div>`;

  const host = $('#totalsList');
  const people = state.settings.people||[];
  const groups = [{id:0,name:'No group (direct)'}].concat(state.settings.splitwiseGroups||[]);
  const sq = srcQuery();
  const spentVal = spentOf(scopeExp);
  const scopeWord = totalsScope==='ALL' ? 'all statements' : totalsScope;
  const spentCard = `<div class="owe-card you-card">
      <span class="avatar" style="background:var(--ink)">$</span>
      <div class="who">Total spent</div>
      <div class="who-sub">everything you charged across ${scopeWord}</div>
      <div class="owe-amt"><div class="big">${money(spentVal)}</div><div class="lbl">spent</div></div>
    </div>`;
  if(!people.length){
    host.innerHTML = spentCard + `<p class="sub">Add people in Settings to split with someone.</p>`;
    $('#combinedBar').innerHTML='';
    return;
  }
  host.innerHTML = spentCard + people.map(p=>{
    const owe = displayTotals[p.id] || 0;
    const swBlock = state.settings.splitwiseToken ? `
        <div class="field-inline"><span>Splitwise:</span>
          <select class="select" id="grp-${p.id}">${groups.map(g=>`<option value="${g.id}">${g.name}</option>`).join('')}</select>
        </div>
        <button class="btn btn-sw" onclick="pushSummary('${p.id}')">↗ Push ${p.name} to Splitwise</button>` : '';
    return `<div class="owe-card">
      <span class="avatar" style="background:var(${personColor(p.id)})">${initial(p.name)}</span>
      <div class="who">${p.name}</div>
      <div class="who-sub">owes you for their share of split expenses</div>
      <div class="owe-amt"><div class="big">${money(owe)}</div><div class="lbl">owes you</div></div>
      <div class="owe-tools">
        <button class="btn btn-primary" onclick="location.href='/api/export/person.pdf?id=${encodeURIComponent(p.id)}${sq}'">⬇︎ PDF</button>
        <button class="btn btn-ghost" onclick="location.href='/api/export/person.csv?id=${encodeURIComponent(p.id)}${sq}'">CSV</button>
        ${swBlock}
      </div>
    </div>`;
  }).join('');

  $('#combinedBar').innerHTML = `
    <button class="btn btn-primary" onclick="location.href='/api/export/combined.pdf?x=1${sq}'">⬇︎ Combined PDF</button>
    <button class="btn btn-ghost" onclick="location.href='/api/export/combined.csv?x=1${sq}'">Combined CSV</button>`;
}

async function pushSummary(pid){
  const p = personById(pid);
  if(!state.settings.splitwiseToken){ toast('Connect Splitwise first (People & Settings) 🔌'); showScreen('settings'); return; }
  if(!p.splitwiseUserId){ toast(`Map ${p.name} to a Splitwise friend in Settings first`); showScreen('settings'); return; }
  const totals = (totalsScope==='ALL') ? (state.totals||{}) : (scopedTotals||{});
  const owe = totals[pid]||0;
  if(owe<=0){ toast(`${p.name}'s share is $0 — nothing to push`); return; }
  const scopeWord = totalsScope==='ALL' ? 'all statements' : totalsScope;
  const grpSel = document.getElementById('grp-'+pid);
  const grpName = grpSel ? grpSel.options[grpSel.selectedIndex].text : 'No group';
  if(!confirm(`Create ONE Splitwise expense charging ${p.name} $${owe.toFixed(2)} for ${scopeWord} (${grpName}), attach the PDF breakdown, and add a comment?\n\nThis creates a real expense in Splitwise.`)) return;
  toast('Pushing summary to Splitwise…');
  const res = await (await fetch('/api/splitwise/push_summary', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({personId: pid, groupId: Number(grpSel?grpSel.value:0), source: totalsScope})
  })).json();
  if(res.error){ toast('Push failed: '+res.error); return; }
  toast(`✅ Created Splitwise expense — ${p.name} owes $${(res.amount||owe).toFixed(2)} (PDF + comment attached)`,'good');
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
$('#screen-totals').addEventListener('click', ev=>{
  const b = ev.target.closest('[data-tscope]'); if(b) setTotalsScope(b.dataset.tscope);
});

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
