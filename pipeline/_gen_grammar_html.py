# -*- coding: utf-8 -*-
"""NCE2 句法标注 → HTML 预览生成器

读取 标注数据库/_payload_grammar.json，生成自包含的 NCE2_句法标注.html
（三视图：词汇 / 语块 / 句型 + 语法点 + 单课概览；支持选课 / 搜索 / 语法点跳转）。
"""
import os, json

BASE = r"E:\04 少儿原版课程\06 新概念英语"
OUT = os.path.join(BASE, "标注数据库")
PAYLOAD = os.path.join(OUT, "_payload_grammar.json")
HTML = os.path.join(OUT, "NCE2_句法标注.html")

data = json.load(open(PAYLOAD, encoding="utf-8"))
payload_js = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

stat = data["stat"]
dist = data["distrib"]

# 取单课标题（从 lessons 概览）
lesson_rows = data.get("lessons", [])
lesson_titles = {r["课号"]: r.get("标题", "") for r in lesson_rows}

HTML_TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NCE2 句法标注预览</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root{
    --bg:#f5f6f8; --card:#ffffff; --ink:#1f2430; --sub:#6b7280;
    --line:#e6e8ec; --accent:#4f46e5; --accent2:#0ea5a4; --warn:#d97706;
    --chip:#eef2ff; --chip2:#e0f2f1; --chip3:#fef3c7; --bad:#fee2e2;
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:"Noto Sans SC",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
       background:var(--bg);color:var(--ink);font-size:14px;line-height:1.6}
  header{background:linear-gradient(135deg,#4f46e5,#0ea5a4);color:#fff;padding:20px 24px}
  header h1{margin:0;font-size:20px;font-weight:700}
  header p{margin:6px 0 0;opacity:.9;font-size:13px}
  .stats{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px}
  .stat{background:rgba(255,255,255,.16);border-radius:12px;padding:8px 14px;min-width:88px}
  .stat b{display:block;font-size:18px;font-weight:700}
  .stat span{font-size:12px;opacity:.92}
  .wrap{max-width:1180px;margin:0 auto;padding:18px 16px 60px}
  .toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:16px 0;
           background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 14px}
  select,input[type=text]{font-family:inherit;font-size:13px;padding:8px 10px;border:1px solid var(--line);
           border-radius:10px;background:#fff;color:var(--ink);outline:none}
  input[type=text]{flex:1;min-width:160px}
  select:focus,input:focus{border-color:var(--accent)}
  .tabs{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 14px}
  .tab{border:1px solid var(--line);background:var(--card);color:var(--sub);padding:8px 16px;border-radius:999px;
       cursor:pointer;font-weight:500;font-size:13px}
  .tab.on{background:var(--accent);color:#fff;border-color:var(--accent)}
  .panel{display:none}
  .panel.on{display:block}
  .card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:6px 4px;overflow:auto}
  table{border-collapse:collapse;width:100%;font-size:13px}
  th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
  th{position:sticky;top:0;background:#fafbfc;color:var(--sub);font-weight:600;font-size:12px;z-index:2;
     border-bottom:2px solid var(--line)}
  tr:hover td{background:#f9fafb}
  .chip{display:inline-block;background:var(--chip);color:#3730a3;border-radius:8px;padding:1px 8px;
        font-size:12px;margin:1px 2px}
  .chip2{background:var(--chip2);color:#0f766e}
  .chip3{background:var(--chip3);color:#92400e}
  .chipb{background:var(--bad);color:#b91c1c}
  .en{font-family:Georgia,"Times New Roman",serif}
  .zh{color:var(--sub)}
  .tag{font-size:11px;color:var(--sub);border:1px solid var(--line);border-radius:6px;padding:0 6px}
  .leaf{display:inline-block;background:#f1f5f9;border-radius:6px;padding:1px 7px;margin:1px;font-family:monospace;font-size:12px}
  .modal-bg{position:fixed;inset:0;background:rgba(15,23,42,.5);display:none;align-items:flex-start;
            justify-content:center;padding:40px 16px;overflow:auto;z-index:50}
  .modal-bg.on{display:flex}
  .modal{background:#fff;border-radius:18px;max-width:820px;width:100%;padding:20px 22px;box-shadow:0 20px 60px rgba(0,0,0,.25)}
  .modal h3{margin:0 0 4px;font-size:17px}
  .modal .en{font-size:15px;margin:4px 0}
  .modal .zh{margin:0 0 12px}
  .sec{margin:14px 0 6px;font-weight:700;color:var(--accent);font-size:13px}
  .close{float:right;cursor:pointer;color:var(--sub);font-size:20px;line-height:1}
  .tree{font-family:monospace;font-size:12px;background:#0f172a;color:#e2e8f0;border-radius:12px;
        padding:14px;white-space:pre-wrap;word-break:break-word;line-height:1.5}
  .muted{color:var(--sub);font-size:12px}
  .pill{display:inline-block;background:var(--chip);color:#3730a3;border-radius:999px;padding:2px 10px;font-size:12px;margin:2px}
  .grp{font-weight:700;margin:14px 0 4px;color:var(--ink)}
  .kp{display:inline-block;margin:2px}
  a.flt{color:var(--accent);cursor:pointer;text-decoration:underline}
  .foot{color:var(--sub);font-size:12px;margin-top:18px;text-align:center}
</style>
</head>
<body>
<header>
  <h1>新概念英语（二）· 句法标注预览</h1>
  <p>spaCy (en_core_web_md) + 规则层 · 三层标注：词汇 / 语块 / 句型 · 教学用途</p>
  <div class="stats" id="stats"></div>
</header>
<div class="wrap">
  <div class="toolbar">
    <label>课程
      <select id="lessonSel"></select>
    </label>
    <label>搜索（英文/中文/lemma）
      <input type="text" id="search" placeholder="如：went / 看戏 / theatre">
    </label>
    <span class="muted" id="countTip"></span>
  </div>

  <div class="tabs">
    <div class="tab on" data-p="tok">① 词汇层（词性·语法属性）</div>
    <div class="tab" data-p="chunk">② 语块层（短语·语块）</div>
    <div class="tab" data-p="sent">③ 句型层（句型·时态·语法点）</div>
    <div class="tab" data-p="gp">语法点清单</div>
    <div class="tab" data-p="les">单课概览</div>
  </div>

  <div class="panel on card" id="p_tok"><table id="t_tok"></table></div>
  <div class="panel card" id="p_chunk"><table id="t_chunk"></table></div>
  <div class="panel card" id="p_sent"><table id="t_sent"></table></div>
  <div class="panel card" id="p_gp"><table id="t_gp"></table></div>
  <div class="panel card" id="p_les"><table id="t_les"></table></div>
</div>

<div class="modal-bg" id="modalBg">
  <div class="modal" id="modal"></div>
</div>

<script>
const DATA = __PAYLOAD__;
const LEStitles = __TITLES__;
const $=id=>document.getElementById(id);
const esc=s=>String(s==null?'':s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const MAX=600;

// 统计卡
(function(){
  const s=DATA.stat, d=DATA.distrib;
  const items=[
    ['课程',s.lessons],['句子',s.sent],['词例',s.token],['语块',s.chunk],['语法点',s.grammarPoints],
    ['SVO',d.pattern.SVO||0],['SV',d.pattern.SV||0],['SVA',d.pattern.SVA||0],['SVP',d.pattern.SVP||0]
  ];
  $('stats').innerHTML=items.map(i=>`<div class="stat"><b>${i[1]}</b><span>${i[0]}</span></div>`).join('');
})();

// 课程下拉
(function(){
  const sel=$('lessonSel');
  let html='<option value="-1">全部课程</option>';
  const ls=[...new Set(DATA.tokens.map(t=>t.lesson))].sort((a,b)=>a-b);
  ls.forEach(n=>{ html+=`<option value="${n}">L${n}${LEStitles[n]?' · '+esc(LEStitles[n]):''}</option>`; });
  sel.innerHTML=html;
  sel.onchange=renderAll;
})();

$('search').oninput=renderAll;
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{
  document.querySelectorAll('.tab').forEach(x=>x.classList.remove('on'));
  document.querySelectorAll('.panel').forEach(x=>x.classList.remove('on'));
  t.classList.add('on'); $('p_'+t.dataset.p).classList.add('on'); renderAll();
});

function curLesson(){return $('lessonSel').value;}
function q(){return $('search').value.trim().toLowerCase();}
function matchText(o){
  const s=q(); if(!s) return true;
  const hay=[o.word,o.lemma,o.sentence,o.sentZh,o.text,o.textZh,o.zh,o.中文名,o.例句,o.译文]
            .filter(x=>x!=null).join(' ').toLowerCase();
  return hay.includes(s);
}

function renderAll(){
  const p=document.querySelector('.tab.on').dataset.p;
  if(p==='tok') renderTok();
  else if(p==='chunk') renderChunk();
  else if(p==='sent') renderSent();
  else if(p==='gp') renderGP();
  else if(p==='les') renderLes();
}

/* ① 词汇层 */
function renderTok(){
  const L=curLesson(), s=q();
  let rows=DATA.tokens.filter(t=>(L==='-1'||String(t.lesson)===L)&&matchText(t));
  $('countTip').textContent=`词例 ${rows.length} 行`+(rows.length>MAX?'（仅显示前 '+MAX+'）':'');
  rows=rows.slice(0,MAX);
  let h=`<thead><tr><th>课</th><th>句</th><th>词</th><th>lemma</th><th>词性</th><th>标签</th>
    <th>形态</th><th>句法角色</th><th>head</th><th>层</th><th>CEFR</th><th>例句</th></tr></thead><tbody>`;
  rows.forEach(t=>{
    const layer=t.layer?`<span class="chip">${esc(t.layer)}</span>`:'';
    const cefr=t.cefr?`<span class="chip2">${esc(t.cefr)}</span>`:'';
    h+=`<tr><td>${t.lesson}</td><td>${t.sentId}</td><td class="en">${esc(t.word)}</td><td class="en">${esc(t.lemma)}</td>
      <td>${esc(t.posZh||t.pos)}<div class="tag">${esc(t.tag)}</div></td>
      <td>${esc(t.tagZh||'')}</td>
      <td class="muted">${esc(t.morphZh||'')}</td>
      <td>${esc(t.depZh||t.dep)}<div class="tag">${esc(t.dep)}</div></td>
      <td class="en">${esc(t.head)}</td><td>${layer}</td><td>${cefr}</td>
      <td class="zh">${esc(t.sentence||'')}</td></tr>`;
  });
  h+=`</tbody>`;
  $('t_tok').innerHTML=h;
}

/* ② 语块层 */
function renderChunk(){
  const L=curLesson(), s=q();
  let rows=DATA.chunks.filter(c=>(L==='-1'||String(c.lesson)===L)&&matchText(c));
  $('countTip').textContent=`语块 ${rows.length} 行`+(rows.length>MAX?'（仅显示前 '+MAX+'）':'');
  rows=rows.slice(0,MAX);
  let h=`<thead><tr><th>课</th><th>句</th><th>类型</th><th>语块文本</th><th>内部结构式</th>
    <th>教学标签</th><th>中心词</th><th>例句</th></tr></thead><tbody>`;
  rows.forEach(c=>{
    h+=`<tr><td>${c.lesson}</td><td>${c.sentId}</td>
      <td><span class="chip3">${esc(c.chunkTypeZh||c.chunkType)}</span><div class="tag">${esc(c.chunkType)}</div></td>
      <td class="en">${esc(c.text)}</td>
      <td class="muted en">${esc(c.patternZh||'')}<div class="tag">${esc(c.pattern||'')}</div></td>
      <td>${esc(c.teachTag||'')}</td>
      <td class="en">${esc(c.headText)}<div class="tag">${esc(c.headPos)}</div></td>
      <td class="zh">${esc(c.sentence||'')}</td></tr>`;
  });
  h+=`</tbody>`;
  $('t_chunk').innerHTML=h;
}

/* ③ 句型层 */
function renderSent(){
  const L=curLesson(), s=q();
  let rows=DATA.sents.filter(r=>(L==='-1'||String(r.lesson)===L)&&matchText(r));
  $('countTip').textContent=`句子 ${rows.length} 行`;
  let h=`<thead><tr><th>课</th><th>句</th><th>句型</th><th>时态/体</th><th>语态</th><th>语气</th>
    <th>从句</th><th>语法点</th><th>英文</th><th>中文</th></tr></thead><tbody>`;
  rows.forEach(r=>{
    const gps=(r.grammarPointsZh||'').split('；').filter(Boolean)
              .map(g=>`<span class="kp"><span class="pill">${esc(g)}</span></span>`).join('');
    h+=`<tr style="cursor:pointer" onclick="openSent(${r.lesson},${r.sentId})">
      <td>${r.lesson}</td><td>${r.sentId}</td>
      <td><b>${esc(r.patternZh||r.pattern)}</b><div class="tag">${esc(r.pattern)}</div></td>
      <td>${esc(r.tense||'')}${r.aspect&&r.aspect!=='—'?'·'+esc(r.aspect):''}</td>
      <td>${esc(r.voice||'')}</td><td>${esc(r.sentType||'')}</td>
      <td class="muted">${esc(r.subClauses||'')}</td>
      <td>${gps}</td>
      <td class="en">${esc(r.text)}</td><td class="zh">${esc(r.textZh||'')}</td></tr>`;
  });
  h+=`</tbody>`;
  $('t_sent').innerHTML=h;
}

/* 语法点清单 */
function renderGP(){
  const s=q();
  let rows=DATA.grammar.filter(g=>matchText(g));
  $('countTip').textContent=`语法点 ${rows.length} 类`;
  let h=`<thead><tr><th>代码</th><th>中文名</th><th>分类</th><th>句数</th><th>首现课</th><th>例句</th><th>译文</th></tr></thead><tbody>`;
  rows.forEach(g=>{
    h+=`<tr><td class="en">${esc(g.语法点代码)}</td><td><b>${esc(g.中文名)}</b></td>
      <td><span class="tag">${esc(g.分类)}</span></td><td>${g.句数}</td><td>L${g.首现课}</td>
      <td class="en">${esc(g.例句)}</td><td class="zh">${esc(g.译文)}</td></tr>`;
  });
  h+=`</tbody>`;
  $('t_gp').innerHTML=h;
}

/* 单课概览 */
function renderLes(){
  const s=q();
  let rows=DATA.lessons.filter(r=>matchText(r));
  $('countTip').textContent=`单课 ${rows.length} 课`;
  let h=`<thead><tr><th>课</th><th>单元</th><th>标题</th><th>句数</th><th>词例</th><th>实词</th>
    <th>均句长</th><th>语块</th><th>语法点</th></tr></thead><tbody>`;
  rows.forEach(r=>{
    h+=`<tr><td>${r.课号}</td><td>U${r.单元}</td><td>${esc(r.标题)}</td><td>${r.句数}</td>
      <td>${r.词例数}</td><td>${r.实词数}</td><td>${r.平均句长}</td><td>${r.语块数}</td><td>${r.语法点数}</td></tr>`;
  });
  h+=`</tbody>`;
  $('t_les').innerHTML=h;
}

/* 句子详情弹窗 */
function openSent(lesson,sentId){
  const r=DATA.sents.find(x=>x.lesson===lesson&&x.sentId===sentId);
  if(!r) return;
  const toks=DATA.tokens.filter(t=>t.lesson===lesson&&t.sentId===sentId);
  const chs=DATA.chunks.filter(c=>c.lesson===lesson&&c.sentId===sentId);
  const tree=DATA.trees.find(t=>t.lesson===lesson&&t.sentId===sentId);
  const tokHtml=toks.map(t=>`<span class="leaf">${esc(t.word)} <small class="muted">${esc(t.pos)}</small></span>`).join(' ');
  const chHtml=chs.map(c=>`<span class="pill">${esc(c.chunkTypeZh||c.chunkType)}: ${esc(c.text)}</span>`).join(' ');
  const gps=(r.grammarPointsZh||'').split('；').filter(Boolean).map(g=>`<span class="pill">${esc(g)}</span>`).join('');
  const m=$('modal');
  m.innerHTML=`<span class="close" onclick="closeModal()">×</span>
    <h3>L${r.lesson} · 句 ${r.sentId} <span class="tag">${esc(r.pattern)} ${esc(r.patternZh||'')}</span></h3>
    <div class="en">${esc(r.text)}</div>
    <div class="zh">${esc(r.textZh||'')}</div>
    <div class="sec">句型 / 时态 / 语态 / 语气</div>
    <div>${esc(r.patternZh||r.pattern)} · ${esc(r.tense||'')}${r.aspect&&r.aspect!=='—'?'·'+esc(r.aspect):''} · ${esc(r.voice||'')} · ${esc(r.sentType||'')}</div>
    <div class="sec">语法点</div><div>${gps||'<span class="muted">无</span>'}</div>
    <div class="sec">从句</div><div>${esc(r.subClauses||'')||'<span class="muted">无</span>'}</div>
    <div class="sec">词性序列</div><div>${tokHtml}</div>
    <div class="sec">语块</div><div>${chHtml||'<span class="muted">无</span>'}</div>
    <div class="sec">依存/短语结构树（近似）</div><div class="tree">${esc(tree?tree.tree:'')}</div>`;
  $('modalBg').classList.add('on');
}
function closeModal(){$('modalBg').classList.remove('on');}
$('modalBg').onclick=e=>{ if(e.target===$('modalBg')) closeModal(); };

renderAll();
</script>
<div class="foot">数据来源：NCE2 全文 96 课 · spaCy en_core_web_md + 规则层 · 生成于 __GEN__</div>
</body>
</html>
"""

html = (HTML_TPL
        .replace("__PAYLOAD__", payload_js)
        .replace("__TITLES__", json.dumps(lesson_titles, ensure_ascii=False))
        .replace("__GEN__", data.get("generatedAt", "")))

with open(HTML, "w", encoding="utf-8") as f:
    f.write(html)
print("HTML %.2f MB -> %s" % (len(html) / 1048576, HTML))
