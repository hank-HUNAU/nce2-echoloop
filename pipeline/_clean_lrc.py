# -*- coding: utf-8 -*-
"""清洗 NCE2 LRC：删除全部 [by:...] 行，保留 [al]/[ar]/[ti] 与时间轴。
- 先整目录备份到 _lrc_原始备份/
- 原地改写（UTF-8，保持原有换行与行尾）
"""
import os, re, shutil, datetime

SRC = r"E:\04 少儿原版课程\06 新概念英语\NCE2-英音"
BAK = r"E:\04 少儿原版课程\06 新概念英语\_lrc_原始备份"
BY_RE = re.compile(r"^\s*\[by:.*\]\s*$", re.I)

os.makedirs(BAK, exist_ok=True)
changed, skipped, removed_lines = [], [], 0

for name in sorted(os.listdir(SRC)):
    if not name.lower().endswith(".lrc"):
        continue
    src = os.path.join(SRC, name)
    raw = open(src, "rb").read()
    text = raw.decode("utf-8")

    # 备份原始
    bak_path = os.path.join(BAK, name)
    if not os.path.exists(bak_path):
        shutil.copy2(src, bak_path)

    lines = text.split("\n")
    kept = [ln for ln in lines if not BY_RE.match(ln)]
    diff = len(lines) - len(kept)
    if diff == 0:
        skipped.append(name)
        continue

    out = "\n".join(kept)
    open(src, "w", encoding="utf-8", newline="").write(out)
    changed.append((name, diff))
    removed_lines += diff

print("已修改文件数:", len(changed), "| 无 by 行未动:", len(skipped))
print("删除 by 行总数:", removed_lines)
print("备份目录:", BAK, "文件数:", len(os.listdir(BAK)))
print("未修改的:", skipped)

# 复核
left = 0
for name in sorted(os.listdir(SRC)):
    if name.lower().endswith(".lrc"):
        t = open(os.path.join(SRC, name), encoding="utf-8").read()
        if "[by:" in t or "[BY:" in t:
            left += 1
print("复核残留 by 的文件数:", left)
