# -*- coding: utf-8 -*-
"""NCE2 句法标注生产线（教学用途 · 三层 · spaCy + 规则层）

三层对应三大教学目的：
  L1 词汇层（token）  → 词汇 + 语法属性（词性/形态/句法角色/词汇层/CEFR）
  L2 语块层（chunk）  → 短语/语块（NP/VP/PP/ADJP/ADVP/SBAR + 内部结构式）
  L3 句型层（sentence）→ 句型（SV/SVO/SVP/SVOO/SVOC…）+ 时态语态语气 + 语法点

用法：
  python _grammar_annotate.py                 # 全书 96 课
  python _grammar_annotate.py --limit 3       # 只跑前 N 课（冒烟）
  python _grammar_annotate.py --model en_core_web_sm
"""
import os, sys, json, re, csv, argparse, collections, datetime

BASE = r"E:\04 少儿原版课程\06 新概念英语"
DATA = os.path.join(BASE, "data")
VOCAB = os.path.join(BASE, "词汇数据")
OUT = os.path.join(BASE, "标注数据库")

_ap = argparse.ArgumentParser()
_ap.add_argument("--limit", type=int, default=0, help="只跑前 N 课（冒烟用）")
_ap.add_argument("--model", default="en_core_web_md")
_ap.add_argument("--vocab-csv", default=os.path.join(VOCAB, "NCE2_全书_词表.csv"))
_a = _ap.parse_args()

import spacy

try:
    NLP = spacy.load(_a.model, exclude=["ner"])
except OSError:
    sys.exit("缺少模型 %s：pip install <对应 wheel> 或 python -m spacy download %s" % (_a.model, _a.model))

# ---------------------------------------------------------------- 映射表
POS_ZH = {
    "NOUN": "名词", "VERB": "动词", "ADJ": "形容词", "ADV": "副词", "PRON": "代词",
    "DET": "限定词", "ADP": "介词", "NUM": "数词", "CCONJ": "并列连词", "SCONJ": "从属连词",
    "PART": "助词/小品词", "AUX": "助动词", "INTJ": "感叹词", "PUNCT": "标点",
    "PROPN": "专有名词", "SYM": "符号", "X": "其他", "SPACE": "空白",
}
TAG_ZH = {
    "NN": "单数名词", "NNS": "复数名词", "NNP": "专有名词单数", "NNPS": "专有名词复数",
    "VB": "动词原形", "VBD": "动词过去式", "VBG": "现在分词/动名词", "VBN": "过去分词",
    "VBP": "现在时非三单", "VBZ": "现在时三单", "MD": "情态动词",
    "JJ": "形容词", "JJR": "形容词比较级", "JJS": "形容词最高级",
    "RB": "副词", "RBR": "副词比较级", "RBS": "副词最高级", "WRB": "疑问副词",
    "IN": "介词/从属连词", "DT": "限定词/冠词", "PRP": "人称代词", "PRP$": "物主代词",
    "WDT": "关系限定词", "WP": "关系代词", "WP$": "关系物主代词", "EX": "存在词there",
    "TO": "不定式标记to", "CC": "并列连词", "CD": "基数词", "PDT": "前位限定词",
    "RP": "小品词", "UH": "感叹词", "FW": "外来词", "POS": "所有格标记",
    ".": "句号", ",": "逗号", ":": "冒号", "``": "左引号", "''": "右引号",
    "?": "问号", "!": "感叹号", "-LRB-": "左括号", "-RRB-": "右括号", "$": "货币符号",
}
MORPH_ZH = {
    "Tense=Past": "过去时", "Tense=Pres": "现在时", "Tense=Fut": "将来时",
    "VerbForm=Fin": "限定动词", "VerbForm=Inf": "不定式", "VerbForm=Ger": "动名词",
    "VerbForm=Part": "分词", "VerbForm=None": "—",
    "Number=Sing": "单数", "Number=Plur": "复数",
    "Person=1": "第一人称", "Person=2": "第二人称", "Person=3": "第三人称",
    "Case=Nom": "主格", "Case=Acc": "宾格", "Case=Gen": "所有格",
    "Degree=Pos": "原级", "Degree=Cmp": "比较级", "Degree=Sup": "最高级",
    "Mood=Ind": "陈述语气", "Mood=Sub": "虚拟语气", "Mood=Imp": "祈使语气",
    "Aspect=Perf": "完成体", "Aspect=Prog": "进行体", "Voice=Pass": "被动",
    "Definite=Def": "定指", "Definite=Ind": "不定指", "PronType=Rel": "关系词",
    "PronType=Int": "疑问词", "PronType=Dem": "指示词", "PronType=Prs": "人称",
    "PronType=Art": "冠词", "Poss=Yes": "所有格", "Reflex=Yes": "反身",
}
DEP_ZH = {
    "ROOT": "谓语中心", "nsubj": "主语", "nsubjpass": "被动主语", "csubj": "主语从句",
    "obj": "宾语", "dobj": "直接宾语", "iobj": "间接宾语", "obl": "介词/斜格补语",
    "nmod": "名词修饰语", "pobj": "介词宾语", "attr": "表语", "acomp": "表语",
    "oprd": "宾语补足语", "xcomp": "补足语(非限定)", "ccomp": "从句补语(宾语从句)",
    "aux": "助动词", "auxpass": "被动助动词", "cop": "系动词", "neg": "否定词",
    "det": "限定词", "predet": "前位限定词", "amod": "定语(形容词)", "nummod": "数量修饰",
    "compound": "复合名词修饰", "poss": "所有格修饰", "advmod": "状语",
    "advcl": "状语从句", "relcl": "定语从句", "acl": "定语性从句/修饰",
    "appos": "同位语", "conj": "并列成分", "cc": "并列连词", "case": "介词/格标记",
    "mark": "从句引导词", "punct": "标点", "expl": "形式主语there/it",
    "prt": "短语动词小品词", "parataxis": "插入/并列", "preconj": "前位连词",
    "quantmod": "数量修饰", "npadvmod": "名词性状语", "prep": "介词", "meta": "元信息",
    "intj": "感叹语", "discourse": "话语标记", "vocative": "呼语", "orphan": "孤立成分",
    "clf": "量词", "fixed": "固定搭配", "flat": "扁平结构", "goeswith": "跨词",
}
CHUNK_ZH = {"NP": "名词短语", "VP": "动词短语", "PP": "介词短语", "ADJP": "形容词短语",
            "ADVP": "副词短语", "SBAR": "从句", "PRT": "短语动词", "NUMQP": "数量短语"}
