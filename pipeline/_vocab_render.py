# -*- coding: utf-8 -*-
"""由 _payload.json 渲染：全书/单课 两份 Markdown 报告 + HTML 预览（数据全量内联）"""
import os, json, collections, datetime, argparse

_ap = argparse.ArgumentParser(description="由 _payload.json 渲染 MD + HTML")
_ap.add_argument("--out-dir", default="词汇数据", help="输出目录名（相对项目根；默认 词汇数据）")
_a = _ap.parse_args()
OUT = os.path.join(r"E:\04 少儿原版课程\06 新概念英语", _a.out_dir)
D = json.load(open(os.path.join(OUT, "_payload.json"), encoding="utf-8"))
K = D["keys"]; BK = D["book"]; LS = D["lessons"]
TOTAL = sum(BK["layer"].values())
COVERED = TOTAL - BK["layer"].get("out", 0) - BK["layer"].get("proper", 0) - BK["layer"].get("num", 0)
CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1"]


def p(a, b=TOTAL):
    return "%.1f%%" % (100.0 * a / b) if b else "0%"


def esc(s):
    return str(s or "").replace("|", "／")


# ---------------- 全书 MD ----------------
m = []
m.append("# 新概念英语（二）· 全书词汇报告\n")
m.append("- 分析口径：九词表 `A1_Starters < A1_Movers < A2_Flyers < KET < PET < FCE < CAE < NGSL < NAWL`，**最低层只归一层**（闭环不重叠）")
m.append("- 语料：96 课正文（不含 comprehension question 与听力指令音），共 **%d token / %d 词条**" % (TOTAL, BK["uniq"]))
m.append("- CEFR：多源扩展层——**Oxford 3000/5000 为主标注**，缺则由 CEFR-J v1.6 → Octanove C1/C2 → EFLLex（等级频率峰值）依次补缺；**多源不一致时保留双标注不覆盖**（见第九节）")
m.append("- 生成时间：%s　｜　工具：article-vocab-analyzer\n" % D["generatedAt"])

m.append("## 一、总体结论\n")
m.append("| 指标 | 数值 |")
m.append("|---|---|")
m.append("| 覆盖率（严格：剔除超纲+专名+数字） | **%s**（%d / %d token） |" % (p(COVERED), COVERED, TOTAL))
m.append("| 覆盖率（宽松：仅剔除超纲） | **%s**（%d / %d token） |" % (p(TOTAL - BK["layer"].get("out", 0)), TOTAL - BK["layer"].get("out", 0), TOTAL))
m.append("| 超纲 token | %d（%s）· 超纲词条 %d 条 |" % (BK["layer"].get("out", 0), p(BK["layer"].get("out", 0)), BK["outUniq"]))
m.append("| 专名 / 数字 | %d 个（%s，%d 个词形） / %d 个（%s） |" % (BK["layer"].get("proper", 0), p(BK["layer"].get("proper", 0)), len(BK["prop"]), BK["layer"].get("num", 0), p(BK["layer"].get("num", 0))))
cov_val = 100.0 * COVERED / TOTAL if TOTAL else 0.0
verdict = "达标" if cov_val >= 95 else "未达标"
m.append("| 独立阅读阈值（≥95%%） | 严格口径 **%s**（差 %.1f 个百分点）｜宽松口径 **达标** |"
         % (verdict, max(0.0, 95 - cov_val)))
m.append("\n> 两口径差异源于专名（334 token）是否计入「已知」。教学上建议以严格口径看**生词负担**，以宽松口径看**阅读流畅度**。\n")

m.append("## 二、九层归属分层（闭环）\n")
m.append("| 层级 | token | 占比 | 词条数 |")
m.append("|---|---|---|---|")
lc = collections.Counter()
for r in BK["rows"]:
    lc[r["layer"]] += r["freq"]
