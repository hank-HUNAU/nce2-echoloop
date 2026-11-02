# -*- coding: utf-8 -*-
"""构建 CEFR 扩展层（多源合并 + 冲突双标注，不静默覆盖）

源与优先级（主标注 level 的取值顺序）：
  1. oxford   = 技能包内置 cefr.json（Oxford 3000/5000，A1–C1，无 C2）  ← 主标注不动
  2. cefrj    = CEFR-J Wordlist v1.6（A1–B2，TUFS，引用即免费）
  3. octanove = Octanove Vocabulary Profile C1/C2 v1.0（CC BY-SA 4.0）  ← 补 C1/C2 通道
  4. efllex   = EFLLex（UCLouvain，15,280 lemma，A1–C1，等级频率分布 → 取峰值等级）

冲突：同一词被两个及以上来源标到不同等级 → conflict=true，各来源等级全部保留在
      oxford/cefrj/octanove/efllex 字段，主标注仍取 Oxford（存在时）不覆盖。
输出：data/cefr_ext.json
"""
import os, json, csv, re, collections, datetime, sys

BASE = r"E:\04 少儿原版课程\06 新概念英语"
SRC = os.path.join(BASE, "词库源")
DATA = os.path.join(BASE, "data")
SKILL_WL = r"C:\Users\Thinkpad\.workbuddy\skills\article-vocab-analyzer\wordlists"

oxford = json.load(open(os.path.join(SKILL_WL, "cefr.json"), encoding="utf-8"))["words"]

# ---- CEFR-J v1.6（ALL_sep：斜杠词头已拆分，便于查表）----
import openpyxl
wb = openpyxl.load_workbook(os.path.join(SRC, "cefrj16", "CEFR-J Wordlist Ver1.6.xlsx"),
                            read_only=True, data_only=True)
cefrj = {}
for sn in ("ALL_sep",):
    rows = wb[sn].iter_rows(values_only=True)
    next(rows)
    for r in rows:
        if not r or not r[0]:
            continue
        h = str(r[0]).strip().lower()
        lv = (str(r[2]).strip().upper() if r[2] else "")
        if h and lv in ("A1", "A2", "B1", "B2"):
            cefrj.setdefault(h, {"level": lv, "pos": (str(r[1]).strip() if r[1] else "")})

# ---- Octanove C1/C2 ----
octan = {}
with open(os.path.join(SRC, "octanove-vocabulary-profile-c1c2-1.0.csv"), encoding="utf-8") as f:
    for row in csv.DictReader(f):
        h = (row.get("headword") or "").strip().lower()
        lv = (row.get("CEFR") or "").strip().upper()
        if h and lv in ("C1", "C2"):
            octan.setdefault(h, {"level": lv, "pos": (row.get("pos") or "").strip()})

# ---- EFLLex（峰值等级）----
efllex = {}
p = os.path.join(SRC, "EFLLex.tsv")
if os.path.exists(p):
    with open(p, encoding="utf-8", errors="replace") as f:
        header = f.readline().rstrip("\n").split("\t")
        cols = {}
        for i, c in enumerate(header):
            m = re.match(r"level_freq@(a1|a2|b1|b2|c1)$", c)
            if m:
                cols[m.group(1)] = i
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 8:
                continue
            w = parts[0].strip().lower()
            if not w:
                continue
            vec = {}
            for lv, i in cols.items():
                try:
                    vec[lv] = float(parts[i])
                except (ValueError, IndexError):
                    vec[lv] = 0.0
            if not any(vec.values()):
                continue
            peak = max(vec, key=lambda k: vec[k])
            efllex.setdefault(w, {"level": peak.upper(), "pos": parts[1] if len(parts) > 1 else "",
                                  "vec": {k: round(v, 2) for k, v in vec.items()}})
else:
    print("!! EFLLex.tsv 缺失，跳过该源", file=sys.stderr)

# ---- 合并 ----
ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]
entries = {}
words = set(oxford) | set(cefrj) | set(octan) | set(efllex)
conflicts = 0
for w in sorted(words):
    o = oxford.get(w, "")
    c = cefrj.get(w, {}).get("level", "")
    t = octan.get(w, {}).get("level", "")
    e = efllex.get(w, {}).get("level", "")
    # 冲突只在「分级词表」之间判定（Oxford / CEFR-J / Octanove 同为等级赋值构念）；
    # EFLLex 是等级频率分布资源（不同构念），仅作补缺回填，不参与冲突判定
    graded = {k: v for k, v in (("oxford", o), ("cefrj", c), ("octanove", t)) if v}
    conflict = len(set(graded.values())) > 1
    present = dict(graded)
    if e:
        present["efllex"] = e
    if conflict:
        conflicts += 1
    # 主标注：Oxford 优先（不静默覆盖），其后 cefrj → octanove → efllex
    if o:
        level, src = o, "oxford"
    elif c:
        level, src = c, "cefrj"
    elif t:
        level, src = t, "octanove"
    elif e:
        level, src = e, "efllex"
    else:
        continue
    pos = (cefrj.get(w, {}).get("pos") or octan.get(w, {}).get("pos")
           or efllex.get(w, {}).get("pos") or "")
    entries[w] = {"level": level, "src": src, "pos": pos,
                  "oxford": o, "cefrj": c, "octanove": t, "efllex": e,
                  "conflict": conflict}

out = {
    "generatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    "policy": "主标注保留 Oxford 不动；CEFR-J/Octanove/EFLLex 仅补缺与并列记录；冲突不覆盖，全部留痕",
    "sources": {
        "oxford": {"file": SKILL_WL + r"\cefr.json", "entries": len(oxford),
                   "levels": dict(collections.Counter(oxford.values())),
                   "note": "Oxford 3000/5000 星标，A1–C1，无 C2"},
        "cefrj": {"file": SRC + r"\cefrj16\CEFR-J Wordlist Ver1.6.xlsx (ALL_sep)", "entries": len(cefrj),
                  "levels": dict(collections.Counter(v["level"] for v in cefrj.values())),
                  "note": "CEFR-J Wordlist v1.6，TUFS 投野研，引用即免费可商用"},
        "octanove": {"file": SRC + r"\octanove-vocabulary-profile-c1c2-1.0.csv", "entries": len(octan),
                     "levels": dict(collections.Counter(v["level"] for v in octan.values())),
                     "note": "Octanove Vocabulary Profile C1/C2 v1.0，CC BY-SA 4.0"},
        "efllex": {"file": p, "entries": len(efllex),
                   "levels": dict(collections.Counter(v["level"] for v in efllex.values())),
                   "note": "EFLLex，UCLouvain CENTAL，取等级频率峰值，A1–C1"},
    },
    "totalEntries": len(entries),
    "conflictEntries": conflicts,
    "entries": entries,
}
path = os.path.join(DATA, "cefr_ext.json")
json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("合并词条:", len(entries), "| 冲突词条:", conflicts)
for k, v in out["sources"].items():
    print("  %-9s %6d  %s" % (k, v["entries"], v["levels"]))
print("输出:", path, "%.1f KB" % (os.path.getsize(path) / 1024))

# 冲突样例
n = 0
for w, e in entries.items():
    if e["conflict"]:
        print("  冲突样例:", w, {k: e[k] for k in ("oxford", "cefrj", "octanove", "efllex") if e[k]})
        n += 1
        if n >= 8:
            break