GRAMMAR_ZH = {}   # 由 RULES 填充


def mz(morph_str):
    if not morph_str:
        return ""
    parts = [p for p in str(morph_str).split("|") if p]
    return "｜".join(MORPH_ZH.get(p, p) for p in parts)


# ---------------------------------------------------------------- 词汇层衔接
def load_vocab_map(path):
    """lemma → (layer, cefr, cefrSrc)。取自既有词汇数据库（九词表 + CEFR 多源层）"""
    m = {}
    if not os.path.exists(path):
        return m
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            lm = (r.get("原形lemma") or r.get("lemma") or "").strip().lower()
            if not lm:
                continue
            m[lm] = (r.get("归属层") or r.get("layer") or "",
                     r.get("CEFR") or r.get("cefr") or "",
                     r.get("CEFR来源") or r.get("cefrSrc") or "")
            w = (r.get("显示词") or "").strip().lower()
            if w:
                m.setdefault(w, m[lm])
    return m


# ---------------------------------------------------------------- L2 语块
CLAUSE_DEPS = {"advcl", "relcl", "ccomp", "acl", "conj", "parataxis", "csubj"}


def span_of(tokens):
    idx = [t.i for t in tokens]
    return min(idx), max(idx)


def collect_vp(doc, verb):
    """VP = 动词 + 助动词/否定/小品词 + 宾语/补语/状语（不跨从句）"""
    keep = []
    for t in doc:
        if t.i == verb.i:
            keep.append(t); continue
        if t.head.i == verb.i and t.dep_ in ("aux", "auxpass", "neg", "prt", "obj", "dobj",
                                         "iobj", "oprd", "acomp", "attr", "xcomp",
                                         "advmod", "obl", "npadvmod", "expl"):
            keep.append(t)
    keep = [t for t in keep if t.dep_ != "punct"]
    return sorted(keep, key=lambda t: t.i)


def extract_chunks(doc):
    chunks = []
    seen = set()
    # NP: spaCy noun_chunks
    for nc in doc.noun_chunks:
        toks = list(nc)
        key = ("NP", nc.start, nc.end)
        if key in seen:
            continue
        seen.add(key)
        chunks.append(("NP", toks, nc.root))
    # PP: 介词 + pobj/obl 子树
    for t in doc:
        if t.pos_ == "ADP" and t.dep_ in ("case", "prep", "advmod", "ROOT", "agent"):
            kids = [c for c in t.subtree if c.dep_ not in ("punct",)]
            if len(kids) <= 1:
                continue
            key = ("PP", t.i, kids[-1].i)
            if key in seen:
                continue
            seen.add(key)
            chunks.append(("PP", kids, t))
    # VP: 动词性中心词
    for t in doc:
        if t.pos_ in ("VERB", "AUX") and t.dep_ in ("ROOT", "conj", "advcl", "relcl",
                                                    "ccomp", "xcomp", "acl", "ccomp"):
            toks = collect_vp(doc, t)
            if len(toks) < 1:
                continue
            s, e = span_of(toks)
            key = ("VP", s, e)
            if key in seen:
                continue
            seen.add(key)
            chunks.append(("VP", toks, t))
    # ADJP / ADVP
    for t in doc:
        if t.pos_ == "ADJ" and any(c.dep_ in ("advmod", "amod", "acomp", "xcomp") for c in t.children):
            toks = [x for x in t.subtree if x.dep_ != "punct"]
            s, e = span_of(toks)
            key = ("ADJP", s, e)
            if key not in seen:
                seen.add(key); chunks.append(("ADJP", toks, t))
        if t.pos_ == "ADV" and any(c.dep_ == "advmod" for c in t.children):
            toks = [x for x in t.subtree if x.dep_ != "punct"]
            s, e = span_of(toks)
            key = ("ADVP", s, e)
            if key not in seen:
                seen.add(key); chunks.append(("ADVP", toks, t))
    # SBAR: mark/从句引导词 或 从句性依存
    for t in doc:
        is_clause_head = (t.dep_ in ("advcl", "relcl", "ccomp", "acl")) or \
                         (t.dep_ == "mark") or (t.pos_ == "SCONJ" and t.dep_ not in ("punct",))
        if not is_clause_head:
            continue
        toks = [x for x in t.subtree if x.dep_ != "punct"]
        if len(toks) < 3:
            continue
        s, e = span_of(toks)
        key = ("SBAR", s, e)
        if key in seen:
            continue
        seen.add(key)
        root = next((x for x in toks if x.dep_ in ("advcl", "relcl", "ccomp", "acl")), toks[0])
        chunks.append(("SBAR", toks, root))
    chunks.sort(key=lambda c: (c[1][0].i, -(c[1][-1].i)))
    return chunks