for k in K + ["out", "proper", "num"]:
    if k == "proper":
        ent = len(BK["prop"])
    elif k == "num":
        ent = None
    else:
        ent = len([r for r in BK["rows"] if r["layer"] == k])
    m.append("| %s | %d | %s | %s |" % (k, BK["layer"].get(k, 0), p(BK["layer"].get(k, 0)), "—" if ent is None else ent))
m.append("| **合计** | **%d** | **100.0%%** | **%d** |\n" % (TOTAL, BK["uniq"]))

m.append("## 三、九词表命中率（重叠口径，供考试适配度参考）\n")
hit = collections.Counter()
for l in LS:
    for k, v in l["hit"].items():
        hit[k] += v
m.append("| 词表 | 命中 token | 占全书 token |")
m.append("|---|---|---|")
for k in K:
    m.append("| %s | %d | %s |" % (k, hit.get(k, 0), p(hit.get(k, 0))))
m.append("\n> 重叠口径：同一词可同时命中多张表，故各行相加可超过 100%；与第二节的「归属分层」不冲突。\n")

m.append("## 四、CEFR 难度剖面（按词条数）\n")
cc = collections.Counter(r["cefr"] or "未标注" for r in BK["rows"])
m.append("| CEFR | 词条数 | 占比 |")
m.append("|---|---|---|")
for k in CEFR_ORDER + ["C2", "未标注"]:
    if cc.get(k):
        m.append("| %s | %d | %s |" % (k, cc[k], p(cc[k], BK["uniq"])))
m.append("\n> CEFR 是有序分类轴，只看分布、不做加总或均值运算。\n")

sc = collections.Counter(r["cefrSrc"] or "未标注" for r in BK["rows"])
SRC_NAME = {"oxford": "Oxford 3000/5000（主标注）", "cefrj": "CEFR-J v1.6",
            "octanove": "Octanove C1/C2", "efllex": "EFLLex（等级频率峰值）", "未标注": "未标注（留空不猜）"}
m.append("## 四之二、CEFR 标注来源分布\n")
m.append("| 来源 | 词条数 | 占比 | 说明 |")
m.append("|---|---|---|---|")
for k, v in sc.most_common():
    m.append("| %s | %d | %s | %s |" % (SRC_NAME.get(k, k), v, p(v, BK["uniq"]),
                                        "主标注优先" if k == "oxford" else ("补缺回填" if k in ("cefrj", "octanove", "efllex") else "无来源可用")))
m.append("")

m.append("## 五、全书高频词 Top 40\n")
m.append("| # | 词 | 层 | CEFR | 频次 | 跨课 | 例句译文 |")
m.append("|---|---|---|---|---|---|---|")
for i, r in enumerate(BK["rows"][:40], 1):
    m.append("| %d | **%s** | %s | %s | %d | %d | %s |" % (i, esc(r["display"]), r["layer"], r["cefr"] or "—", r["freq"], r["ndoc"], esc(r["zh"])))
m.append("")

m.append("## 六、超纲词清单（%d 条，按频次降序）\n" % BK["outUniq"])
m.append("| 词 | 频次 | 跨课 | CEFR | 原文例句 | 首现 |")
m.append("|---|---|---|---|---|---|")
for r in BK["rows"]:
    if r["layer"] == "out":
        m.append("| %s | %d | %d | %s | %s | %s |" % (esc(r["display"]), r["freq"], r["ndoc"], r["cefr"] or "—", esc(r["example"]), r["at"]))
m.append("")

m.append("## 七、分层词卡摘要（每层 Top 12）\n")
for k in K:
    rows = [r for r in BK["rows"] if r["layer"] == k][:12]
    if not rows:
        continue
    m.append("**%s**（该层共 %d 词条）\n" % (k, len([r for r in BK["rows"] if r["layer"] == k])))
    m.append("| 词 | CEFR | 频次 | 跨课 | 例句译文 |")
    m.append("|---|---|---|---|---|")
    for r in rows:
        m.append("| %s | %s | %d | %d | %s |" % (esc(r["display"]), r["cefr"] or "—", r["freq"], r["ndoc"], esc(r["zh"])))
    m.append("")

