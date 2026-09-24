const app = document.querySelector('#app');
const notice = document.querySelector('#notice');
let data, conversation = {}, busy = false, categorySlug, subSlug;
const drafts = new Map();
let thread = localStorage.getItem('coach-thread') || `web-${crypto.randomUUID()}`;
localStorage.setItem('coach-thread', thread);
const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  const value = await response.json(); if (!response.ok) throw Error(value.error || '请求失败'); return value;
}
function markdown(raw = '') {
  raw = raw.replace(/<!--[\s\S]*?-->/g, '');
  return raw.split(/(```[\s\S]*?```)/g).map(part => {
    if (part.startsWith('```')) {
      const code = part.replace(/^```[^\n]*\n?/, '').replace(/```$/, '').trimEnd();
      return `<div class="codebox"><button data-copy>复制代码</button><pre><code>${esc(code)}</code></pre></div>`;
    }
    const lines=part.split('\n'); let table=false;
    return lines.map((line,index) => {
      if(line.trim().startsWith('|')){
        if(/^\s*\|[\s:|\-]+\|\s*$/.test(line))return '';
        const start=!table; table=true;
        const cells=line.trim().replace(/^\||\|$/g,'').split('|');
        const tag=start?'th':'td';
        const end=!lines[index+1]?.trim().startsWith('|'); if(end)table=false;
        return `${start?'<div class="table-scroll"><table>':''}<tr>${cells.map(c=>`<${tag}>${esc(c.trim())}</${tag}>`).join('')}</tr>${end?'</table></div>':''}`;
      }
      const h = line.match(/^(#{1,6}) (.*)$/);
      if(h) return `<h${Math.min(h[1].length+1,4)}>${esc(h[2])}</h${Math.min(h[1].length+1,4)}>`;
      if(!line.trim()) return '';
      return `<p>${esc(line).replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>').replace(/`([^`]+)`/g,'<code>$1</code>')}</p>`;
    }).join('');
  }).join('');
}
const progress = c => `<div class="coverage"><div class="row"><a href="#patterns/${esc(c.slug)}">${esc(c.title)}</a><small>${c.completed_count}/${c.total_count}</small></div><progress value="${c.completed_count}" max="${c.total_count}"></progress></div>`;
function overview() {
  const s=data.status, p=s.recommended_next, plan=data.plan||{}, target=plan.daily_target||{};
  const lessonItems=[...(plan.reviews||[]).map(x=>({...x,kind:'复习'})),...(plan.new_or_open||[]).map(x=>({...x,kind:'新题'}))];
  app.innerHTML=`<div class="eyebrow">YOUR LEARNING JOURNEY</div><h1>每一次练习，都有迹可循。</h1><p class="muted">回顾已走过的路，专注今天的下一步。</p>
  <section class="hero"><div><small>下一步 · ${conversation.selected_problem && conversation.phase !== 'complete' ? '继续当前练习' : '学习计划推荐'}</small><h2>${esc(conversation.selected_problem?.title || p?.title || '准备开始练习')}</h2><span class="muted">${p?.reason==='due-review'?'到期复习 · 尝试从记忆中独立推导':'根据你的本地学习记录安排'}</span></div><a class="button primary" href="#training">进入训练 →</a></section>
  <section class="panel lesson"><div class="row"><div><div class="eyebrow">TODAY'S LESSON</div><h2>今日课程：${target.review||0} 道复习 · ${target.new||0} 道新题</h2><p class="muted">先处理到期复习，再进入新题；进度始终从本地学习记录重新计算。</p></div><button class="primary" data-start>${conversation.selected_problem && conversation.phase !== 'complete'?'继续当前题':'开始今日课程'} →</button></div><div class="lesson-queue">${lessonItems.length?lessonItems.map((item,i)=>`<div class="item"><span class="badge">${i+1}</span> <strong>${esc(item.kind)}</strong> · #${esc(item.id||'—')} ${esc(item.title||item.slug)}<br><small>${esc(item.difficulty||'')}${item.next_review?` · 复习日期 ${esc(item.next_review)}`:''}</small></div>`).join(''):'<p class="muted">今日计划已完成，或还没有可用题目。</p>'}</div></section>
  <div class="stats">${[['已 AC',s.status_counts.AC||0,'不重复题目数'],['稳固掌握',s.mastery_counts.solid||0,'有完整 teach-back 证据'],['到期复习',s.due_reviews.length,'按本地复习日期计算'],['最近练习',s.latest_session?.split('/').pop()?.replace('.md','')||'暂无','已保存的学习记录']].map(([label,value,desc])=>`<div class="stat"><span>${label}</span><strong>${value}</strong><small>${desc}</small></div>`).join('')}</div>
  <div class="columns"><section class="panel"><div class="row"><h2>题型覆盖</h2><a href="#patterns">浏览模板 →</a></div><p class="muted">已完成代表题 / 课程题数 · 覆盖不等于掌握</p>${data.categories.map(progress).join('')}</section><div><section class="panel"><h2>待复习 <span class="badge">${s.due_reviews.length}</span></h2>${s.due_reviews.length?s.due_reviews.map(p=>`<div class="item"><button class="link" data-note="${esc(p.slug)}">#${p.id} ${esc(p.title)}</button><br><small>复习日期 ${p.next_review} · ${esc(p.mastery)}</small></div>`).join(''):'<p class="muted">暂时没有到期复习。</p>'}</section><section class="panel"><h2>最近练习记录</h2>${data.sessions.length?data.sessions.map((s,i)=>`<div class="item"><button class="link" data-session="${i}">${s.date} · 查看复盘 →</button></div>`).join(''):'<p class="muted">完成第一道题后，记录会出现在这里。</p>'}</section></div></div>`;
}
function patterns() {
  const c=data.categories.find(c=>c.slug===categorySlug)||data.categories[0]; categorySlug=c.slug;
  const sub=c.subpatterns.find(s=>s.slug===subSlug)||c.subpatterns[0]; subSlug=sub.slug;
  app.innerHTML=`<div class="row"><div><div class="eyebrow">PATTERN ATLAS</div><h1>理解模式，迁移解法。</h1><p class="muted">${data.categories.length} 个题型 · Python 骨架与适用边界</p></div><input id="search" aria-label="搜索题型、题号或关键词" placeholder="搜索题型、题号或关键词…"></div><div class="library"><aside class="catalog">${data.categories.map(k=>`<button data-category="${k.slug}" class="${k.slug===c.slug?'selected':''}">${esc(k.title)} <small>${k.completed_count}/${k.total_count}</small></button>`).join('')}</aside><section class="panel"><div class="row"><h2>${esc(c.title)}</h2><span class="badge">课程覆盖 ${c.completed_count}/${c.total_count}</span></div><div class="tabs">${c.subpatterns.map(s=>`<button data-sub="${s.slug}" class="${s.slug===sub.slug?'selected':''}">${esc(s.title)}</button>`).join('')}</div><p class="muted">当前子模式：${esc(sub.title)}。下方为题型共享讲解与骨架；现有卡片尚未逐一提供独立子模式模板。占位函数需按题意补全。</p><h3>本子模式代表题</h3>${sub.problems.map(p=>`<div class="item row"><span>#${p.id} ${esc(p.title)}</span><button data-note="${p.slug}">打开笔记</button></div>`).join('')}<button data-ask="请讲解${esc(c.title)}中的${esc(sub.title)}，先从适用条件和 invariant 开始。">向 Coach 提问 →</button><article>${markdown(c.content)}</article></section></div>`;
  document.querySelector('#search').addEventListener('input', e=>{
    const q=e.target.value.toLowerCase();
    document.querySelectorAll('[data-category]').forEach(b=>{const c=data.categories.find(c=>c.slug===b.dataset.category);b.hidden=!JSON.stringify(c).toLowerCase().includes(q);});
  });
}
const phaseLabel = {coaching:'推导与练习',debugging:'调试中',teach_back:'复述检查',awaiting_approval:'等待保存',complete:'本轮已结束',pattern_card:'阅读题型卡'};
function training() {
  const c=conversation, p=c.selected_problem, a=c.teach_back_assessment||{}, lesson=c.day_plan||data.plan||{}, next=lesson.recommended_next;
  const related=data.categories.filter(k=>k.subpatterns.some(s=>s.problems.some(x=>x.slug===p?.slug)));
  app.innerHTML=`<div class="row"><div><div class="eyebrow">FOCUS SESSION</div><h1>${esc(p?.title||'单题训练')}</h1><span class="badge">${phaseLabel[c.phase]||'准备开始'}</span> <small>${c.attempt_recorded?'本次练习已保存':'本次练习尚未保存'}</small></div><div class="actions"><button data-refresh>刷新会话</button><button data-new>新会话</button></div></div><div class="training"><section class="panel chat"><div class="messages" aria-live="polite">${c.messages?.length?c.messages.map(m=>`<div class="message ${m.role}"><small>${m.role==='human'?'YOU':'COACH'}</small><article>${markdown(m.content)}</article></div>`).join(''):'<div class="hero"><div><h2>从你的思路开始。</h2><p>选一道题，讲讲最直观的解法。Coach 会陪你一步步推导。</p><button class="primary" data-start>开始练习 →</button></div></div>'}</div>${c.pending_action?`<div class="approval"><h3>保存前确认</h3><p>${esc(c.pending_action.description)}</p><details><summary>查看具体变更</summary><pre>${esc(JSON.stringify(c.pending_action.arguments,null,2))}</pre></details><div class="actions"><button class="primary" data-decision="approve">${c.pending_action.action==='initialize_problem'?'创建题目':'保存练习'}</button><button data-decision="reject">暂不保存</button></div></div>`:''}<form id="composer" class="composer"><div class="actions"><button type="button" data-prompt="请给我一点提示">一点提示</button><button type="button" data-draft="请检查下面的代码：\n\n">检查代码</button><select id="judge" aria-label="报告判题结果"><option value="">报告判题结果</option><option>AC</option><option>WA</option><option>TLE</option><option>RE</option><option>MLE</option></select><button type="button" data-draft="下一题">下一题</button></div><label for="message" class="muted">你的思路、问题或代码</label><textarea id="message" placeholder="试着先说说你的想法…" required></textarea><div class="row"><small id="working">${busy?'Coach 正在处理，请稍候…':'Enter 换行 · Ctrl/⌘ + Enter 发送'}</small><button class="primary" id="send">发送 →</button></div></form></section><aside><section class="panel"><h2>今日课程</h2><p class="muted">${lesson.daily_target?`目标：${lesson.daily_target.review||0} 复习 · ${lesson.daily_target.new||0} 新题`:''}</p>${next?`<p><small>完成本题后建议</small><br><strong>${esc(next.title||next.slug)}</strong></p>`:'<p class="muted">当前没有下一项。</p>'}${c.attempt_recorded&&next?'<button class="primary" data-draft="下一题">进入下一题 →</button>':''}</section><section class="panel"><h2>本题信息</h2>${p?`<p>#${p.id||'—'} · ${esc(p.difficulty||'')}</p><a target="_blank" rel="noopener" href="https://leetcode.com/problems/${encodeURIComponent(p.slug)}/">打开 LeetCode ↗</a><p><small>上次记录：${esc(p.mastery||'未评估')}</small></p><button data-note="${esc(p.slug)}">查看笔记</button>`:'<p class="muted">开始后显示当前题目。</p>'}<h3>学习检查</h3>${[['Judge AC',c.judge_result==='AC'],['Invariant',a.invariant_correct],['时间与空间复杂度',a.complexity_correct],['边界条件',a.edge_case_identified],['适用范围',a.pattern_boundary_understood],['保存完成',c.attempt_recorded]].map(([label,done])=>`<div class="check">${done?'✓':'○'} ${label}</div>`).join('')}</section><section class="panel"><h2>相关模板</h2>${related.length?related.map(k=>`<details><summary>${esc(k.title)} · 查看模板</summary><article>${markdown(k.content)}</article></details>`).join(''):'<p class="muted">暂无关联题型。</p>'}<a href="#patterns">打开完整模板库 →</a></section></aside></div>`;
  const history = document.createElement('button'); history.textContent='历史会话'; history.dataset.history=''; document.querySelector('[data-new]').before(history);
  const form=document.querySelector('#composer');form.querySelector('textarea').value=drafts.get(thread)||'';
  form.querySelector('textarea').addEventListener('input',e=>drafts.set(thread,e.target.value));
  form.onsubmit=e=>{e.preventDefault();send({action:'message',message:form.querySelector('textarea').value});};
  document.querySelector('#message').onkeydown=e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();form.requestSubmit();}};
  document.querySelector('#judge').onchange=e=>{if(e.target.value)setDraft(e.target.value==='AC'?'/ac':`提交结果：${e.target.value}。\n失败输入或报错：`);};
  document.querySelector('.messages').scrollTop=1e9;
  setBusy();
}
function setDraft(value){drafts.set(thread,value);const input=document.querySelector('#message');if(input){input.value=value;input.focus();}}
function setBusy(){document.querySelectorAll('#composer button,#composer select,#composer textarea,[data-start],[data-decision],[data-new],[data-history],[data-refresh]').forEach(b=>b.disabled=busy);const w=document.querySelector('#working');if(w)w.textContent=busy?'Coach 正在处理，请稍候…':'Enter 换行 · Ctrl/⌘ + Enter 发送';}
async function send(payload){
  if(busy)return;
  busy=true;notice.textContent='';
  const activeThread=thread;
  if(payload.action==='message')conversation={...conversation,messages:[...(conversation.messages||[]),{role:'human',content:payload.message}]};
  render();setBusy();
  let complete=false, reader;
  const previews=new Map();
  try{
    const response=await fetch(`/api/conversation/stream?thread=${encodeURIComponent(activeThread)}`,{
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(!response.ok)throw Error((await response.json()).error||'请求失败');
    if(!response.body)throw Error('浏览器不支持流式读取');
    reader=response.body.getReader();const decoder=new TextDecoder();let buffer='';
    const consume=line=>{
      if(!line.trim())return;
      const event=JSON.parse(line);
      if(event.type==='error')throw Error(event.message);
      if(event.type==='preview'){
        let message=previews.get(event.id);
        if(!message){message={role:'ai',content:''};previews.set(event.id,message);conversation.messages=[...(conversation.messages||[]),message];}
        message.content=event.text;render();
        const working=document.querySelector('#working');if(working)working.textContent='正在接收回复 · 内容为未校验预览…';
      }
      if(event.type==='status'){const working=document.querySelector('#working');if(working)working.textContent=event.text;}
      if(event.type==='done'){conversation=event.conversation;complete=true;render();}
    };
    while(true){
      const {value,done}=await reader.read();buffer+=decoder.decode(value,{stream:!done});
      let newline;while((newline=buffer.indexOf('\n'))>=0){consume(buffer.slice(0,newline));buffer=buffer.slice(newline+1);}
      if(done){if(buffer.trim())consume(buffer);break;}
    }
    if(!complete)throw Error('流式连接中断。服务端可能仍在处理，请刷新会话确认状态，不要重复提交。');
    if(payload.action==='message')drafts.delete(activeThread);
    data=await api('/api/overview');render();
  }catch(e){
    notice.textContent=e.message;
    if(!complete){conversation={...conversation,messages:(conversation.messages||[]).filter(m=>!Array.from(previews.values()).includes(m))};render();}
  }finally{if(reader){await reader.cancel().catch(()=>{});reader.releaseLock();}busy=false;setBusy();}
}
function render(){if(!data)return;const [page,slug]=location.hash.slice(1).split('/');if(slug)categorySlug=slug;document.querySelectorAll('nav a').forEach(a=>a.classList.toggle('active',a.hash===`#${page||'overview'}`));if(page==='training')training();else if(page==='patterns')patterns();else overview();}
function read(title,content){document.querySelector('#reader-content').innerHTML=`<h2>${esc(title)}</h2>${markdown(content)}`;document.querySelector('#reader').showModal();}
document.querySelector('#close-reader').onclick=()=>document.querySelector('#reader').close();
document.addEventListener('click',async e=>{const b=e.target.closest('button');if(!b)return;try{
 if(b.hasAttribute('data-copy')){await navigator.clipboard.writeText(b.parentElement.querySelector('code').textContent);b.textContent='已复制';}
 if(b.dataset.category){categorySlug=b.dataset.category;subSlug=null;location.hash=`patterns/${categorySlug}`;render();}
 if(b.dataset.sub){subSlug=b.dataset.sub;render();}
 if(b.dataset.note){const n=await api(`/api/note?slug=${encodeURIComponent(b.dataset.note)}`);read(n.metadata.title,n.note);}
 if(b.dataset.session!==undefined){const s=data.sessions[Number(b.dataset.session)];read(s.date,s.content);}
 if(b.dataset.ask){drafts.set(thread,b.dataset.ask);location.hash='training';training();document.querySelector('#message').focus();}
 if(b.hasAttribute('data-start'))await send({action:'start'});
 if(b.dataset.decision)await send({action:b.dataset.decision});
 if(b.dataset.prompt)await send({action:'message',message:b.dataset.prompt});
 if(b.dataset.draft)setDraft(b.dataset.draft);
 if(b.hasAttribute('data-refresh')){conversation=await api(`/api/conversation?thread=${thread}`);data=await api('/api/overview');render();}
 if(b.hasAttribute('data-new')&&!busy){thread=`web-${crypto.randomUUID()}`;localStorage.setItem('coach-thread',thread);conversation={};render();}
 if(b.hasAttribute('data-history')&&!busy){const threads=await api('/api/threads');document.querySelector('#reader-content').innerHTML='<h2>历史会话</h2>'+threads.map(t=>`<div class="item"><button data-thread="${esc(t.id)}">${esc(t.title)}</button><br><small>${esc(t.id)}</small></div>`).join('');document.querySelector('#reader').showModal();}
 if(b.dataset.thread&&!busy){thread=b.dataset.thread;localStorage.setItem('coach-thread',thread);conversation=await api(`/api/conversation?thread=${encodeURIComponent(thread)}`);document.querySelector('#reader').close();render();}
 }catch(error){notice.textContent=error.message;}});
window.addEventListener('hashchange',render);
Promise.all([api('/api/overview'),api(`/api/conversation?thread=${thread}`)]).then(([d,c])=>{data=d;conversation=c;render();}).catch(e=>{notice.textContent=e.message;app.innerHTML='<p>无法加载学习空间。请确认本地服务正在运行，然后刷新页面。</p>';});