def pattern_of(toks, head):
    return "+".join(t.pos_ for t in toks)


def pattern_zh(toks):
    return "+".join(POS_ZH.get(t.pos_, t.pos_) for t in toks)


# ---------------------------------------------------------------- L3 句型与语法点
MODALS = {"can", "could", "may", "might", "must", "shall", "should", "will",
          "would", "need", "dare", "ought"}
REL_MARKERS = {"that", "which", "who", "whom", "whose", "when", "where", "why", "as"}
ADVCL_KIND = {
    "when": "AdverbialTime", "while": "AdverbialTime", "as": "AdverbialTime",
    "after": "AdverbialTime", "before": "AdverbialTime", "until": "AdverbialTime",
    "since": "AdverbialReason", "because": "AdverbialReason", "as": "AdverbialReason",
    "if": "AdverbialCondition", "unless": "AdverbialCondition",
    "although": "AdverbialConcession", "though": "AdverbialConcession",
    "so": "AdverbialResult", "in": "AdverbialPurpose", "for": "AdverbialReason",
}


def root_of(doc):
    return next((t for t in doc if t.dep_ == "ROOT"), None)


def effective_root(doc):
    """有效主句中心：spaCy 偶发把介词/名词立为 ROOT 导致真实主句脱节，
    此时找回「带真实主语（非关系代词）的限定动词」作为主句中心；否则返回原 ROOT。"""
    r = root_of(doc)
    if r is None:
        return None
    if r.pos_ in ("VERB", "AUX"):
        return r
    for v in doc:
        if v.tag_ in ("VBD", "VBP", "VBZ", "MD", "VB") and v.pos_ in ("VERB", "AUX"):
            vs = [c for c in doc if c.head.i == v.i and c.dep_ in ("nsubj", "nsubjpass", "csubj")]
            if vs and all(c.lemma_.lower() not in REL_MARKERS for c in vs):
                return v
    return r


def subtree_text(tok):
    return " ".join(t.text for t in tok.subtree if t.dep_ != "punct")


def tense_aspect(doc):
    """返回 (tense, aspect)"""
    r = effective_root(doc)
    if r is None:
        return "", ""
    chain = [t for t in doc if t.head.i == r.i and t.dep_ in ("aux", "auxpass")] + [r]
    lemmas = [t.lemma_.lower() for t in chain]
    tags = [t.tag_ for t in chain]
    modal = next((l for l, t in zip(lemmas, chain) if t.tag_ == "MD"), None)
    has_be = any(l == "be" and t.dep_ == "aux" for t, l in zip(chain, lemmas))
    has_have = any(l == "have" and t.dep_ == "aux" for t, l in zip(chain, lemmas))
    vbg = any(t.tag_ == "VBG" for t in chain)
    vbn = any(t.tag_ == "VBN" for t in chain)
    have_tag = next((t.tag_ for t, l in zip(chain, lemmas) if t.dep_ == "aux" and l == "have"), "")
    be_tag = next((t.tag_ for t, l in zip(chain, lemmas) if t.dep_ == "aux" and l == "be"), "")
    # 时态
    if "use" in lemmas and any(t.text.lower() == "to" for t in doc):
        return "UsedTo", "一般"
    if modal == "will":
        return ("Future", "进行" if vbg else "一般")
    if modal == "would":
        return "FuturePast", "一般"
    if has_have and vbn:
        base = "PastPerf" if have_tag == "VBD" else "PresPerf"
        if vbg:
            return (base + "Cont", "完成进行")
        return (base, "完成")
    if has_be and vbg:
        return ("Past" if be_tag == "VBD" else "Present", "进行")
    if r.tag_ == "VBD":
        return "Past", "一般"
    if r.tag_ in ("VBP", "VBZ"):
        return "Present", "一般"
    if r.tag_ == "VB" and modal:
        return "Present", "一般"
    return "—", "—"


