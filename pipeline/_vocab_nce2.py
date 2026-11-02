# -*- coding: utf-8 -*-
"""NCE2 词汇数据生产线：调用 article-vocab-analyzer 的 assess() 引擎，
对 96 课逐课 + 全书 做九词表判定，产出 CSV / MD / HTML 预览所需的 payload。

输入：data/nce2_lessons.json（英文正典）、data/nce2_zh.json（中文译文层，可选）
输出：词汇数据/{单课/*.csv, 全书_*.csv, *_报告.md, NCE2_词汇数据.html}
"""
import os, sys, json, re, importlib.util, collections, datetime, csv, argparse

_ap = argparse.ArgumentParser(description="NCE2 词汇数据生产线")
_ap.add_argument("--out-dir", default="词汇数据", help="输出目录名（相对项目根；默认 词汇数据）")
_ap.add_argument("--strict-lemma", action="store_true",
                 help="启用技能的 lemma 归一修正（-ed/-ing 双写缺陷 + 不规则补表 + -ied→y）；会改变 lemma 与覆盖率")
_ap.add_argument("--cefr-multi", action="store_true",
                 help="CEFR 走技能的多源层（assess_vocab.cefr_annotate）而非本地 cefr_ext.json")
_ap.add_argument("--cefr-sources", default=None,
                 help="第三方 CEFR 源目录（默认 词库源）")
_a = _ap.parse_args()

BASE = r"E:\04 少儿原版课程\06 新概念英语"
DATA = os.path.join(BASE, "data")
OUT = os.path.join(BASE, _a.out_dir)
SKILL = r"C:\Users\Thinkpad\.workbuddy\skills\article-vocab-analyzer"

spec = importlib.util.spec_from_file_location("av", os.path.join(SKILL, "scripts", "assess_vocab.py"))
av = importlib.util.module_from_spec(spec); spec.loader.exec_module(av)

wls = av.discover_wordlists(SKILL)
KEYS = [k for k, _, _ in wls]
# CEFR 改由扩展层提供（Oxford 主标注 + CEFR-J/Octanove/EFLLex 补缺与并列留痕）
EXT = json.load(open(os.path.join(DATA, "cefr_ext.json"), encoding="utf-8"))["entries"]
SUPP = json.load(open(os.path.join(DATA, "lemma_supplement.json"), encoding="utf-8"))["map"]


def _ed_candidates(w):
    """-ed/-ing 词形的额外候选：补 stem_suffix 对 passed→pas、carried→carri 这类误切"""
    out = []
    if w.endswith("ed"):
        b = w[:-2]
        out += [b, b + "e", b + b[-1], b[:-1] + "y", b[:-1]]
    elif w.endswith("ing"):
        b = w[:-3]
        out += [b, b + "e", b + b[-1], b[:-1] + "y"]
    elif w.endswith("ies") and len(w) > 3:
        out.append(w[:-3] + "y")
    elif w.endswith("s") and not w.endswith("ss") and len(w) > 2:
        out += [w[:-1], w[:-1] + "e"]
    return out


def cefr_lookup(lemma):
    """查扩展层；lemma 直查未命中时按词形候选回退（含不规则补表与 -ed/-ing 修正候选）。
    返回 (level, src, alt, conflict)；alt 仅在冲突时非空"""
    if CEFR_VIA_SKILL:
        return _cefr_lookup_skill(lemma)
    cands = [lemma]
    if lemma in SUPP:
        cands.append(SUPP[lemma])
    cands += av.lemma_candidates(lemma) + _ed_candidates(lemma) + _ed_candidates(SUPP.get(lemma, lemma))
    seen = set()
    for c in cands:
        if not c or c in seen:
            continue
        seen.add(c)
        e = EXT.get(c)
        if e:
            alt = {k: e[k] for k in ("oxford", "cefrj", "octanove", "efllex") if e.get(k)}
            return e["level"], e["src"], (alt if e.get("conflict") else {}), bool(e.get("conflict"))
    return "", "", {}, False


