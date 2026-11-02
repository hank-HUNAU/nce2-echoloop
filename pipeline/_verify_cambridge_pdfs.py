# -*- coding: utf-8 -*-
"""Cambridge 官方词表 PDF 全量核验
- 完整性：SHA256 / 字节 / 页数 / pypdf 可解析 / 文本抽取成功
- 内容量：抽取文本长度、唯一小写词形数
- 交叉核验：与本地 wordlists（KET/PET/YLE 三层）比对覆盖率（证明本地 JSON 的官方来源）
- 输出：词汇数据/剑桥词表PDF核验报告.md + 词汇数据/cambridge_pdf_verify.json
"""
import os, re, json, hashlib, collections, datetime

from pypdf import PdfReader

BASE = r"E:\04 少儿原版课程\06 新概念英语"
SRC = os.path.join(BASE, "词库源")
OUT = os.path.join(BASE, "词汇数据")
WL = r"C:\Users\Thinkpad\.workbuddy\skills\article-vocab-analyzer\wordlists"

PAIRS = [
    ("506886-a2-key-2020-vocabulary-list.pdf", "A2 Key（KET）2020", ["KET"], "https://www.cambridgeenglish.org/Images/506886-a2-key-2020-vocabulary-list.pdf"),
    ("506887-b1-preliminary-vocabulary-list.pdf", "B1 Preliminary（PET）", ["PET"], "https://www.cambridgeenglish.org/Images/506887-b1-preliminary-vocabulary-list.pdf"),
    ("506166-starters-movers-flyers-word-list-2025.pdf", "YLE 2025 合并版（Starters/Movers/Flyers）",
     ["A1_Starters", "A1_Movers", "A2_Flyers"], "https://www.cambridgeenglish.org/Images/506166-starters-movers-flyers-word-list-2025.pdf"),
    ("739104-starters-movers-flyers-word-list-2025.pdf", "YLE 2025 合并版（副本/另一入口）",
     ["A1_Starters", "A1_Movers", "A2_Flyers"], "https://www.cambridgeenglish.org/Images/739104-starters-movers-flyers-word-list-2025.pdf"),
    ("351849-pre-a1-starters-word-list-2018.pdf", "Pre A1 Starters 2018 单册", ["A1_Starters"],
     "https://www.cambridgeenglish.org/Images/351849-pre-a1-starters-word-list-2018.pdf"),
    ("351851-a2-flyers-word-list-2018.pdf", "A2 Flyers 2018 单册", ["A2_Flyers"],
     "https://www.cambridgeenglish.org/Images/351851-a2-flyers-word-list-2018.pdf"),
]

TOKEN_RE = re.compile(r"[a-z][a-z'\-]*")


def load_local(key):
    d = json.load(open(os.path.join(WL, key + ".json"), encoding="utf-8"))
    words = set()
    for e in d.get("entries", []):
        for seg in str(e["head"]).lower().split("/"):
            seg = seg.strip()
            if not seg:
                continue
            for t in TOKEN_RE.findall(seg):
                words.add(t)
    return words, len(d.get("entries", []))


