# -*- coding: utf-8 -*-
"""统一 [ti:] 尾标点：以新概念英语（二）官方书名为准。
- 保留 14 处疑问句 '?'（2/14/21/25/30/39/41/48/57/58/59/78/82/90）
- 补齐官方有 '!' 但 LRC 缺失的 3 课：18 He Often does This! / 29 Taxi! / 66 Sweet as Honey!
- 文件名因 Windows 禁用 ? ! 保持无标点，改由 JSON 的 title / titleFile 双字段区分
"""
import os, re, glob

SRC = r"E:\04 少儿原版课程\06 新概念英语\NCE2-英音"
FIX = {18: "He Often does This!", 29: "Taxi!", 66: "Sweet as Honey!"}

changed = []
for path in sorted(glob.glob(os.path.join(SRC, "*.lrc"))):
    name = os.path.basename(path)
    no = int(re.match(r"^(\d+)", name).group(1))
    if no not in FIX:
        continue
    txt = open(path, encoding="utf-8").read()
    new = re.sub(r"^\[ti:(.*?)\]\s*$", lambda m: "[ti:%s]" % FIX[no], txt, count=1, flags=re.M)
    if new != txt:
        open(path, "w", encoding="utf-8", newline="").write(new)
        changed.append((no, FIX[no]))

print("标题修正:", changed)

# 复核
q = e = 0
for path in sorted(glob.glob(os.path.join(SRC, "*.lrc"))):
    ti = re.search(r"^\[ti:(.*)\]\s*$", open(path, encoding="utf-8").read(), re.M).group(1).strip()
    if ti.endswith("?"):
        q += 1
    elif ti.endswith("!"):
        e += 1
print("复核 → 带 ? 的课:", q, "| 带 ! 的课:", e, "| 合计:", q + e)