def detect_pattern(doc):
    r = effective_root(doc)
    if r is None:
        return "Fragment", "非完整句"
    # 仅看主句（ROOT 的直接依存），避免从句成分泄漏到主句句型
    # 主语候选额外纳入被 spaCy 偶发误标为 npadvmod 的名词/代词/专名（如 "Dan wondered…" 中 Dan）
    subj = [t for t in doc if t.head.i == r.i and t.dep_ in ("nsubj", "nsubjpass", "csubj")]
    subj += [t for t in doc if t.head.i == r.i and t.dep_ == "npadvmod"
             and t.pos_ in ("NOUN", "PROPN", "PRON")]
    objs = [t for t in doc if t.head.i == r.i and t.dep_ in ("obj", "dobj")]
    iobjs = [t for t in doc if t.head.i == r.i and t.dep_ == "iobj"]
    comps = [t for t in doc if t.head.i == r.i and t.dep_ in ("attr", "acomp")]
    oprd = [t for t in doc if t.head.i == r.i and t.dep_ == "oprd"]
    xcomp_r = [t for t in doc if t.head.i == r.i and t.dep_ == "xcomp"]
    expl = [t for t in doc if t.head.i == r.i and t.dep_ == "expl"]
    if expl and expl[0].lemma_.lower() == "there" and r.lemma_ == "be":
        return "There-be", "There be 存在句"
    if expl and expl[0].lemma_.lower() == "it" and comps:
        return "It-形式主语", "It 作形式主语"
    if r.lemma_ == "be" and comps:
        return "SVP", "主系表"
    if iobjs and objs:
        return "SVOO", "主谓双宾"
    # 复杂及物（宾补）：宾语 + 宾补（形容词/名词/分词/不定式，且不定式须有宾语在前，即 ask sb to do）
    if objs and (oprd or xcomp_r):
        return "SVOC", "主谓宾补"
    if objs:
        return "SVO", "主谓宾"
    if any(t.head.i == r.i and t.dep_ in ("obl", "advmod", "advcl") for t in doc):
        return "SVA", "主谓+状语"
    if subj:
        return "SV", "主谓"
    # 回退：ROOT 为限定动词（即便主语未检出，亦可能是祈使或解析误差）→ 判为主谓，避免误杀主句
    if (r.pos_ in ("VERB", "AUX") and "Tense=" in str(r.morph)) or r.tag_ in ("VBD", "VBP", "VBZ", "MD", "VB"):
        return "SV", "主谓"
    return "Fragment", "非完整句（碎片/解析待核）"


def detect_clauses(doc):
    out = []
    for t in doc:
        if t.dep_ == "relcl":
            out.append(("CLAUSE.Relative", "定语从句"))
        elif t.dep_ == "acl":
            out.append(("CLAUSE.Relative", "定语从句(分词/不定式)"))
        elif t.dep_ == "advcl":
            mk = [c for c in t.children if c.dep_ == "mark"]
            lm = mk[0].lemma_.lower() if mk else ""
            kind = ADVCL_KIND.get(lm, "Adverbial")
            zh = {"AdverbialTime": "时间状语从句", "AdverbialReason": "原因状语从句",
                  "AdverbialCondition": "条件状语从句", "AdverbialConcession": "让步状语从句",
                  "AdverbialPurpose": "目的状语从句", "AdverbialResult": "结果状语从句",
                  "Adverbial": "状语从句"}[kind]
            out.append(("CLAUSE." + kind, zh))
        elif t.dep_ == "ccomp":
            out.append(("CLAUSE.ObjectClause", "宾语从句"))
        elif t.dep_ in ("csubj",):
            out.append(("CLAUSE.NounClause", "主语从句"))
    # 去重保序
    seen, res = set(), []
    for c in out:
        if c[0] in seen:
            continue
        seen.add(c[0]); res.append(c)
    return res


