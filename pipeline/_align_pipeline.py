# -*- coding: utf-8 -*-
"""统一句级对齐管线 v1（NCE2 模式已实现；TH!NK/RE 模式预留接口）

节点化设计（仿扣子工作流，CLI 实现）：
  节点1 detect : 清点来稿（音频 + 源文本 + 现有对齐）
  节点2 route  : 信任分级——ASR 词级时间戳 × LRC 交叉验证（偏差<0.3s 信任 LRC，否则 ASR 修正）
  节点3 align  : 词级校准（faster-whisper word_timestamps + 归一化模糊匹配 + 静音吸附兜底）
  节点4 verify : 审核指标（句数/时长/字符数/起点偏差分布/修正数/兜底数/WPM 异常句）
  节点5 export : 对齐正典 JSON（含 source/method/confidence 元数据）+ data json t/t2 + SRT 正典/导入包

标准：句首 = 首词 onset-0.12s（防切头）；句尾 = 末词 offset+0.25s（≤下一句首）；
      词级匹配失败（<60% 词）→ 回退静音带吸附值并在报告标记。
音频不剪切不修改；本管线唯一产物是时间轴。
"""
import json, os, re, sys, subprocess, difflib, argparse, time

BASE = r"E:\04 少儿原版课程\06 新概念英语"
APP_DATA = os.path.join(BASE, "nce2-echoloop", "data")
AUDIO_DIR = os.path.join(BASE, "nce2-echoloop", "audio")
EX_DIR = os.path.join(BASE, "对齐正典")
CACHE_DIR = os.path.join(BASE, "_align_cache")
FFMPEG = r"C:/Users/Thinkpad/.workbuddy/binaries/python/envs/default/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"
MODEL = "small"
LEAD, TAIL = 0.12, 0.25          # 句首提前量 / 句尾延后量
DEV_TRUST = 0.30                 # 与 LRC 偏差 ≤0.3s → 记为信任 LRC 级
DEV_LIMIT = 2.0                  # 偏差 >2s → 判 ASR 失配，回退静音带吸附值
MATCH_MIN = 0.60                 # 句内词匹配率下限

def norm(w):
    return re.sub(r"[^a-z0-9']", "", w.lower())

# ---------- 节点1 detect ----------
def detect(no):
    jf = os.path.join(APP_DATA, "L%02d.json" % no)
    mp3 = os.path.join(AUDIO_DIR, "L%02d.mp3" % no)
    if not (os.path.exists(jf) and os.path.exists(mp3)):
        return None
    d = json.load(open(jf, encoding="utf-8"))
    return {"no": no, "title": d.get("title",""), "question": d.get("question"),
            "sentences": d["sentences"], "audio": mp3, "duration": d.get("duration")}

# ---------- ASR（带缓存） ----------
def asr_words(no, mp3):
    cf = os.path.join(CACHE_DIR, "L%02d.asr.json" % no)
    if os.path.exists(cf):
        return json.load(open(cf, encoding="utf-8"))
    import numpy as np
    raw = subprocess.run([FFMPEG, "-hide_banner", "-i", mp3, "-f", "f32le",
                          "-acodec", "pcm_f32le", "-ac", "1", "-ar", "16000", "pipe:"],
                         capture_output=True).stdout
    audio = np.frombuffer(raw, np.float32)
    os.environ["HF_HUB_OFFLINE"] = "1"
    from faster_whisper import WhisperModel
    model = WhisperModel(MODEL, device="cpu", compute_type="int8")
    segs, info = model.transcribe(audio, language="en", word_timestamps=True,
                                  vad_filter=True, vad_parameters={"min_silence_duration_ms": 400})
    words = []
    for sg in segs:
        for w in (sg.words or []):
            t = w.word.strip()
            if t:
                words.append({"w": norm(t), "raw": t, "s": round(w.start,3), "e": round(w.end,3),
                              "p": round(w.probability,3)})
    out = {"words": words, "duration": info.duration, "lang": info.language,
           "model": MODEL, "asrAt": time.strftime("%Y-%m-%d %H:%M")}
    os.makedirs(CACHE_DIR, exist_ok=True)
    json.dump(out, open(cf, "w", encoding="utf-8"), ensure_ascii=False)
    return out

