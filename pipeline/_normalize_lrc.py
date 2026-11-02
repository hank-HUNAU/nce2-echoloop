# -*- coding: utf-8 -*-
"""LRC 规范化：删除全部空行、去掉行尾空白、统一 CRLF→LF、文件末尾恰好 1 个换行。
（[al]/[ar]/[ti] 与时间轴内容一字不动）
"""
import os, re, glob

SRC = r"E:\04 少儿原版课程\06 新概念英语\NCE2-英音"
BAK = r"E:\04 少儿原版课程\06 新概念英语\_lrc_原始备份"

changed = 0
blank_removed = 0
crlf_fixed = 0
ws_fixed = 0

for path in sorted(glob.glob(os.path.join(SRC, "*.lrc"))):
    name = os.path.basename(path)
    raw = open(path, "rb").read()
    orig = raw.decode("utf-8")
    if "\r\n" in orig:
        crlf_fixed += 1
    lines = orig.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    kept = []
    for ln in lines:
        if ln.strip() == "":
            blank_removed += 1
            continue
        if ln != ln.rstrip():
            ws_fixed += 1
            ln = ln.rstrip()
        kept.append(ln)
    new = "\n".join(kept) + "\n"
    bak = os.path.join(BAK, name)
    if not os.path.exists(bak):
        open(bak, "wb").write(raw)
    if new != orig:
        open(path, "w", encoding="utf-8", newline="").write(new)
        changed += 1

print("规范化改动文件数:", changed)
print("移除空行:", blank_removed, "| 行尾空白清理:", ws_fixed, "| CRLF 转 LF:", crlf_fixed)

# 复核
bad = 0
for path in sorted(glob.glob(os.path.join(SRC, "*.lrc"))):
    t = open(path, encoding="utf-8").read()
    if not t.endswith("\n") or t.endswith("\n\n") or any(l.strip() == "" for l in t.split("\n")[:-1]):
        bad += 1
print("复核不合规文件数:", bad)