def detect_grammar(doc, tense, pat):
    pts = []
    r = effective_root(doc)
    texts = [t.text.lower() for t in doc]
    lemmas = [t.lemma_.lower() for t in doc]
    has = lambda w: w in lemmas
    # 时态
    tz = {"Present": "一般现在时", "Past": "一般过去时", "Future": "一般将来时",
          "FuturePast": "过去将来时", "PresPerf": "现在完成时", "PastPerf": "过去完成时",
          "PresPerfCont": "现在完成进行时", "PastPerfCont": "过去完成进行时",
          "UsedTo": "used to 过去习惯"}
    if tense in tz:
        pts.append(("TENSE." + tense, tz[tense]))
    # 语态
    if any(t.dep_ == "auxpass" for t in doc) or any(t.dep_ == "nsubjpass" for t in doc):
        tag = "VOICE.Passive"
        if any(t.tag_ == "MD" for t in doc):
            tag = "VOICE.PassiveModal"
        elif any(t.tag_ == "VBG" for t in doc):
            tag = "VOICE.PassiveProg"
        pts.append((tag, "被动语态"))
    # 情态
    for t in doc:
        if t.tag_ == "MD":
            pts.append(("MODAL." + t.lemma_.capitalize(), "情态动词 %s" % t.lemma_))
    if "have to" in " ".join(lemmas):
        pts.append(("MODAL.HaveTo", "have to 必须"))
    # 从句
    for code, zh in detect_clauses(doc):
        pts.append((code, zh))
    # 非谓语
    for t in doc:
        if t.tag_ == "VBG" and t.dep_ in ("acl", "advcl", "amod", "csubj"):
            pts.append(("NONFINITE.Participle", "现在分词作修饰/状语"))
        if t.tag_ == "VBG" and t.dep_ in ("csubj", "attr", "obj", "xcomp"):
            pts.append(("NONFINITE.Gerund", "动名词"))
        if t.tag_ == "VBN" and t.dep_ in ("acl", "advcl", "amod"):
            pts.append(("NONFINITE.PastParticiple", "过去分词作定语/状语"))
        if t.tag_ == "VB" and t.head.tag_ != "MD" and t.dep_ in ("xcomp", "ccomp", "advcl", "acl", "csubj"):
            pts.append(("NONFINITE.Infinitive", "不定式"))
        if t.tag_ == "VB" and t.dep_ == "xcomp" and t.head.lemma_ in ("tell", "ask", "want", "make", "let", "see", "hear", "order", "advise"):
            pts.append(("NONFINITE.Infinitive", "不定式作宾补"))
    # 语气/句类
    if doc[-1].text == "?":
        wh = {"what", "who", "whom", "whose", "which", "when", "where", "why", "how"}
        if any(l in wh for l in lemmas[:4]):
            pts.append(("QUESTION.Wh", "特殊疑问句"))
        else:
            pts.append(("QUESTION.YesNo", "一般疑问句"))
        if has("n't") or has("not"):
            pass
    if doc[-1].text == "!":
        pts.append(("MOOD.Exclamative", "感叹句"))
        if has("what") or has("how"):
            pts.append(("STRUCT.Exclamative", "What/How 感叹句"))
    if r is not None and r.tag_ == "VB" and not any(t.dep_ in ("nsubj", "nsubjpass", "csubj") for t in doc) \
       and not any(t.dep_ == "aux" for t in doc):
        pts.append(("MOOD.Imperative", "祈使句"))
    if has("were") or has("would") and has("if"):
        pts.append(("MOOD.Subjunctive", "虚拟语气"))
    # 否定
    for w, zh in (("not", "否定的 not"), ("never", "否定的 never"), ("no", "否定的 no"),
                  ("hardly", "半否定 hardly"), ("neither", "否定 neither"), ("nor", "否定 nor")):
        if has(w):
            pts.append(("NEGATION." + w.capitalize(), zh))
            break
    # 特殊结构
    if pat[0] == "There-be":
        pts.append(("STRUCT.ThereBe", "There be 存在句"))
    if pat[0] == "It-形式主语":
        pts.append(("STRUCT.ItFormal", "It 作形式主语"))
    if has("so") and has("that"):
        pts.append(("STRUCT.SoThat", "so...that 结果/程度"))
    if has("too") and has("to"):
        pts.append(("STRUCT.TooTo", "too...to 太…以致不能"))
    if has("than"):
        pts.append(("STRUCT.Comparative", "比较级 + than"))
    if any(t.tag_ in ("JJS", "RBS") for t in doc):
        pts.append(("STRUCT.Superlative", "最高级"))
    if any(t.tag_ in ("JJR", "RBR") for t in doc):
        pts.append(("STRUCT.Comparative", "比较级"))
    if has("either") or has("neither"):
        pts.append(("STRUCT.EitherOr", "either/neither 并列"))
    if has("only") and any(l == "also" for l in lemmas):
        pts.append(("STRUCT.NotOnlyButAlso", "not only...but also"))
    # 强调句 / 倒装
    if lemmas[:3] == ["it", "be"] and has("that"):
        pts.append(("STRUCT.Cleft", "强调句 It is ... that"))
    if lemmas and lemmas[0] in ("never", "seldom", "hardly", "only", "not") and \
       any(t.dep_ == "aux" and t.i < (r.i if r else 0) for t in doc):
        pts.append(("STRUCT.Inversion", "部分倒装"))
    # 句型
    pzh = {"SV": "主谓", "SVO": "主谓宾", "SVP": "主系表", "SVOO": "主谓双宾",
           "SVOC": "主谓宾补", "SVA": "主谓+状语"}
    if pat[0] in pzh:
        pts.append(("PATTERN." + pat[0], pzh[pat[0]] + "句型"))
    if any(t.dep_ == "cc" for t in doc):
        pts.append(("PATTERN.Coordinate", "并列结构"))
    # 去重保序
    seen, res = set(), []
    for c, z in pts:
        if c in seen:
            continue
        seen.add(c); res.append((c, z))
        GRAMMAR_ZH[c] = z
    return res