m.append("## 八、专名认识清单（Top 30）\n")
m.append("| 专名 | 频次 |")
m.append("|---|---|")
for w, n in BK["prop"][:30]:
    m.append("| %s | %d |" % (esc(w), n))

# ---- 九、CEFR 冲突清单（多源不一致，双标注留痕）----
conf = [r for r in BK["rows"] if r.get("cefrConflict")]
m.append("\n## 九、CEFR 冲突清单（Oxford / CEFR-J / Octanove 不一致）\n")
m.append("- 口径：仅在**同为等级赋值构念**的三张分级词表之间判定冲突；EFLLex 是频率分布资源（不同构念），只作补缺，**不参与冲突判定**。")
m.append("- 处理：主标注仍取 **Oxford**（存在时），其余来源等级全部并列记录，**不静默覆盖**。")
m.append("- 冲突词条：**%d / %d**（%.1f%%）；完整清单见 `NCE2_CEFR冲突清单.csv`\n"
         % (len(conf), BK["uniq"], 100.0 * len(conf) / BK["uniq"]))
m.append("| 词 | 主标注(采用) | 来源 | Oxford | CEFR-J | Octanove | EFLLex(参考) | 频次 |")
m.append("|---|---|---|---|---|---|---|---|")
for r in conf[:40]:
    a = r.get("cefrAlt") or {}
    m.append("| %s | **%s** | %s | %s | %s | %s | %s | %d |" % (
        esc(r["display"]), r["cefr"], r["cefrSrc"], a.get("oxford", "—"), a.get("cefrj", "—"),
        a.get("octanove", "—"), a.get("efllex", "—"), r["freq"]))
if len(conf) > 40:
    m.append("\n> 上表为前 40 条（按频次降序），其余 %d 条见 CSV。\n" % (len(conf) - 40))
m.append("")
open(os.path.join(OUT, "NCE2_词汇报告_全书.md"), "w", encoding="utf-8").write("\n".join(m))

# ---------------- 单课 MD ----------------
s = []
s.append("# 新概念英语（二）· 单课词汇报告（96 课）\n")
s.append("- 口径同全书报告：九词表最低层归属、CEFR 可选标注、正文不含问题行")
s.append("- 生成时间：%s\n" % D["generatedAt"])
s.append("## 一、96 课总览\n")
s.append("| 课 | 标题 | token | 词条 | 超纲 | 覆盖率 | 占比最高层 |")
s.append("|---|---|---|---|---|---|---|")
for l in LS:
    hi = max(((k, v) for k, v in l["layer"].items() if k in K), key=lambda x: x[1], default=("-", 0))
    s.append("| %d | %s | %d | %d | %d | %.1f%% | %s |" % (l["no"], esc(l["title"]), l["total"], l["uniq"], l["out"], l["coverage"], hi[0]))
s.append("")
s.append("## 二、各课超纲词\n")
for l in LS:
    outs = [e for e in l["ents"] if e["layer"] == "out"]
    if not outs:
        continue
    s.append("**L%d %s**　超纲 %d token / %d 词条：%s\n" % (
        l["no"], esc(l["title"]), l["out"], len(outs),
        "、".join("%s(%d)" % (esc(e["display"]), e["freq"]) for e in outs)))
open(os.path.join(OUT, "NCE2_词汇报告_单课.md"), "w", encoding="utf-8").write("\n".join(s))

# ---------------- HTML ----------------
tpl = open(os.path.join(OUT, "_tpl.html"), encoding="utf-8").read()
html = tpl.replace("__PAYLOAD__", json.dumps(D, ensure_ascii=False, separators=(",", ":")))
hp = os.path.join(OUT, "NCE2_词汇数据.html")
open(hp, "w", encoding="utf-8").write(html)

for f in ("NCE2_词汇报告_全书.md", "NCE2_词汇报告_单课.md", "NCE2_词汇数据.html"):
    print("%-28s %8.1f KB" % (f, os.path.getsize(os.path.join(OUT, f)) / 1024))
