# -*- coding: utf-8 -*-
"""对齐正典 SRT 生成器（NCE2 96 课 · 执行标准定案 2026-10-31）

生成链（顺序不可乱）：
  1. LRC 起点（权威）+ 官方 MP3
  2. _audio_boundary_audit.py 静音带吸附 → nce2-echoloop/data/L{NN}.json 的 t/t2
  3. 本脚本：t/t2 → 对齐正典/L{NN}.srt（双语）★ 对齐唯一正典，人工校对改这里
  4. EchoLoop导入包/{NN}－{title}.srt 同步重生成（同一时间轴）

修订流：发现偏差 → 听音频改正典 SRT → 手工同步回 data json t/t2 → 重跑本脚本。
禁止：直接手改 data/*.json（生成物，重跑构建即丢）；不做 Whisper 重对齐（LRC 边界已验证健康）。
SRT 格式：序号 / start --> end / 英文行 / 中文行 / 空行。
"""
import json, os, re

BASE = r"E:\04 少儿原版课程\06 新概念英语"
APP_DATA = os.path.join(BASE, "nce2-echoloop", "data")
OUT_EX = os.path.join(BASE, "对齐正典")
OUT_IMP = os.path.join(BASE, "EchoLoop导入包")

def ts(sec):
    sec = max(0.0, float(sec))
    h = int(sec // 3600); m = int(sec % 3600 // 60); s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    if ms == 1000: s += 1; ms = 0
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)

os.makedirs(OUT_EX, exist_ok=True)
os.makedirs(OUT_IMP, exist_ok=True)

ok = fail = 0
for no in range(1, 97):
    jf = os.path.join(APP_DATA, "L%02d.json" % no)
    if not os.path.exists(jf):
        print("L%02d: 缺数据，跳过" % no); fail += 1; continue
    d = json.load(open(jf, encoding="utf-8"))
    ss = d.get("sentences") or []
    if not ss:
        print("L%02d: 无句子，跳过" % no); fail += 1; continue

    def build(with_q):
        lines = []
        cues = []
        if with_q and d.get("question"):
            q = d["question"]
            cues.append(("听前预测", q.get("en",""), q.get("zh","")))
        for s in ss:
            cues.append((None, s.get("en",""), s.get("zh","")))
        # 正典：句级 cue 用 t/t2；预测题挂在第一句之前（start=0, end=首句 t）
        n = 0
        for ci, (tag, en, zh) in enumerate(cues):
            n += 1
            if ci == 0 and tag:
                st, en2 = 0.0, ss[0]["t"]
            else:
                idx = ci - (1 if cues[0][0] else 0)
                st = ss[idx]["t"]; en2 = ss[idx]["t2"]
            lines.append(str(n))
            lines.append(ts(st) + " --> " + ts(max(en2, st + 0.5)))
            lines.append(en)
            if zh: lines.append(zh)
            lines.append("")
        return "\n".join(lines)

    # 对齐正典（含预测题 cue，便于听校时对齐上下文）
    open(os.path.join(OUT_EX, "L%02d.srt" % no), "w", encoding="utf-8-sig").write(build(True))
    # EchoLoop 导入包（原命名规则：NN－Title.srt）
    title = re.sub(r'[\\/:*?"<>|]', "", d.get("title") or ("L%02d" % no))
    open(os.path.join(OUT_IMP, "%02d－%s.srt" % (no, title)), "w", encoding="utf-8-sig").write(build(False))
    ok += 1

print("完成：正典 %d 份（对齐正典/），导入包 %d 份（EchoLoop导入包/），失败 %d" % (ok, ok, fail))
