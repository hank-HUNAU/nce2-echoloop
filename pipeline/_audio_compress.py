# -*- coding: utf-8 -*-
"""NCE2 音频瘦身：128k 立体声+封面 -> 64k 单声道无封面，并校验时长漂移。"""
import os, re, subprocess, sys

FF = r"C:\Users\Thinkpad\.workbuddy\binaries\python\envs\default\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
SRC = r"E:\04 少儿原版课程\06 新概念英语\nce2-echoloop\audio"
DST = r"E:\04 少儿原版课程\06 新概念英语\audio_压缩"

def dur(path):
    r = subprocess.run([FF, "-hide_banner", "-i", path], capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    return round(int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3)), 3) if m else None

os.makedirs(DST, exist_ok=True)
files = sorted(f for f in os.listdir(SRC) if f.endswith(".mp3"))
print(f"{len(files)} 个文件")
rows, total_old, total_new, max_drift = [], 0, 0, 0.0
for i, f in enumerate(files, 1):
    s = os.path.join(SRC, f); d = os.path.join(DST, f)
    d0 = dur(s)
    if os.path.exists(d) and os.path.getsize(d) > 10000:  # 断点续跑：已存在则跳过
        d1 = dur(d)
        drift = abs(d1 - d0); max_drift = max(max_drift, drift)
        so, sn = os.path.getsize(s), os.path.getsize(d)
        total_old += so; total_new += sn
        rows.append((f, d0, d1, drift, so, sn))
        continue
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", s,
                    "-vn", "-ac", "1", "-ar", "44100", "-b:a", "64k",
                    "-codec:a", "libmp3lame", d], check=True)
    d1 = dur(d)
    drift = abs(d1 - d0)
    max_drift = max(max_drift, drift)
    so, sn = os.path.getsize(s), os.path.getsize(d)
    total_old += so; total_new += sn
    rows.append((f, d0, d1, drift, so, sn))
    if i % 16 == 0: print(f"  {i}/{len(files)}")

print(f"\n总体积: {total_old/1048576:.1f}MB -> {total_new/1048576:.1f}MB (压缩率 {100-100*total_new/total_old:.1f}%)")
print(f"最大时长漂移: {max_drift*1000:.0f}ms")
bad = [r for r in rows if r[3] > 0.15]
print("漂移>150ms:", bad if bad else "无")
# 写明细
with open(r"E:\04 少儿原版课程\06 新概念英语\_audio_compress_log.csv", "w", encoding="utf-8-sig") as fp:
    fp.write("file,dur_old,dur_new,drift_s,size_old,size_new\n")
    for f, d0, d1, dr, so, sn in rows:
        fp.write(f"{f},{d0},{d1},{dr},{so},{sn}\n")
print("明细: _audio_compress_log.csv")
