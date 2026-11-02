# -*- coding: utf-8 -*-
"""P2-A：96 课音频句尾边界批量审计
管线（L1 已验证）：ffmpeg silencedetect 全量静音带 → 句尾 t2 落带检查 → 吸附（只提前不延后）
规则：
  - 覆盖带：new = clamp(e-0.2, a+0.1, b)（留在带内、带端-0.2s 防 next 起音泄漏）
  - 越界（无带覆盖）：回拉到 b 之前最后一个静音带 e-0.2
  - 末句：不超过 音频长-0.3；若有尾部静音带取 e-0.2
  - 兜底：new >= t+0.5（防塌缩）、new <= 下一句起点
幂等：已吸附的边界重跑无变化。产物：仅改 data/L{NN}.json 的 t2 字段。
"""
import json, re, subprocess, sys, os

FF = r"C:/Users/Thinkpad/.workbuddy/binaries/python/envs/default/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"
DATA = "nce2-echoloop/data"
AUDIO = "nce2-echoloop/audio"
NOISE, D = "-42dB", 0.15

def silences(mp3):
    r = subprocess.run([FF, "-hide_banner", "-i", mp3,
                        "-af", f"silencedetect=noise={NOISE}:d={D}", "-f", "null", "-"],
                       capture_output=True, text=True)
    ivs, cur = [], None
    for l in r.stderr.splitlines():
        m = re.search(r"silence_(start|end): ([\d.]+)", l)
        if m:
            t, v = m.group(1), float(m.group(2))
            if t == "start":
                cur = v
            elif cur is not None:
                ivs.append((cur, v)); cur = None
    return ivs

def duration(mp3):
    r = subprocess.run([FF, "-hide_banner", "-i", mp3, "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    return int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3)) if m else None


def audit_lesson(no):
    jf = f"{DATA}/L{no:02d}.json"
    mp3 = f"{AUDIO}/L{no:02d}.mp3"
    if not os.path.exists(jf) or not os.path.exists(mp3):
        return None
    d = json.load(open(jf, encoding="utf-8"))
    ss = d.get("sentences") or []
    if len(ss) < 2:
        return None
    D = duration(mp3)
    if not D:
        return None
    ivs = silences(mp3)
    changed = 0
    for i, sn in enumerate(ss):
        b = sn["t2"]
        t = sn["t"]
        if i == len(ss) - 1:
            new = min(b, D - 0.3)
            for (a, e) in reversed(ivs):
                if e >= D - 0.5:
                    new = min(new, e - 0.2)
                    break
        else:
            nxt = ss[i+1]["t"]
            hit = None
            for (a, e) in ivs:
                if a - 0.05 <= b <= e:
                    hit = (a, e); break
            if hit:
                new = min(max(hit[1] - 0.2, hit[0] + 0.1), b)
            else:
                prev = [(a, e) for (a, e) in ivs if e <= b + 0.05]
                if prev:
                    a, e = prev[-1]
                    new = min(max(e - 0.2, a + 0.1), b)
                else:
                    new = b
            new = min(new, nxt)
        new = max(new, t + 0.5)
        if abs(new - b) > 0.01:
            sn["t2"] = round(new, 2)
            changed += 1
    if changed:
        json.dump(d, open(jf, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return changed, len(ss), D

total_lessons = total_changed = 0
rows = []
for no in range(1, 97):
    r = audit_lesson(no)
    if r is None:
        rows.append((no, "SKIP"))
        continue
    ch, n, D = r
    total_lessons += 1
    total_changed += ch
    rows.append((no, f"{ch}/{n} 句修正 · 音长{D:.1f}s"))
    print(f"L{no:02d}: {ch}/{n} 处修正")
print(f"\n===== 完成 {total_lessons} 课，共修正 {total_changed} 处句尾 =====")