def key_structure(doc, pat):
    lemmas = [t.lemma_.lower() for t in doc]
    if pat == "There-be":
        return "There be + 名词 + (地点/时间状语)"
    if pat == "It-形式主语":
        return "It is + adj/n + to do / that 从句"
    if "so" in lemmas and "that" in lemmas:
        return "so + adj/adv + that 从句"
    if "too" in lemmas and "to" in lemmas:
        return "too + adj + to do"
    if "such" in lemmas and "that" in lemmas:
        return "such + (a/an) + adj + n + that 从句"
    if "than" in lemmas:
        return "比较级 + than"
    if "used" in lemmas and "to" in lemmas:
        return "used to + 动词原形（过去习惯）"
    if "there" == lemmas[0] if lemmas else False:
        return "There be + 名词"
    root = effective_root(doc)
    if root is not None and root.lemma_ == "be":
        return "主语 + be + 表语"
    if root is not None:
        return "主语 + %s + %s" % (root.lemma_, "宾语/状语")
    return ""


def parse_tree(doc):
    """依存树转写的近似短语结构树（非 Penn 原版，供教师核对）"""
    r = effective_root(doc)
    if r is None:
        return ""
    def label(t):
        return {"VERB": "VP", "AUX": "VP", "NOUN": "NP", "PROPN": "NP", "PRON": "NP",
                "ADP": "PP", "ADJ": "ADJP", "ADV": "ADVP", "SCONJ": "SBAR",
                "CCONJ": "CONJP", "NUM": "NP", "DET": "NP"}.get(t.pos_, t.tag_)
    def walk(t):
        kids = [c for c in t.children if c.dep_ != "punct"]
        leaf = "(%s %s)" % (t.tag_, t.text.replace("(", "[").replace(")", "]"))
        if not kids:
            return leaf
        units = [(t.i, leaf)] + [(c.i, walk(c)) for c in kids]
        units.sort(key=lambda x: x[0])
        inner = " ".join(u[1] for u in units)
        return "(%s %s)" % (label(t), inner)
    return walk(r)


