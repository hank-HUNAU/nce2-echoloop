# -*- coding: utf-8 -*-
"""NCE2 每课任务单生成器（P0，儿童自学线 A 框架）

产出：
  标注数据库/NCE2_听写选句清单.csv   —— ≤10 词听写池（CSV 正典）
  任务单/index.html                  —— 96 课导航 + 完成进度
  任务单/L01.html … L96.html         —— 平板点选 + 打印双版式任务单

数据源：
  标注数据库/NCE2_句型标注.csv · NCE2_语块标注.csv · NCE2_词性标注.csv
  词汇数据/单课/L{nn}_*.csv · data/nce2_lessons.json · data/nce2_zh.json
"""
import os, csv, json, glob, html, collections, datetime, urllib.parse

BASE = r"E:\04 少儿原版课程\06 新概念英语"
DATA = os.path.join(BASE, "data")
ANNO = os.path.join(BASE, "标注数据库")
VOCAB = os.path.join(BASE, "词汇数据")
OUT = os.path.join(BASE, "任务单")
AUDIO_DIR = "../NCE2-英音/"

MAX_DICT_PER_LESSON = 5      # 每课听写题上限
SHORT_WORDS = 10             # 听写句词数上限

# ---------------------------------------------------------------- 数据装载
def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

lessons_meta = {l["no"]: l for l in load_json(os.path.join(DATA, "nce2_lessons.json"))["lessons"]}
zh = {l["no"]: l for l in load_json(os.path.join(DATA, "nce2_zh.json"))["lessons"]}

