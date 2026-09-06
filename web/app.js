const $ = (id) => document.getElementById(id);
let token = '', documents = [], selected = new Set(), busy = false;
const headers = () => token ? {Authorization: `Bearer ${token}`} : {};
async function api(path, options = {}) {
  const response = await fetch(path, {...options, headers: {...headers(), ...options.headers}});
  if (!response.ok) { let detail = 'Request failed'; try { detail = (await response.json()).detail || detail; } catch {} throw Error(typeof detail === 'string' ? detail : 'Please check your input.'); }
  return response;
}
async function loadDocuments() {
  documents = await (await api('/api/documents')).json();
  selected = new Set([...selected].filter(id => documents.some(d => d.id === id)));
  $('documents').replaceChildren();
  for (const doc of documents) {
    const row = document.createElement('div'); row.className = 'doc';
    const check = document.createElement('input'); check.type = 'checkbox'; check.id = 'doc-' + doc.id; check.checked = selected.has(doc.id);
    check.onchange = () => { check.checked ? selected.add(doc.id) : selected.delete(doc.id); updateScope(); };
    const label = document.createElement('label'); label.htmlFor = check.id; label.textContent = doc.title;
    const sub = document.createElement('small'); sub.textContent = `${doc.kind.toUpperCase()} · ${doc.chunks} chunks`; label.append(sub);
    row.append(check, label);
    if (token) { const remove = document.createElement('button'); remove.className='delete'; remove.textContent='×'; remove.setAttribute('aria-label', `Delete ${doc.title}`); remove.onclick=async()=>{ if(confirm(`Delete ${doc.title} from the index?`)) try { await api('/api/documents/'+doc.id,{method:'DELETE'}); await loadDocuments(); } catch(e){$('status').textContent=e.message;} }; row.append(remove); }
    $('documents').append(row);
  }
  updateScope();
}
function updateScope() { $('scope').textContent = selected.size ? `Searching ${selected.size} selected source${selected.size>1?'s':''}` : `Searching all ${documents.length} sources`; }
function showEvidence(source) {
  $('evidence').classList.remove('hidden'); $('evidence-title').textContent=source.title;
  $('evidence-meta').textContent=`${source.kind.toUpperCase()} · ${source.page ? 'Page '+source.page+' · ' : ''}Similarity ${source.score} · Chunk ${source.chunk+1}`;
  $('evidence-text').textContent=source.text;
  const valid = /^https:\/\//i.test(source.url || ''); $('evidence-url').classList.toggle('hidden',!valid); $('evidence-url').href=valid?source.url:'#';
}
function renderAnswer(element, text, sources) {
  text = text.replace(/【(\d+)】/g, '[$1]');
  element.replaceChildren(); const parts=text.split(/(\[\d+\])/g);
  for(const part of parts){ const match=/^\[(\d+)\]$/.exec(part); const source=match&&sources.find(s=>s.citation===Number(match[1])); if(source){const b=document.createElement('button');b.className='citation';b.textContent=part;b.title=source.title;b.onclick=()=>showEvidence(source);element.append(b);}else element.append(document.createTextNode(part)); }
}
async function ask(question) {
  if(busy||!question.trim())return; busy=true; $('send').disabled=true; $('welcome').classList.add('hidden'); $('status').textContent='Retrieving evidence…'; $('question').value='';
  const q=document.createElement('div'); q.className='message question';q.textContent=question;$('messages').append(q);
  const a=document.createElement('div');a.className='message answer';const label=document.createElement('span');label.className='message-label';label.textContent='✳ ATLAS';const content=document.createElement('div');a.append(label,content);$('messages').append(a);
  let answer='',sources=[];
  try {
    const r=await api('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question,document_ids:[...selected]})});
    const reader=r.body.getReader(), decoder=new TextDecoder();let buffer='';
    while(true){const {value,done}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});let cut;
      while((cut=buffer.indexOf('\n\n'))>=0){const frame=buffer.slice(0,cut);buffer=buffer.slice(cut+2);const type=frame.match(/^event: (.*)$/m)?.[1];const dataLine=frame.match(/^data: (.*)$/m)?.[1];if(!dataLine)continue;const data=JSON.parse(dataLine);
        if(type==='sources'){sources=data;$('status').textContent=`Found ${sources.length} relevant excerpts. Preparing answer…`;}
        if(type==='token'){answer+=data;renderAnswer(content,answer,sources);$('status').textContent='Answer streaming…';}
        if(type==='error')throw Error(data);
        if(type==='done'){const meta=document.createElement('div');meta.className='meta';meta.textContent=`${data.sources} retrieved excerpts · ${(data.duration_ms/1000).toFixed(1)}s · Click a citation to inspect evidence`;a.append(meta);$('status').textContent='';}
      }
    }
  }catch(e){$('status').textContent=e.message;if(!answer)content.textContent='No answer was generated.';}finally{busy=false;$('send').disabled=false;}
}
$('chat-form').onsubmit=e=>{e.preventDefault();ask($('question').value);};
$('question').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();ask($('question').value);}};
document.querySelectorAll('[data-question]').forEach(b=>b.onclick=()=>ask(b.dataset.question));
$('new-chat').onclick=()=>{if(busy)return;$('messages').replaceChildren();$('welcome').classList.remove('hidden');$('status').textContent='';};
$('close-evidence').onclick=()=>$('evidence').classList.add('hidden');
for(const id of ['add-source','add-small'])$(id).onclick=()=>$('source-dialog').showModal();
$('close-source').onclick=()=>$('source-dialog').close();
$('settings').onclick=()=>$('settings-dialog').showModal();
$('close-settings').onclick=()=>$('settings-dialog').close();
$('settings-form').onsubmit=async e=>{e.preventDefault();token=$('owner-token').value;$('owner-token').value='';$('settings-dialog').close();await loadDocuments();$('status').textContent='Access token set. Protected actions will verify it on the server.';};
$('sign-out').onclick=async()=>{token='';$('owner-token').value='';$('settings-dialog').close();$('messages').replaceChildren();$('evidence').classList.add('hidden');await loadDocuments();};
$('source-type').onchange=()=>{const pdf=$('source-type').value==='pdf';$('file-label').classList.toggle('hidden',!pdf);$('url-label').classList.toggle('hidden',pdf);};
$('source-form').onsubmit=async e=>{e.preventDefault();$('ingest-button').disabled=true;$('ingest-status').textContent='Extracting, chunking, and indexing…';try{let body,h={};const kind=$('source-type').value;if(kind==='pdf'){const f=$('source-file').files[0];if(!f)throw Error('Select a PDF first.');body=new FormData();body.append('file',f);}else{h={'Content-Type':'application/json'};body=JSON.stringify({value:$('source-value').value});}const result=await(await api('/api/ingest/'+kind,{method:'POST',headers:h,body})).json();$('ingest-status').textContent=`Indexed ${result.chunks} chunks. Ready to search.`;await loadDocuments();}catch(e){$('ingest-status').textContent=e.message;}finally{$('ingest-button').disabled=false;}};
$('api-link').href='/docs';
async function init(){try{const health=await(await api('/api/health')).json();$('mode').textContent=health.mode==='demo'?'Demo index · Qdrant':'Semantic index · Qdrant';if(health.mode==='demo'||!health.llm_configured)$('mode-note').textContent='Demo shows retrieved excerpts without an LLM.';await loadDocuments();}catch(e){$('status').textContent='Could not connect: '+e.message;}}
init();
