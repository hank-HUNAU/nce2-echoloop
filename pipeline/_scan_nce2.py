# -*- coding: utf-8 -*-
"""扫描 NCE2-英音 文件夹：解析 96 篇 LRC → 结构化 JSON（小程序数据底座）
- LRC: [al]/[ar]/[ti]/[by] 元信息 + [mm:ss.xx] 时间轴行
- 第 1 条时间轴行 = 本课 comprehension question（预习问题），其后为正文句子
- MP3 时长：按首个有效帧头比特率估算（CBR 假设），标记 estimated=True
"""
import os, re, json, struct, datetime

SRC = r"E:\04 少儿原版课程\06 新概念英语\NCE2-英音"
OUT_DIR = r"E:\04 少儿原版课程\06 新概念英语\data"
os.makedirs(OUT_DIR, exist_ok=True)

TIME_RE = re.compile(r"\[(\d{2}):(\d{2})\.(\d{2})\](.*)")
META_RE = re.compile(r"^\[(al|ar|ti|by):(.*)\]\s*$")

BITRATES_V1L3 = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
BITRATES_V2L3 = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]
RATES = {0: 44100, 1: 48000, 2: 32000}  # MPEG1
RATES_V2 = {0: 22050, 1: 24000, 2: 16000}  # MPEG2
RATES_V25 = {0: 11025, 1: 12000, 2: 8000}


def read_text(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def mp3_duration_est(path):
    """估算 MP3 时长（秒）：剥离 ID3v2 → 读首个有效帧头比特率 → size*8/bitrate"""
    try:
        data = open(path, "rb").read()
        size = len(data)
        pos = 0
        if data[:3] == b"ID3":
            tag_size = ((data[6] & 0x7F) << 21) | ((data[7] & 0x7F) << 14) | \
                       ((data[8] & 0x7F) << 7) | (data[9] & 0x7F)
            pos = 10 + tag_size
        while pos < size - 4:
            if data[pos] == 0xFF and (data[pos + 1] & 0xE0) == 0xE0:
                b1, b2, b3 = data[pos + 1], data[pos + 2], data[pos + 3]
                ver_bits = (b1 >> 3) & 0x03      # 11=MPEG1, 10=MPEG2, 00=MPEG2.5
                layer = (b1 >> 1) & 0x03         # 01=LayerIII
                br_idx = (b2 >> 4) & 0x0F
                sr_idx = (b2 >> 2) & 0x03
                if layer == 1 and br_idx not in (0, 15):
                    if ver_bits == 3:
                        br, sr = BITRATES_V1L3[br_idx], RATES.get(sr_idx, 44100)
                    elif ver_bits == 2:
                        br, sr = BITRATES_V2L3[br_idx], RATES_V2.get(sr_idx, 22050)
                    else:
                        br, sr = BITRATES_V2L3[br_idx], RATES_V25.get(sr_idx, 11025)
                    return round((size - pos) * 8 / (br * 1000.0), 2), br
            pos += 1
    except Exception:
        pass
    return None, None


def parse_lrc(path):
    meta, lines = {}, []
    for ln in read_text(path).splitlines():
        ln = ln.strip()
        if not ln:
            continue
        m = META_RE.match(ln)
        if m:
            meta[m.group(1)] = m.group(2).strip()
            continue
        m = TIME_RE.match(ln)
        if m:
            mm, ss, cs, txt = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4).strip()
            lines.append({
                "t": round(mm * 60 + ss + cs / 100.0, 2),
                "ts": "%02d:%02d.%02d" % (mm, ss, cs),
                "text": txt,
            })
    return meta, lines


def main():
    lessons = []
    for name in sorted(os.listdir(SRC)):
        if not name.lower().endswith(".lrc"):
            continue
        stem = name[:-4]
        m = re.match(r"^(\d{1,3})－(.+)$", stem)
        no = int(m.group(1)) if m else None
        title_file = m.group(2) if m else stem
        lrc_path = os.path.join(SRC, name)
        mp3_path = os.path.join(SRC, stem + ".mp3")
        meta, lines = parse_lrc(lrc_path)
        # 常规：lines[0] = comprehension question，其后为正文
        # 例外（L8）：lines[0]=标题朗读 / lines[1]=听力指令 / lines[2]=问题 / 其后正文
        prompt = instruction = None
        body_start = 1
        if len(lines) >= 3 and re.match(r"(?i)^first listen", lines[1]["text"]):
            prompt, instruction = lines[0]["text"], lines[1]["text"]
            body_start = 3
        question = lines[body_start - 1]["text"] if lines else ""
        body = lines[body_start:]
        dur, br = mp3_duration_est(mp3_path) if os.path.exists(mp3_path) else (None, None)
        words = sum(len(re.findall(r"[A-Za-z']+", l["text"])) for l in body)
        lessons.append({
            "no": no,
            "title": meta.get("ti") or title_file,
            "titleFile": title_file,
            "audio": stem + ".mp3" if os.path.exists(mp3_path) else None,
            "lrc": name,
            "audioBytes": os.path.getsize(mp3_path) if os.path.exists(mp3_path) else None,
            "durationSecEst": dur,
            "kbpsEst": br,
            "question": question,
            "prompt": prompt,
            "instruction": instruction,
            "sentCount": len(body),
            "wordCount": words,
            "lines": lines,
        })
    lessons.sort(key=lambda x: x["no"] or 999)
    data = {
        "book": "新概念英语（二）",
        "accent": "英音",
        "sourceDir": SRC,
        "generatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "lessonCount": len(lessons),
        "note": "durationSecEst 为按 CBR 首帧比特率估算值（无 ffprobe 环境），非精确时长",
        "lessons": lessons,
    }
    out = os.path.join(OUT_DIR, "nce2_lessons.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    total_dur = sum(l["durationSecEst"] or 0 for l in lessons)
    total_words = sum(l["wordCount"] for l in lessons)
    total_sent = sum(l["sentCount"] for l in lessons)
    total_bytes = sum(l["audioBytes"] or 0 for l in lessons)
    missing_audio = [l["no"] for l in lessons if not l["audio"]]
    no_question = [l["no"] for l in lessons if not l["question"]]
    empty_body = [l["no"] for l in lessons if l["sentCount"] == 0]
    print("课数:", len(lessons))
    print("缺失音频:", missing_audio)
    print("无问题行:", no_question)
    print("无正文:", empty_body)
    print("正文总句数:", total_sent, "总词数:", total_words)
    print("总时长(估): %.1f 秒 = %.1f 分钟 = %.2f 小时" % (total_dur, total_dur / 60, total_dur / 3600))
    print("音频总体积: %.1f MB" % (total_bytes / 1024 / 1024))
    print("JSON:", out, "%.1f KB" % (os.path.getsize(out) / 1024))


if __name__ == "__main__":
    main()