# ---------------------------------------------------------------- 主流程
def main():
    lessons = json.load(open(os.path.join(DATA, "nce2_lessons.json"), encoding="utf-8"))["lessons"]
    zh_map = {}
    title_zh = {}
    zp = os.path.join(DATA, "nce2_zh.json")
    if os.path.exists(zp):
        for l in json.load(open(zp, encoding="utf-8"))["lessons"]:
            zh_map[l["no"]] = {x["i"]: x["zh"] for x in l["lines"]}
            title_zh[l["no"]] = l.get("titleZh", "")
    vmap = load_vocab_map(_a.vocab_csv)
    if _a.limit:
        lessons = lessons[:_a.limit]

    os.makedirs(OUT, exist_ok=True)
    rows_tok, rows_chunk, rows_sent, rows_lesson = [], [], [], []
    gp_counter = collections.Counter()
    gp_first = {}          # code → (lesson, 英, 译)
    pos_cnt, dep_cnt, chunk_cnt, pat_cnt = (collections.Counter(), collections.Counter(),
                                            collections.Counter(), collections.Counter())
    tense_cnt, voice_cnt = collections.Counter(), collections.Counter()
    nlp = NLP

    for li, les in enumerate(lessons):
        no = les["no"]
        unit = (no - 1) // 24 + 1
        body = les["lines"][3:] if les.get("instruction") else les["lines"][1:]
        zhs = zh_map.get(no, {})
        lpat = collections.Counter()
        for si, b in enumerate(body):
            text = b["text"]
            doc = nlp(text)
            zh = zhs.get(si, "")
            r = effective_root(doc)
            # ---------- L1 token ----------
            for t in doc:
                if t.is_space:
                    continue
                lm = t.lemma_.lower() if t.lemma_ != "-PRON-" else t.text.lower()
                layer, cefr, csrc = vmap.get(lm, vmap.get(t.text.lower(), ("", "", "")))
                gf = []
                ms = str(t.morph)
                for k in ("Tense=", "Number=", "Degree=", "VerbForm=", "Case=", "Person=", "Mood="):
                    if k in ms:
                        gf.append(MORPH_ZH.get([p for p in ms.split("|") if p.startswith(k)][0],
                                               [p for p in ms.split("|") if p.startswith(k)][0]))
                if t.dep_ == "auxpass":
                    gf.append("被动")
                if t.tag_ == "MD":
                    gf.append("情态")
                rows_tok.append({
                    "lesson": no, "unit": unit, "sentId": si, "tokId": t.i,
                    "word": t.text, "lemma": (t.lemma_ if t.lemma_ != "-PRON-" else t.text),
                    "pos": t.pos_, "posZh": POS_ZH.get(t.pos_, t.pos_),
                    "tag": t.tag_, "tagZh": TAG_ZH.get(t.tag_, t.tag_),
                    "morph": ms, "morphZh": mz(ms),
                    "dep": t.dep_, "depZh": DEP_ZH.get(t.dep_, t.dep_),
                    "headIdx": t.head.i, "head": t.head.text, "headPos": t.head.pos_,
                    "isStop": "Y" if (t.is_stop and t.pos_ not in ("PUNCT",)) else "",
                    "layer": layer, "cefr": cefr, "cefrSrc": csrc,
                    "gramFeature": "｜".join(gf), "sentence": text,
                })
                pos_cnt[t.pos_] += 1
                dep_cnt[t.dep_] += 1
            # ---------- L2 chunk ----------
            for ctype, toks, head in extract_chunks(doc):
                s, e = span_of(toks)
                txt = " ".join(t.text for t in toks)
                lm_txt = " ".join((t.lemma_ if t.lemma_ != "-PRON-" else t.text) for t in toks)
                rows_chunk.append({
                    "lesson": no, "unit": unit, "sentId": si,
                    "chunkType": ctype, "chunkTypeZh": CHUNK_ZH.get(ctype, ctype),
                    "text": txt, "lemma": lm_txt,
                    "start": s, "end": e, "length": len(toks),
                    "headIdx": head.i, "headText": head.text, "headPos": head.pos_,
                    "pattern": pattern_of(toks, head), "patternZh": pattern_zh(toks),
                    "dep": head.dep_, "depZh": DEP_ZH.get(head.dep_, head.dep_),
                    "governor": head.head.text if head.head.i != head.i else "",
                    "teachTag": teach_tag(ctype, toks, head, doc),
                    "sentence": text, "sentZh": zh,
                })
                chunk_cnt[ctype] += 1
            # ---------- L3 sentence ----------
            tense, aspect = tense_aspect(doc)
            pat, pat_zh = detect_pattern(doc)
            r0 = effective_root(doc)
            subj = [t for t in doc if t.head.i == r0.i and t.dep_ in ("nsubj", "nsubjpass", "csubj")]
            subj += [t for t in doc if t.head.i == r0.i and t.dep_ == "npadvmod"
                     and t.pos_ in ("NOUN", "PROPN", "PRON")]
            objs = [t for t in doc if t.head.i == r0.i and t.dep_ in ("obj", "dobj")]
            iobjs = [t for t in doc if t.head.i == r0.i and t.dep_ == "iobj"]
            comps = [t for t in doc if t.head.i == r0.i and t.dep_ in ("attr", "acomp")]
            oprd = [t for t in doc if t.head.i == r0.i and t.dep_ in ("oprd", "xcomp")]
            adjn = [t for t in doc if t.head.i == r0.i and t.dep_ in ("obl", "advmod", "advcl")]
            voice = "被动" if (any(t.dep_ == "auxpass" for t in doc) or
                              any(t.dep_ == "nsubjpass" for t in doc)) else "主动"
            mood = "陈述"
            if doc[-1].text == "?":
                mood = "疑问"
            elif r is not None and r.tag_ == "VB" and not subj:
                mood = "祈使"
            elif doc[-1].text == "!":
                mood = "感叹"
            neg = "Y" if any(t.dep_ == "neg" or t.lemma_.lower() in
                             ("never", "neither", "nor") for t in doc) else ""
            modal = " ".join(sorted({t.lemma_.lower() for t in doc if t.tag_ == "MD"}))
            cl = detect_clauses(doc)
            rel = " ".join(sorted({t.text.lower() for t in doc
                                   if t.dep_ in ("relcl", "acl", "mark") or
                                   (t.tag_ in ("WDT", "WP", "WRB"))} & REL_MARKERS))
            coord = " ".join(sorted({t.lemma_.lower() for t in doc if t.dep_ == "cc"}))
            gps = detect_grammar(doc, tense, (pat, pat_zh))
            for c, z in gps:
                gp_counter[c] += 1
                if c not in gp_first:
                    gp_first[c] = (no, text, zh)
            rows_sent.append({
                "lesson": no, "unit": unit, "sentId": si, "titleZh": title_zh.get(no, ""),
                "text": text, "textZh": zh,
                "len": len(doc), "wordCount": sum(1 for t in doc if not t.is_punct),
                "sentType": mood, "clauseType": clause_type(doc),
                "pattern": pat, "patternZh": pat_zh,
                "subject": " / ".join(subtree_text(t) for t in subj),
                "verb": (r.text if r else ""),
                "object": " / ".join(subtree_text(t) for t in objs),
                "indirectObject": " / ".join(subtree_text(t) for t in iobjs),
                "complement": " / ".join(subtree_text(t) for t in comps + oprd),
                "adjunct": " / ".join(subtree_text(t) for t in adjn[:2]),
                "tense": tense, "aspect": aspect, "voice": voice, "mood": mood,
                "negation": neg, "modality": modal,
                "subClauses": "；".join(z for _, z in cl),
                "relMarker": rel, "coordinator": coord,
                "grammarPoints": "；".join(c for c, _ in gps),
                "grammarPointsZh": "；".join(z for _, z in gps),
                "keyStructure": key_structure(doc, pat),
                "parseTree": parse_tree(doc),
            })
            pat_cnt[pat] += 1
            lpat[pat] += 1
            tense_cnt[tense] += 1
            voice_cnt[voice] += 1
        rows_lesson.append({
            "课号": no, "单元": unit, "标题": les["title"],
            "句数": len(body),
            "token数": sum(1 for r in rows_tok if r["lesson"] == no),
            "实词数": sum(1 for r in rows_tok if r["lesson"] == no and not r["isStop"]),
            "平均句长": round(sum(1 for r in rows_tok if r["lesson"] == no) / max(1, len(body)), 1),
            "语块数": sum(1 for r in rows_chunk if r["lesson"] == no),
            "语法点数": len({c for r in rows_sent if r["lesson"] == no
                             for c in r["grammarPoints"].split("；") if c}),
            **{("句型_" + k): v for k, v in lpat.items()},
        })
        if li % 12 == 0:
            print("  已处理 %d/%d 课" % (li + 1, len(lessons)))

    # ---------------- CSV 写出 ----------------
    def dump(name, rows, cols=None):
        if not rows:
            return
        cols = cols or list(rows[0].keys())
        p = os.path.join(OUT, name)
        with open(p, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        print("%-28s %6d 行  %.1f KB" % (name, len(rows), os.path.getsize(p) / 1024))

    dump("NCE2_词性标注.csv", rows_tok)
    dump("NCE2_语块标注.csv", rows_chunk)
    dump("NCE2_句型标注.csv", rows_sent)
    dump("NCE2_单课标注概览.csv", rows_lesson)
    gp_rows = []
    for code, n in gp_counter.most_common():
        no, ex, zhx = gp_first.get(code, ("", "", ""))
        gp_rows.append({"语法点代码": code, "中文名": GRAMMAR_ZH.get(code, code),
                        "分类": code.split(".")[0], "句数": n, "首现课": no,
                        "例句": ex, "译文": zhx})
    dump("NCE2_语法点清单.csv", gp_rows)

    payload = {
        "generatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "model": _a.model,
        "stat": {"lessons": len(lessons), "sent": len(rows_sent), "token": len(rows_tok),
                 "chunk": len(rows_chunk), "grammarPoints": len(gp_rows)},
        "distrib": {"pos": dict(pos_cnt.most_common()), "dep": dict(dep_cnt.most_common(30)),
                    "chunk": dict(chunk_cnt.most_common()), "pattern": dict(pat_cnt.most_common()),
                    "tense": dict(tense_cnt.most_common()), "voice": dict(voice_cnt.most_common())},
        "tokens": rows_tok, "chunks": rows_chunk, "sents": [
            {k: v for k, v in r.items() if k != "parseTree"} for r in rows_sent],
        "trees": [{"lesson": r["lesson"], "sentId": r["sentId"], "tree": r["parseTree"]}
                  for r in rows_sent],
        "grammar": gp_rows, "lessons": rows_lesson,
    }
    pj = os.path.join(OUT, "_payload_grammar.json")
    json.dump(payload, open(pj, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("payload %.1f KB" % (os.path.getsize(pj) / 1024))
    print("句型分布:", dict(pat_cnt.most_common()))
    print("语法点数:", len(gp_rows))


def teach_tag(ctype, toks, head, doc):
    """语块教学标签"""
    pat = pattern_of(toks, head)
    if ctype == "NP":
        if pat.startswith("DET+ADJ+NOUN"):
            return "冠词+形+名"
        if pat.startswith("DET+NOUN"):
            return "冠词+名"
        if "ADJ" in pat:
            return "形容词修饰名词"
        if pat == "PRON":
            return "代词作名词短语"
        if "NOUN+NOUN" in pat or "PROPN" in pat:
            return "名词作定语/专名"
        return "名词短语"
    if ctype == "VP":
        if any(t.dep_ == "auxpass" for t in toks):
            return "被动谓语"
        if any(t.tag_ == "VBG" for t in toks) and any(t.lemma_ == "be" for t in toks):
            return "进行时态谓语"
        if any(t.tag_ == "VBN" for t in toks) and any(t.lemma_ == "have" for t in toks):
            return "完成时态谓语"
        if any(t.dep_ == "prt" for t in toks):
            return "短语动词"
        if any(t.tag_ == "MD" for t in toks):
            return "情态谓语"
        return "动词短语"
    if ctype == "PP":
        return "介词短语作%s" % ("状语" if head.dep_ in ("advmod", "obl", "advcl") else "定语/表语")
    if ctype == "SBAR":
        return {"advcl": "状语从句", "relcl": "定语从句", "ccomp": "宾语从句",
                "acl": "定语性从句", "mark": "从句"}.get(head.dep_, "从句")
    if ctype == "ADJP":
        return "形容词短语"
    if ctype == "ADVP":
        return "副词短语"
    return ctype


def clause_type(doc):
    has_sub = any(t.dep_ in ("advcl", "relcl", "ccomp", "acl", "csubj") for t in doc)
    has_coord = any(t.dep_ == "cc" for t in doc)
    if has_sub and has_coord:
        return "并列复合句"
    if has_sub:
        return "复合句"
    if has_coord:
        return "并列句"
    return "简单句"


if __name__ == "__main__":
    main()