def _cefr_lookup_skill(lemma):
    """走技能多源层 assess_vocab.cefr_annotate()：alt 是 'k=v k=v' 串，这里还原成 dict"""
    lv, src, alt_s, cf = av.cefr_annotate(lemma, OXFORD)
    alt = {}
    for part in (alt_s or "").split():
        if "=" in part:
            k, v = part.split("=", 1)
            alt[k] = v
    return lv, src, alt, bool(cf)


# ---- 开关生效 ----
CEFR_VIA_SKILL = bool(_a.cefr_multi)
OXFORD = None
if _a.strict_lemma:
    av.STRICT_LEMMA = True
    av.SUPPLEMENT = SUPP
    print("strict-lemma：已开启（补表 %d 条；lemma 会变 → 覆盖率/词库主键随之变）" % len(SUPP))
if CEFR_VIA_SKILL:
    OXFORD = av.load_cefr(os.path.join(SKILL, "wordlists", "cefr.json"))
    src_dir = _a.cefr_sources or os.path.join(BASE, "词库源")
    if not av.load_cefr_multi(SKILL, OXFORD, src_dir):
        sys.exit("技能多源层未装载成功（源目录：%s）" % src_dir)
    print("CEFR 通道：技能多源层（cefr_annotate）")
print("词表层序:", " < ".join(KEYS))

lessons = json.load(open(os.path.join(DATA, "nce2_lessons.json"), encoding="utf-8"))["lessons"]
zh_map = {}
zp = os.path.join(DATA, "nce2_zh.json")
if os.path.exists(zp):
    for l in json.load(open(zp, encoding="utf-8"))["lessons"]:
        zh_map[l["no"]] = {x["i"]: x["zh"] for x in l["lines"]}
    print("中文译文层：%d 课可用" % len(zh_map))


def body_of(l):
    return l["lines"][3:] if l.get("instruction") else l["lines"][1:]


def analyse(sents):
    """返回 (items_with_meta, total, numbers, proper, hit_counts, layer_counts)"""
    per_key, hit_tok, out_items, numbers_n, proper_n, total = av.assess(sents, wls)
    # 把 token 与句序号对齐（out_items 严格按 句→token 顺序）
    idx = 0
    for si, s in enumerate(sents):
        for _t in av.tokenize(s):
            out_items[idx]["si"] = si
            idx += 1
    for it in out_items:
        if it["kind"] == "word":
            it["layer"] = KEYS[min(it["hit"])]
            lv, src, alt, cf = cefr_lookup(it["lemma"])
            it["cefr"], it["cefrSrc"], it["cefrAlt"], it["cefrConflict"] = lv, src, alt, cf
            rec = per_key[min(it["hit"])].get(("word", it["lemma"]))
            it["pos"] = rec["pos"] if rec else ""
        elif it["kind"] == "out":
            it["layer"] = "out"
            lv, src, alt, cf = cefr_lookup(it["lemma"])
            it["cefr"], it["cefrSrc"], it["cefrAlt"], it["cefrConflict"] = lv, src, alt, cf
            it["pos"] = ""
        else:
            it["layer"] = it["kind"]      # num / proper
            it["cefr"] = ""
            it["pos"] = ""
    return out_items, total, numbers_n, proper_n, hit_tok, per_key


def agg_lesson(items, sents, zh):
    """按 lemma 聚合单课词条"""
    ent = {}
    for it in items:
        if it["kind"] in ("num",):
            continue
        k = it["lemma"]
        e = ent.setdefault(k, {"lemma": k, "display": av.display_word(it["form"], it["lemma"]),
                               "pos": it.get("pos", ""), "layer": it["layer"], "cefr": it["cefr"],
                               "cefrSrc": it.get("cefrSrc", ""), "cefrAlt": it.get("cefrAlt", {}),
                               "cefrConflict": it.get("cefrConflict", False),
                               "freq": 0, "nsent": set(), "kind": it["kind"], "example": "", "zh": ""})
        e["freq"] += 1
        e["nsent"].add(it["si"])
        if not e["example"]:
            e["example"] = sents[it["si"]]
            e["zh"] = zh.get(it["si"], "")
    for e in ent.values():
        e["range"] = len(e["nsent"]); e.pop("nsent")
    return sorted(ent.values(), key=lambda e: (-e["freq"], e["lemma"]))


