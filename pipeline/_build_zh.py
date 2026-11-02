# -*- coding: utf-8 -*-
"""把逐句中文译文并入课文数据，产出 data/nce2_zh.json（中文译文层）。
- 原文来自 data/nce2_lessons.json（唯一英文正典），译文来自 data/_zh_u*_raw.json
- 按 body 句序一一对应，条数不符即报错（防错位）
"""
import json, os, datetime, glob, sys

BASE = r"E:\04 少儿原版课程\06 新概念英语\data"
lessons = json.load(open(os.path.join(BASE, "nce2_lessons.json"), encoding="utf-8"))["lessons"]
by_no = {l["no"]: l for l in lessons}

zh_raw = {}
for p in sorted(glob.glob(os.path.join(BASE, "_zh_u*_raw.json"))):
    zh_raw.update(json.load(open(p, encoding="utf-8")))

out, errs = [], []
for k in sorted(zh_raw, key=lambda x: int(x)):
    no = int(k)
    src, zh = by_no[no], zh_raw[k]
    body = src["lines"][1:] if src.get("instruction") is None else src["lines"][3:]
    if len(body) != len(zh["lines"]):
        errs.append("L%d 句数不符：英文 %d / 译文 %d" % (no, len(body), len(zh["lines"])))
        continue
    out.append({
        "no": no,
        "unit": (no - 1) // 24 + 1,
        "title": src["title"],
        "titleZh": zh["titleZh"],
        "question": src["question"],
        "questionZh": zh["questionZh"],
        "lines": [
            {"i": i, "t": b["t"], "ts": b["ts"], "text": b["text"], "zh": t}
            for i, (b, t) in enumerate(zip(body, zh["lines"]))
        ],
    })

if errs:
    print("!! 校验失败："); [print("  ", e) for e in errs]; sys.exit(1)

data = {
    "book": "新概念英语（二）",
    "layer": "中文译文（逐句）",
    "accent": "英音",
    "source": "data/nce2_lessons.json（英文正典） + data/_zh_u*_raw.json（译文源）",
    "scope": "全书 Unit 1–4（第 1-96 课）：Unit 1（1-24）试点 + Unit 2（25-48）+ Unit 3（49-72）+ Unit 4（73-96）",
    "granularity": "逐句（含标题译文 + 问题译文）",
    "generatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "lessonCount": len(out),
    "sentenceCount": sum(len(l["lines"]) for l in out),
    "lessons": out,
}
path = os.path.join(BASE, "nce2_zh.json")
json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("并入课数:", len(out), "| 句数:", data["sentenceCount"], "| 输出:", path,
      "%.1f KB" % (os.path.getsize(path) / 1024))