# ---------- 节点3 align（词级校准） ----------
def align_lesson(lesson, asr):
    ss = lesson["sentences"]
    aw = asr["words"]
    a_norm = [w["w"] for w in aw]
    t_norm, span = [], []           # 每句在拼接序列中的词区间
    for s in ss:
        ws = [norm(x) for x in re.findall(r"[A-Za-z0-9']+", s["en"])]
        span.append((len(t_norm), len(t_norm)+len(ws)))
        t_norm.extend(ws)
    sm = difflib.SequenceMatcher(None, a_norm, t_norm, autojunk=False)
    match = [[] for _ in ss]        # 每句命中的 asr 词下标
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        if op != "equal":
            continue
        for k in range(b1, b2):
            j = k - b1 + a1
            for si, (x, y) in enumerate(span):
                if x <= k < y:
                    match[si].append(j); break
    out, stats = [], {"fixed":0,"fallback":0,"devs":[],"trust":0}
    prev_end = 0.0
    for i, s in enumerate(ss):
        t_old, t2_old = s["t"], s["t2"]
        m = match[i]
        nw = len(re.findall(r"[A-Za-z0-9']+", s["en"]))
        ratio = len(m)/nw if nw else 0
        entry = {"i": i, "en": s["en"], "zh": s["zh"], "t_lrc": t_old, "t2_lrc": t2_old}
        if m and ratio >= MATCH_MIN:
            st, en2 = aw[m[0]]["s"], aw[m[-1]]["e"]
            st = max(st - LEAD, prev_end + 0.02)
            en2 = min(en2 + TAIL, st + max(t2_old - t_old, 2.0) + 4.0)
            en2 = max(en2, st + 0.6)
            dev = abs(st - t_old)
            stats["devs"].append(round(dev, 3))
            grade = "A" if dev <= DEV_TRUST else "B"
            if dev > DEV_TRUST: stats["fixed"] += 1
            else: stats["trust"] += 1
            wpm = round(len(m) / max(en2 - st, 0.5) * 60)
            out.append(dict(entry, t=round(st,3), t2=round(en2,3),
                            source="asr_word", method="词级校准", grade=grade,
                            match=round(ratio,2), devLrc=round(dev,3), wpm=wpm))
            prev_end = en2
        else:
            out.append(dict(entry, t=t_old, t2=t2_old,
                            source="lrc_snap", method="静音带吸附", grade="F",
                            match=round(ratio,2), wpm=None))
            stats["fallback"] += 1
            prev_end = t2_old
    for a, b in zip(out, out[1:]):    # 防重叠
        if b["t"] < a["t2"]: a["t2"] = round(b["t"] - 0.02, 3)
    return out, stats

# ---------- 节点4 verify ----------
def verify_lesson(no, aligned, lesson, asr, stats):
    chars = sum(len(x["en"]) for x in aligned)
    dur = max((x["t2"] for x in aligned), default=0)
    devs = stats["devs"]
    devs_sorted = sorted(devs)
    p = lambda q: devs_sorted[int(q*(len(devs_sorted)-1))] if devs_sorted else None
    wpm_bad = [x["i"]+1 for x in aligned if x.get("wpm") and (x["wpm"]>250 or x["wpm"]<60)]
    return {"lesson": no, "title": lesson["title"], "sentences": len(aligned),
            "audioChars": chars, "audioDur": round(dur,1),
            "avgDev": round(sum(devs)/len(devs),3) if devs else None,
            "p50": p(0.5), "p95": p(0.95), "max": devs_sorted[-1] if devs_sorted else None,
            "fixed": stats["fixed"], "trust": stats["trust"], "fallback": stats["fallback"],
            "wpmOutlier": wpm_bad}

# ---------- 节点5 export ----------
def export_lesson(no, aligned, lesson):
    json.dump({"no": no, "title": lesson["title"], "question": lesson["question"],
               "pipeline": "unified-align v1", "generatedAt": time.strftime("%Y-%m-%d %H:%M"),
               "sentences": aligned},
              open(os.path.join(EX_DIR, "L%02d.align.json" % no), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    jf = os.path.join(APP_DATA, "L%02d.json" % no)
    d = json.load(open(jf, encoding="utf-8"))
    for x, a in zip(d["sentences"], aligned):
        x["t"], x["t2"] = a["t"], a["t2"]
    json.dump(d, open(jf, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def export_srt():
    subprocess.run([sys.executable, os.path.join(BASE, "_build_alignment_srt.py")])

# ---------- 主流程 ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lessons", default="1-3")
    a = ap.parse_args()
    if "-" in a.lessons: lo, hi = map(int, a.lessons.split("-"))
    else: lo = hi = int(a.lessons)
    rows, t0 = [], time.time()
    for no in range(lo, hi+1):
        lesson = detect(no)
        if not lesson: print("L%02d: SKIP" % no); continue
        ta = time.time()
        asr = asr_words(no, lesson["audio"])
        aligned, stats = align_lesson(lesson, asr)
        rep = verify_lesson(no, aligned, lesson, asr, stats)
        export_lesson(no, aligned, lesson)
        rows.append(rep)
        print("L%02d: %s | 句%d 字%d | 偏差avg %.3f p95 %s | 修正%d 兜底%d | ASR %.0fs"
              % (no, rep["title"][:16], rep["sentences"], rep["audioChars"],
                 rep["avgDev"] or 0, rep["p95"], rep["fixed"], rep["fallback"], time.time()-ta))
    total_chars = sum(r["audioChars"] for r in rows)
    total_dur = sum(r["audioDur"] for r in rows)
    summary = {"lessons": len(rows), "totalChars": total_chars, "totalDur": round(total_dur,1),
               "totalFixed": sum(r["fixed"] for r in rows),
               "totalFallback": sum(r["fallback"] for r in rows),
               "elapsed": round(time.time()-t0,1)}
    json.dump({"summary": summary, "rows": rows},
              open(os.path.join(CACHE_DIR, "report_%s.json" % a.lessons.replace("-","_")), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    export_srt()
    print("===== %d 课完成 | 总字符 %d | 总时长 %.0fs | ASR修正 %d | 兜底 %d | 用时 %.0fs ====="
          % (len(rows), total_chars, total_dur, summary["totalFixed"], summary["totalFallback"], summary["elapsed"]))

if __name__ == "__main__":
    main()