os.makedirs(os.path.join(OUT, "单课"), exist_ok=True)
per_lesson, book_ent, book_prop, book_out_ex = {}, {}, collections.Counter(), {}
book_freq, book_doc, book_meta = collections.Counter(), collections.Counter(), {}
totals = collections.Counter()
summary = []

for l in lessons:
    no = l["no"]
    body = body_of(l)
    sents = [x["text"] for x in body]
    items, total, numbers_n, proper_n, hit_tok, per_key = analyse(sents)
    zh = zh_map.get(no, {})
    ents = agg_lesson(items, sents, zh)

    layer_cnt = collections.Counter(e_kind_layer := [it["layer"] for it in items])
    proper_forms = collections.Counter(it["form"] for it in items if it["kind"] == "proper")
    merged = sum(v for k, v in layer_cnt.items() if k != "out")
    cov = 100.0 * merged / total if total else 0
    uniq = len([e for e in ents if e["kind"] != "proper"])

    per_lesson[no] = {
        "no": no, "title": l["title"], "titleZh": (zh_map.get(no) and ""), "total": total,
        "uniq": uniq, "layer": dict(layer_cnt), "proper": proper_n, "num": numbers_n,
        "out": layer_cnt.get("out", 0), "coverage": round(cov, 1),
        "ents": ents, "properForms": proper_forms.most_common(),
        "hit": {k: len(h) for k, h in zip(KEYS, hit_tok)},
    }
    summary.append((no, l["title"], total, uniq, layer_cnt.get("out", 0), round(cov, 1)))

    # 全书聚合
    for it in items:
        if it["kind"] == "num":
            totals["num"] += 1; continue
        if it["kind"] == "proper":
            book_prop[it["form"]] += 1
            totals["proper"] += 1
            continue
        lm = it["lemma"]
        book_freq[lm] += 1
        totals[it["layer"]] += 1
        m = book_meta.setdefault(lm, {"lemma": lm, "display": av.display_word(it["form"], lm),
                                      "pos": it.get("pos", ""), "layer": it["layer"],
                                      "cefr": it["cefr"], "cefrSrc": it.get("cefrSrc", ""),
                                      "cefrAlt": it.get("cefrAlt", {}),
                                      "cefrConflict": it.get("cefrConflict", False),
                                      "example": "", "zh": "", "at": ""})
        if not m["example"]:
            m["example"] = sents[it["si"]]
            m["at"] = "L%02d" % no
            m["zh"] = zh.get(it["si"], "")
        book_doc[lm] = book_doc.get(lm, 0)
    for lm in {it["lemma"] for it in items if it["kind"] in ("word", "out")}:
        book_doc[lm] += 0  # ensure key
    seen = {it["lemma"] for it in items if it["kind"] in ("word", "out")}
    for lm in seen:
        book_doc[lm] += 1

book_rows = []
for lm, f in book_freq.most_common():
    m = book_meta[lm]
    book_rows.append({**m, "freq": f, "ndoc": book_doc.get(lm, 0)})

# ---- CSV: 单课 ----
for no, d in per_lesson.items():
    p = os.path.join(OUT, "单课", "L%02d_%s.csv" % (no, re.sub(r'[\\/:*?"<>|]', "", d["title"])[:40]))
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["显示词", "原形lemma", "词性", "归属层", "CEFR", "CEFR来源", "CEFR冲突", "频次", "跨句Range", "例句译文", "原文例句"])
        for e in d["ents"]:
            w.writerow([e["display"], e["lemma"], e["pos"], e["layer"], e["cefr"], e["cefrSrc"],
                        ("/".join("%s=%s" % (k, v) for k, v in sorted(e["cefrAlt"].items())) if e["cefrConflict"] else ""),
                        e["freq"], e["range"], e["zh"], e["example"]])

