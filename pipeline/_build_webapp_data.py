# -*- coding: utf-8 -*-
"""NCE2 → nce2-echoloop 仓库数据生成器

输出：
  nce2-echoloop/data/L01.json .. L96.json   逐课载荷（时间轴/译文/语块/语法点）
  nce2-echoloop/audio/L01.mp3  .. L96.mp3   音频（复制并改 ASCII 名，避免 URL 编码问题）

载荷 schema：
{ no,title,titleZh,audio,duration,question:{en,zh},
  sentences:[{i,t,t2,en,zh,meta?,pat,patZh,gp:[..],chunks:[{c,x,g}]}] }
"""
import os, json, shutil, collections

BASE = r"E:\04 少儿原版课程\06 新概念英语"
DATA = os.path.join(BASE, "data")
ANNO = os.path.join(BASE, "标注数据库")
AUDIO = os.path.join(BASE, "NCE2-英音")
REPO = os.path.join(BASE, "nce2-echoloop")

MAX_CHUNKS = 4          # 每句语块上限
MIN_CHUNK_LEN = 2       # 最短语块词数
CHUNK_ORDER = {"VP": 0, "PP": 1, "SBAR": 2, "ADJP": 3, "ADVP": 4, "NP": 5}


def load_csv(name):
    import csv
    with open(os.path.join(ANNO, name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    os.makedirs(os.path.join(REPO, "data"), exist_ok=True)
    os.makedirs(os.path.join(REPO, "audio"), exist_ok=True)
    lessons = json.load(open(os.path.join(DATA, "nce2_lessons.json"), encoding="utf-8"))["lessons"]
    zhs = {l["no"]: l for l in json.load(open(os.path.join(DATA, "nce2_zh.json"), encoding="utf-8"))["lessons"]}

    # 语块按 (lesson, sentId) 分组
    chunks_by = collections.defaultdict(list)
    for r in load_csv("NCE2_语块标注.csv"):
        if int(r["length"]) >= MIN_CHUNK_LEN:
            chunks_by[(int(r["lesson"]), int(r["sentId"]))].append(r)

    # 句型/语法点按 (lesson, sentId)
    pat_by = {}
    for r in load_csv("NCE2_句型标注.csv"):
        key = (int(r["lesson"]), int(r["sentId"]))
        gps = [g for g in (r.get("grammarPointsZh") or "").split("；") if g][:3]
        pat_by[key] = (r.get("patternZh") or "", gps)

    n_ok = 0
    for les in lessons:
        no = les["no"]
        body_start = 3 if les.get("instruction") else 1
        zl = zhs.get(no, {})
        zmap = {int(x["i"]): x.get("zh", "") for x in zl.get("lines", [])}
        lines = les["lines"]
        sents = []
        for i, ln in enumerate(lines):
            t = float(ln.get("t") or 0)
            nxt = lines[i + 1] if i + 1 < len(lines) else None
            t2 = float(nxt["t"]) if nxt and nxt.get("t") else t + 10.0
            if t2 <= t:
                t2 = t + 3.0
            en = (ln.get("text") or "").strip()
            if not en:
                continue
            item = {"i": i, "t": round(t, 2), "t2": round(t2, 2), "en": en, "zh": ""}
            if i < body_start:
                item["meta"] = True
                if i == body_start - 1:
                    item["zh"] = zl.get("questionZh", "")
            else:
                item["zh"] = zmap.get(i - body_start, "")
            cs = chunks_by.get((no, i - body_start if i >= body_start else -1), [])
            cs = sorted(cs, key=lambda r: (CHUNK_ORDER.get(r["chunkType"], 9), -int(r["length"])))[:MAX_CHUNKS]
            if cs:
                item["chunks"] = [{"c": r["chunkType"], "x": r["text"], "g": r.get("teachTag", "")} for r in cs]
            pt = pat_by.get((no, i - body_start if i >= body_start else -1))
            if pt and (pt[0] or pt[1]):
                item["pat"], item["gp"] = pt[0], pt[1]
            sents.append(item)

        payload = {
            "no": no, "title": les["title"], "titleZh": zl.get("titleZh", ""),
            "audio": "audio/L%02d.mp3" % no, "duration": les.get("durationSecEst") or 0,
            "question": {"en": les.get("question") or (lines[0]["text"] if lines else ""),
                         "zh": zl.get("questionZh", "")},
            "sentences": sents,
        }
        with open(os.path.join(REPO, "data", "L%02d.json" % no), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

        src = os.path.join(AUDIO, les["audio"])
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(REPO, "audio", "L%02d.mp3" % no))
            n_ok += 1
        else:
            print("!! 缺音频:", les["audio"])

    total = sum(os.path.getsize(os.path.join(REPO, "data", f)) for f in os.listdir(os.path.join(REPO, "data"))) / 1048576
    print("data/L01..L96.json (%.1f MB) + audio %d 个 -> %s" % (total, n_ok, REPO))


if __name__ == "__main__":
    main()