def load_csv(name):
    with open(os.path.join(ANNO, name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

sents = load_csv("NCE2_句型标注.csv")
chunks_all = load_csv("NCE2_语块标注.csv")
toks_all = load_csv("NCE2_词性标注.csv")

sent_by_lesson = collections.defaultdict(list)
for r in sents:
    sent_by_lesson[int(r["lesson"])].append(r)
chunk_by_lesson = collections.defaultdict(list)
for r in chunks_all:
    chunk_by_lesson[int(r["lesson"])].append(r)
tok_by_sent = collections.defaultdict(list)
for r in toks_all:
    tok_by_sent[(int(r["lesson"]), int(r["sentId"]))].append(r)

def vocab_rows(no):
    p = glob.glob(os.path.join(VOCAB, "单课", "L%02d_*.csv" % no))
    if not p:
        return []
    with open(p[0], encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

# ---------------------------------------------------------------- 句型卡积木着色
def color_rows(no, sid):
    """给一句的 token 打上 S/V/O/C/灰 角色色，返回 [(word, role)]"""
    toks = sorted(tok_by_sent.get((no, sid), []), key=lambda r: int(r["tokId"]))
    root_idx = next((int(t["tokId"]) for t in toks if t["dep"] == "ROOT"), None)
    out = []
    for t in toks:
        dep, pos, hi = t["dep"], t["pos"], int(t["headIdx"])
        role = ""
        if dep == "ROOT" or (pos in ("VERB", "AUX") and dep in ("aux", "auxpass", "cop")):
            role = "V"
        elif dep in ("nsubj", "nsubjpass", "csubj"):
            role = "S"
        elif dep == "npadvmod" and pos in ("NOUN", "PROPN", "PRON") and hi == root_idx:
            role = "S"
        elif dep in ("obj", "dobj", "iobj"):
            role = "O"
        elif dep in ("attr", "acomp", "oprd", "xcomp"):
            role = "C"
        elif dep in ("obl", "advmod", "advcl") or (dep == "npadvmod"):
            role = "A"   # 状语·灰
        out.append((t["word"], role))
    return out

def colored_html(no, sid):
    spans = []
    for w, role in color_rows(no, sid):
        cls = {"S": "bS", "V": "bV", "O": "bO", "C": "bC", "A": "bA"}.get(role, "")
        spans.append('<span class="%s">%s</span>' % (cls, html.escape(w)))
    return " ".join(spans)

# ---------------------------------------------------------------- 各课卡片挑选
def pick_cards(no):
    ss = sorted(sent_by_lesson.get(no, []), key=lambda r: int(r["sentId"]))
    body = [r for r in ss if r["pattern"] != "Fragment"] or ss
    pat_cards = body[:3]
    # 语块：每类取最长 2 条，拼 6 条
    by_type = collections.defaultdict(list)
    for c in chunk_by_lesson.get(no, []):
        if int(c["length"]) >= 2:
            by_type[c["chunkType"]].append(c)
    picked = []
    for t, take in (("VP", 2), ("PP", 2), ("SBAR", 1), ("NP", 1)):
        for c in sorted(by_type.get(t, []), key=lambda r: -int(r["length"]))[:take]:
            picked.append(c)
    # 词汇卡：实词按频次
    CONTENT = {"n", "v", "adj", "adv"}
    vr = [r for r in vocab_rows(no) if r.get("词性", "") in CONTENT]
    vr.sort(key=lambda r: -int(r["频次"] or 0))
    words = vr[:8]
    # 听写：≤10 词
    dict_items = [r for r in ss if int(r["wordCount"]) <= SHORT_WORDS][:MAX_DICT_PER_LESSON]
    return pat_cards, picked, words, dict_items, ss

# ---------------------------------------------------------------- 任务单模板
TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>L__NO__ __TITLE__ · 任务单</title>
<style>
  :root{--S:#E03131;--V:#2F9E44;--O:#1971C2;--C:#9C36B5;--A:#868E96;
        --ink:#212529;--sub:#868E96;--line:#E9ECEF;--card:#fff;--bg:#F8F9FA;--acc:#4C6EF5}
  *{box-sizing:border-box}
  body{margin:0;font-family:"Noto Sans SC",-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
       background:var(--bg);color:var(--ink);font-size:16px;line-height:1.65}
  .wrap{max-width:760px;margin:0 auto;padding:14px 14px 80px}
  header{background:linear-gradient(135deg,#4C6EF5,#12B886);color:#fff;border-radius:16px;padding:16px 18px}
  header h1{margin:0;font-size:20px} header .zh{opacity:.92;font-size:14px}
  header .back{float:right;color:#fff;text-decoration:none;font-size:13px;opacity:.9}
  .btn{display:inline-block;background:var(--acc);color:#fff;border:0;border-radius:999px;
       padding:10px 22px;font-size:16px;font-family:inherit;cursor:pointer}
  .btn.print{background:#495057}
  section{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px 16px;margin-top:14px}
  h2{font-size:16px;margin:0 0 8px}
  h2 .no{display:inline-block;width:26px;height:26px;border-radius:50%;background:var(--acc);color:#fff;
         text-align:center;line-height:26px;font-size:14px;margin-right:6px}
  .tip{color:var(--sub);font-size:13px;margin:2px 0 10px}
  .player{width:100%;margin:6px 0}
  .sent{display:flex;align-items:flex-start;gap:8px;padding:8px 0;border-bottom:1px dashed var(--line)}
  .sent:last-child{border-bottom:0}
  .play{flex:0 0 40px;width:40px;height:40px;border-radius:50%;border:0;background:var(--acc);color:#fff;
        font-size:16px;cursor:pointer}
  .sent .en{font-family:Georgia,"Times New Roman",serif}
  .sent .zh{color:var(--sub);font-size:14px;display:none}
  .sent.open .zh{display:block}
  .ck{margin-left:auto;flex:0 0 auto;transform:scale(1.4);accent-color:var(--acc)}
  .dict .box{border-bottom:2px solid var(--ink);min-height:26px;margin:10px 0;letter-spacing:2px}
  .rev{background:#F1F3F5;border:1px solid var(--line);border-radius:8px;color:var(--sub);
       font-size:13px;padding:4px 12px;cursor:pointer;font-family:inherit}
  .cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}
  .wcard{border:1px solid var(--line);border-radius:12px;padding:8px 10px}
  .wcard b{font-size:17px;font-family:Georgia,serif}
  .chip{display:inline-block;border-radius:6px;padding:0 6px;font-size:11px;background:#EDF2FF;color:#364FC7;margin-left:4px}
  .chip.cefr{background:#E6FCF5;color:#0CA678}
  .chip.out{background:#FFF0F6;color:#C2255C}
  .ccard{border:1px solid var(--line);border-radius:12px;padding:8px 10px}
  .ccard .tag{color:var(--sub);font-size:12px}
  .pcard{border:1px solid var(--line);border-radius:12px;padding:10px 12px;margin-bottom:8px}
  .pcard .pat{float:right;font-size:12px;color:var(--sub)}
  .bS{color:var(--S);font-weight:700}.bV{color:var(--V);font-weight:700}
  .bO{color:var(--O);font-weight:700}.bC{color:var(--C);font-weight:700}.bA{color:var(--A)}
  .legend{font-size:12px;color:var(--sub);margin-top:6px}
  .legend i{font-style:normal;font-weight:700;margin-right:8px}
  details.full{margin-top:10px} details.full summary{cursor:pointer;color:var(--acc)}
  .fulltext .sent{border:0;padding:4px 0}
  .fulltext .idx{color:var(--sub);font-size:12px;flex:0 0 30px}
  footer{color:var(--sub);font-size:12px;text-align:center;margin-top:18px}
  @media print{
    body{background:#fff;font-size:12.5pt}
    .wrap{max-width:none;padding:0}
    header{border-radius:0;background:#fff;color:#000;border-bottom:2px solid #000}
    header .back,.play,.btn,.no-print{display:none!important}
    section{border:1px solid #999;border-radius:0;page-break-inside:avoid}
    .sent .zh{display:none!important}
    .box{border-bottom:1.5pt solid #000}
    .rev{display:none}
    .sent{page-break-inside:avoid}
  }
</style>
</head>
<body>
<div class="wrap">
<header>
  <a class="back" href="index.html">← 目录</a>
  <h1>L__NO__ · __TITLE__</h1>
  <div class="zh">__TITLEZH__ · 约 __DUR__ 分钟 · __NPAT__</div>
</header>

<section>
  <button class="btn" onclick="playAll()">▶ 通听全文</button>
  <button class="btn print no-print" onclick="window.print()">🖨 打印纸质版</button>
  <audio id="au" class="player" controls preload="none"></audio>
</section>

<section>
  <h2><span class="no">1</span>聆听 · 盲听 + 答题卡</h2>
  <div class="tip">先只看图和下面的问题，再盲听 2 遍，口头回答后勾选完成。</div>
  <div class="pcard"><b>Q：</b><span class="en">__QUESTION__</span>
    <div class="zh">__QUESTIONZH__</div></div>
  <label><input type="checkbox" class="ck" data-k="listen"> 聆听完成（听懂大意）</label>
</section>

<section>
  <h2><span class="no">2</span>跟读 · 逐句影子</h2>
  <div class="tip">每句：点 ▶ 听一遍 → 立刻影子跟读 → 再听对比。跟读前先把全文"看图听大意"过一遍。点句子可看中文。</div>
  <div id="shadowList"></div>
  <label><input type="checkbox" class="ck" data-k="shadow"> 跟读完成（逐句影子）</label>
</section>

<section class="dict">
  <h2><span class="no">3</span>听写 · 只写听到的</h2>
  <div class="tip">每格一个词。点 ▶ 听句子，写下来；写完点「对答案」。__DICT_TIP__</div>
  <div id="dictList"></div>
  <label><input type="checkbox" class="ck" data-k="dict"> 听写完成</label>
</section>

<section>
  <h2><span class="no">4</span>三线卡 · 词汇 / 语块 / 句型</h2>
  <div class="tip">先混个脸熟，不用背。点句型卡里的句子可在预览页看解析。</div>
  <b>词汇卡</b>
  <div class="cards">__WORDCARDS__</div>
  <p style="margin:10px 0 4px"><b>语块卡</b></p>
  <div class="cards">__CHUNKCARDS__</div>
  <p style="margin:10px 0 4px"><b>句型卡</b> <span class="pat">积木色：句子成分一眼看穿</span></p>
  __PATTERNCARDS__
  <div class="legend"><i style="color:var(--S)">红=主语S</i><i style="color:var(--V)">绿=动词V</i><i style="color:var(--O)">蓝=宾语O</i><i style="color:var(--C)">紫=补语C</i><i style="color:var(--A)">灰=状语</i></div>
</section>

<section>
  <details class="full"><summary>课文全文（含中文，打印版自动带出）</summary>
    <div class="fulltext" id="fullText"></div>
  </details>
</section>

<footer>NCE2 任务单 · A 框架（聆听/跟读/听写 + D+7 复述）· __GEN__</footer>
</div>

<script>
const D = __DATA__;
const KEY = "L__NO__:";
const au = document.getElementById("au");
au.src = AUDIO_BASE + encodeURI(D.audio);

function seg(i){ const s=D.sent[i]; au.currentTime=s.t; au.play();
  const stop=()=>{ if(au.currentTime>=s.t2){ au.pause(); au.removeEventListener("timeupdate",stop);} };
  au.addEventListener("timeupdate", stop); }
function playAll(){ au.currentTime=D.sent[0].t; au.play(); }

const sl=document.getElementById("shadowList");
D.sent.forEach((s,i)=>{
  const d=document.createElement("div"); d.className="sent";
  d.innerHTML='<button class="play" onclick="seg('+i+')">▶</button>'+
    '<div><div class="en">'+s.x+'</div><div class="zh">'+s.z+'</div></div>'+
    '<input type="checkbox" class="ck" data-k="s'+i+'">';
  d.onclick=e=>{ if(e.target.tagName!=="BUTTON"&&e.target.type!=="checkbox") d.classList.toggle("open"); };
  sl.appendChild(d);
});

const dl=document.getElementById("dictList");
D.dict.forEach((it,i)=>{
  const d=document.createElement("div"); d.className="sent";
  let boxes=""; for(let k=0;k<it.n;k++) boxes+='<div class="box"></div>';
  d.innerHTML='<button class="play" onclick="seg('+it.si+')">▶</button>'+
    '<div style="flex:1">'+boxes+
    '<div class="zh"><span class="en">'+it.x+'</span><br>'+it.z+'</div></div>'+
    '<button class="rev" onclick="this.parentElement.classList.add(\'open\')">对答案</button>';
  dl.appendChild(d);
});

const ft=document.getElementById("fullText");
D.sent.forEach((s,i)=>{ ft.insertAdjacentHTML("beforeend",
  '<div class="sent"><span class="idx">'+(i+1)+'</span><div><div class="en">'+s.x+'</div><div class="zh">'+s.z+'</div></div></div>'); });

document.querySelectorAll(".ck").forEach(c=>{
  c.checked = localStorage.getItem(KEY+c.dataset.k)==="1";
  c.onchange = ()=> localStorage.setItem(KEY+c.dataset.k, c.checked?"1":"0");
});
</script>
</body>
</html>
"""

AUDIO_BASE_JS = 'const AUDIO_BASE="%s";' % AUDIO_DIR

INDEX_TPL = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NCE2 任务单目录</title>
<style>
 body{margin:0;font-family:"Noto Sans SC",-apple-system,"PingFang SC",sans-serif;background:#F8F9FA;color:#212529}
 .wrap{max-width:900px;margin:0 auto;padding:18px 14px 60px}
 h1{font-size:20px} .sub{color:#868E96;font-size:13px;margin-bottom:14px}
 .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px}
 a.card{display:block;background:#fff;border:1px solid #E9ECEF;border-radius:14px;padding:10px 12px;
        text-decoration:none;color:#212529}
 a.card:hover{border-color:#4C6EF5}
 a.card b{font-size:15px} a.card .t{color:#868E96;font-size:12px;display:block}
 .dot{float:right;font-size:12px;color:#ADB5BD}
 a.card.done{border-color:#12B886;background:#F0FFF9}
 a.card.done .dot{color:#12B886}
</style></head><body><div class="wrap">
<h1>新概念英语（二）· 每课任务单</h1>
<div class="sub">A 框架：聆听 → 跟读 → 听写 → 三线卡 · 完成一门三门全勾即亮绿（进度存本机浏览器）· 已完成 <span id="n">0</span>/96</div>
<div class="grid">__CARDS__</div>
</div>
<script>
const LS=window.localStorage, items=[].slice.call(document.querySelectorAll("a.card"));
function refresh(){ let n=0; items.forEach(a=>{
  const no=a.dataset.no, k="L"+no+":";
  const done=["listen","shadow","dict"].every(x=>LS.getItem(k+x)==="1");
  a.classList.toggle("done",done); a.querySelector(".dot").textContent=done?"✓":"○";
  if(done)n++; }); document.getElementById("n").textContent=n; }
refresh();
</script></body></html>
"""

# ---------------------------------------------------------------- 主流程
def main():
    os.makedirs(OUT, exist_ok=True)

    # ① 听写选句清单 CSV（正典）
    dict_rows = []
    for r in sents:
        if int(r["wordCount"]) <= SHORT_WORDS:
            dict_rows.append({
                "课号": r["lesson"], "课标题": r.get("titleZh", "") or "", "句ID": r["sentId"],
                "句子": r["text"], "译文": r["textZh"], "词数": r["wordCount"],
                "句型": r["pattern"], "句型中文": r["patternZh"], "时态": r["tense"],
            })
    dict_rows.sort(key=lambda x: (int(x["课号"]), int(x["句ID"])))
    p = os.path.join(ANNO, "NCE2_听写选句清单.csv")
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(dict_rows[0].keys()))
        w.writeheader(); w.writerows(dict_rows)
    print("听写选句清单 %d 行 -> %s" % (len(dict_rows), p))

    # ② 逐课任务单
    n_files = 0
    index_cards = []
    for no in sorted(lessons_meta):
        lm = lessons_meta[no]
        zl = zh.get(no, {})
        body_start = 3 if lm.get("instruction") else 1
        lines = lm["lines"]
        dur_est = lm.get("durationSecEst") or 0
        # 句子（含音频时间轴）：sentId si ↔ lines[body_start+si]
        ss = sorted(sent_by_lesson.get(no, []), key=lambda r: int(r["sentId"]))
        sent_js = []
        for si, r in enumerate(ss):
            li = body_start + si
            t = lines[li]["t"] if li < len(lines) else 0.0
            t2 = lines[li + 1]["t"] if li + 1 < len(lines) else t + 10.0
            sent_js.append({"t": round(t, 2), "t2": round(t2, 2),
                            "x": html.escape(r["text"]), "z": html.escape(r.get("textZh", ""))})
        pat_cards, picked_chunks, words, dict_items, _ss = pick_cards(no)

        wordcards = []
        for w in words:
            layer = w.get("归属层", ""); cefr = w.get("CEFR", "")
            chip = '<span class="chip out">超纲</span>' if "超纲" in layer or not layer else \
                   '<span class="chip">%s</span><span class="chip cefr">%s</span>' % (html.escape(layer), html.escape(cefr))
            wordcards.append('<div class="wcard"><b>%s</b>%s<div class="tag">%s</div></div>'
                             % (html.escape(w["显示词"]), chip,
                                html.escape((w.get("原文例句") or "")[:60])))
        chunkcards = []
        for c in picked_chunks:
            chunkcards.append('<div class="ccard"><b class="en">%s</b><div class="tag">%s · %s</div></div>'
                              % (html.escape(c["text"]), html.escape(c["chunkTypeZh"]),
                                 html.escape(c.get("teachTag", ""))))
        pcards = []
        for r in pat_cards:
            pcards.append('<div class="pcard"><span class="pat">%s</span><div>%s</div>'
                          '<div class="zh" style="font-size:13px;color:var(--sub)">%s</div></div>'
                          % (html.escape(r["patternZh"]), colored_html(no, int(r["sentId"])),
                             html.escape(r.get("textZh", ""))))

        dict_tip = ""
        dict_js = [{"si": int(r["sentId"]), "n": int(r["wordCount"]),
                    "x": html.escape(r["text"]), "z": html.escape(r.get("textZh", ""))}
                   for r in dict_items]
        if not dict_js:
            dict_tip = "本课无 ≤10 词短句，改为关键词听写（词汇卡里的词听写 3 个）。"
            dict_js = [{"si": 0, "n": 1, "x": "", "z": ""}]

        data = {
            "no": no, "audio": lm["audio"], "dur": dur_est,
            "sent": sent_js, "dict": dict_js,
        }
        h = (TPL
             .replace("__NO__", "%02d" % no)
             .replace("__TITLE__", html.escape(lm["title"]))
             .replace("__TITLEZH__", html.escape(zl.get("titleZh", "")))
             .replace("__DUR__", str(int(dur_est // 60)))
             .replace("__NPAT__", "首现语法点见句型卡")
             .replace("__QUESTION__", html.escape(lm.get("question", "") or (lines[0]["text"] if lines else "")))
             .replace("__QUESTIONZH__", html.escape(zl.get("questionZh", "")))
             .replace("__DICT_TIP__", dict_tip)
             .replace("__WORDCARDS__", "".join(wordcards))
             .replace("__CHUNKCARDS__", "".join(chunkcards))
             .replace("__PATTERNCARDS__", "".join(pcards))
             .replace("__DATA__", json.dumps(data, ensure_ascii=False))
             .replace("__GEN__", datetime.datetime.now().strftime("%Y-%m-%d")))
        # 注入音频基址
        h = h.replace("<script>\nconst D =", "<script>\n%s\nconst D =" % AUDIO_BASE_JS)
        fp = os.path.join(OUT, "L%02d.html" % no)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(h)
        n_files += 1
        index_cards.append('<a class="card" data-no="%d" href="L%02d.html"><span class="dot">○</span>'
                           '<b>L%02d · %s</b><span class="t">%s</span></a>'
                           % (no, no, no, html.escape(lm["title"]), html.escape(zl.get("titleZh", ""))))

    # ③ 目录页
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(INDEX_TPL.replace("__CARDS__", "".join(index_cards)))
    print("任务单 %d 份 + index.html -> %s" % (n_files, OUT))

if __name__ == "__main__":
    main()