# ---- CSV: 单课概览 ----
with open(os.path.join(OUT, "NCE2_单课概览.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["课号", "标题", "token数", "词条数", "超纲token", "合并覆盖率%", "命中最高层"] + KEYS)
    for no, title, total, uniq, outn, cov in summary:
        d = per_lesson[no]
        hi = next((k for k in KEYS if d["layer"].get(k)), "-")
        w.writerow([no, title, total, uniq, outn, cov, hi] + [d["layer"].get(k, 0) for k in KEYS])

# ---- CSV: 全书 ----
with open(os.path.join(OUT, "NCE2_全书_词表.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["显示词", "原形lemma", "词性", "归属层", "CEFR", "CEFR来源", "CEFR冲突", "全书频次", "跨课数", "首现", "例句译文", "原文例句"])
    for r in book_rows:
        w.writerow([r["display"], r["lemma"], r["pos"], r["layer"], r["cefr"], r["cefrSrc"],
                    ("/".join("%s=%s" % (k, v) for k, v in sorted(r["cefrAlt"].items())) if r["cefrConflict"] else ""),
                    r["freq"], r["ndoc"], r["at"], r["zh"], r["example"]])

with open(os.path.join(OUT, "NCE2_全书_超纲词.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["词", "频次", "跨课数", "CEFR", "CEFR来源", "例句译文", "原文例句", "首现"])
    for r in book_rows:
        if r["layer"] == "out":
            w.writerow([r["display"], r["freq"], r["ndoc"], r["cefr"], r["cefrSrc"], r["zh"], r["example"], r["at"]])

# ---- CSV: CEFR 冲突清单（多源不一致，全部留痕，不静默覆盖）----
with open(os.path.join(OUT, "NCE2_CEFR冲突清单.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["词", "主标注(采用)", "主标注来源", "Oxford", "CEFR-J", "Octanove", "EFLLex", "全书频次", "跨课数", "归属层", "原文例句"])
    n = 0
    for r in book_rows:
        if not r["cefrConflict"]:
            continue
        a = r["cefrAlt"]
        w.writerow([r["display"], r["cefr"], r["cefrSrc"], a.get("oxford", ""), a.get("cefrj", ""),
                    a.get("octanove", ""), a.get("efllex", ""), r["freq"], r["ndoc"], r["layer"], r["example"]])
        n += 1
    print("CEFR 冲突词条(NCE2 范围内):", n)

# ---- CSV: EFLLex 回填明细（原 354 条未标注中由 EFLLex 补上的部分）----
with open(os.path.join(OUT, "NCE2_EFLLex回填明细.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["词", "EFLLex等级", "归属层", "全书频次", "跨课数", "原文例句", "说明"])
    n_fill = 0
    for r in book_rows:
        if r["cefrSrc"] == "efllex":
            w.writerow([r["display"], r["cefr"], r["layer"], r["freq"], r["ndoc"], r["example"],
                        "Oxford/CEFR-J/Octanove 均无标注，由 EFLLex 等级频率峰值回填"])
            n_fill += 1
    print("EFLLex 回填词条:", n_fill)

with open(os.path.join(OUT, "NCE2_全书_专名词.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["专名", "频次"])
    for wd, n in book_prop.most_common():
        w.writerow([wd, n])

payload = {
    "generatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    "keys": KEYS,
    "book": {"total": sum(totals.values()), "layer": dict(totals), "rows": book_rows,
             "prop": book_prop.most_common(),
             "uniq": len(book_rows), "outUniq": len([r for r in book_rows if r["layer"] == "out"])},
    "lessons": [{"no": d["no"], "title": d["title"], "total": d["total"], "uniq": d["uniq"],
                 "out": d["out"], "coverage": d["coverage"], "layer": d["layer"],
                 "proper": d["proper"], "num": d["num"], "hit": d["hit"],
                 "ents": [{k: e[k] for k in ("display", "lemma", "pos", "layer", "cefr", "cefrSrc",
                                             "cefrAlt", "cefrConflict", "freq", "range", "zh", "example")}
                          for e in d["ents"]],
                 "properForms": d["properForms"]} for d in per_lesson.values()],
}
json.dump(payload, open(os.path.join(OUT, "_payload.json"), "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))
print("payload: %d 课 / 全书 %d 词条（超纲 %d）/ %.1f KB"
      % (len(payload["lessons"]), payload["book"]["uniq"], payload["book"]["outUniq"],
         os.path.getsize(os.path.join(OUT, "_payload.json")) / 1024))
print("全书 token 分布:", dict(totals))