rows = []
for fn, label, locals_, url in PAIRS:
    path = os.path.join(SRC, fn)
    rec = {"file": fn, "label": label, "url": url}
    if not os.path.exists(path):
        rec.update({"status": "缺失"})
        rows.append(rec); continue
    raw = open(path, "rb").read()
    rec["bytes"] = len(raw)
    rec["sha256"] = hashlib.sha256(raw).hexdigest()
    try:
        rd = PdfReader(path)
        rec["pages"] = len(rd.pages)
        txt = "\n".join((p.extract_text() or "") for p in rd.pages)
        rec["ok"] = True
    except Exception as ex:
        rec.update({"pages": 0, "ok": False, "error": str(ex), "textChars": 0,
                    "uniqueTokens": 0, "compare": {}})
        rows.append(rec); continue
    try:
        txt = "\n".join((p.extract_text() or "") for p in rd.pages)
    except Exception as ex:
        rec.update({"ok": False, "error": "文本抽取失败: %s" % ex, "textChars": 0,
                    "uniqueTokens": 0, "compare": {}})
        rows.append(rec); continue
    toks = set(TOKEN_RE.findall(txt.lower()))
    rec["textChars"] = len(txt)
    rec["uniqueTokens"] = len(toks)
    rec["compare"] = {}
    for key in locals_:
        lw, n = load_local(key)
        hit = lw & toks
        rec["compare"][key] = {"localEntries": n, "localTokens": len(lw),
                               "hit": len(hit), "coverage": round(100.0 * len(hit) / len(lw), 1) if lw else 0}
    rec["status"] = "通过" if rec["ok"] and rec["pages"] > 0 else "解析失败"
    rows.append(rec)
    print("%-52s 页=%-4d token=%-6d %s" % (fn, rec["pages"], rec["uniqueTokens"],
          " ".join("%s:%.1f%%" % (k, v["coverage"]) for k, v in rec["compare"].items())))

json.dump({"generatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "files": rows},
          open(os.path.join(OUT, "cambridge_pdf_verify.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# ---- MD 报告 ----
m = ["# Cambridge 官方词表 PDF · 全量核验报告\n",
     "- 核验日期：%s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
     "- 核验项：文件完整性（SHA256/字节/页数/可解析）、内容量（抽取文本与唯一词形）、**与本地 wordlists 的交叉覆盖率**",
     "- 用途：证明本地 `KET.json / PET.json / A1_*.json / A2_Flyers.json` 的官方来源可追溯\n",
     "| 文件 | 级别 | 大小 | 页数 | SHA256(前12) | 唯一词形 | 交叉覆盖率 | 结论 |",
     "|---|---|---|---|---|---|---|---|"]
for r in rows:
    if r.get("status") == "缺失":
        m.append("| %s | %s | — | — | — | — | — | ❌ 未下载 |" % (r["file"], r["label"])); continue
    cmp_txt = "；".join("%s %.1f%%（%d/%d）" % (k, v["coverage"], v["hit"], v["localTokens"])
                        for k, v in r.get("compare", {}).items()) or "—"
    m.append("| %s | %s | %.1f MB | %s | `%s` | %s | %s | %s |" % (
        r["file"], r["label"], r["bytes"] / 1048576, r.get("pages", 0), r["sha256"][:12],
        r.get("uniqueTokens", 0), cmp_txt,
        "✅ 通过" if r.get("status") == "通过" else "❌ " + str(r.get("error", ""))[:60]))
m.append("")
m.append("## 核验说明\n")
m.append("1. **覆盖率口径**：把本地词表词头拆成单词形，与 PDF 抽取文本的词形集合取交集；"
         "PDF 为多栏排版，抽取顺序不保证，故用集合比对而非序列比对。")
m.append("2. **未达 100% 的常见原因**：PDF 中的屈折形式、词组拆分、图片化词条、抽取丢字；"
         "因此覆盖率用于**溯源证明**，不用于判定本地词表缺失。")
m.append("3. **B2 First / C1 Advanced / C2 Proficiency**：官方备考页未发布词汇表 PDF"
         "（仅 A2 Key 与 B1 Preliminary 有官方 vocabulary list，YLE 有 word list）→ "
         "本地 `FCE.json`/`CAE.json` 采用 CEFR-J B2 / Octanove C1 替代源属**有据可依**。")
m.append("")
m.append("## 文件清单与来源 URL\n")
for r in rows:
    m.append("- `%s` ← %s" % (r["file"], r["url"]))
open(os.path.join(OUT, "剑桥词表PDF核验报告.md"), "w", encoding="utf-8").write("\n".join(m))
print("报告已写出：", os.path.join(OUT, "剑桥词表PDF核验报告.md"))
