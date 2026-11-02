# -*- coding: utf-8 -*-
"""NCE2 → Echo Loop 导入包生成器

Echo Loop 只支持 SRT/VTT 字幕（Dart `subtitle` 包），不吃 LRC。
本脚本把 data/nce2_lessons.json 的逐句时间轴 + data/nce2_zh.json 的译文层
转成每课一份双语 SRT（第一行英文 / 第二行中文），连同 MP3 复制进 EchoLoop导入包/。

时间轴规则：start = 该行 t；end = 下一行 t（末行 = t + 10s）。
覆盖全部行（含理解题行 / L8 的标题+指令行），保证字幕与整段音频对齐。
"""
import os, json, shutil

BASE = r"E:\04 少儿原版课程\06 新概念英语"
DATA = os.path.join(BASE, "data")
AUDIO_DIR = os.path.join(BASE, "NCE2-英音")
OUT = os.path.join(BASE, "EchoLoop导入包")
EN_ONLY = os.path.join(OUT, "srt_纯英文备用")


def ts(sec):
    """秒 → SRT 时间 HH:MM:SS,mmm"""
    sec = max(0.0, float(sec))
    h = int(sec // 3600)
    m = int(sec % 3600 // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    if ms == 1000:
        s += 1; ms = 0
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


def build_srt(lines, zhs, question_zh):
    """lines: nce2_lessons.json 的 lines（全部行）；zhs: body 句中文 {i: zh}"""
    blocks = []
    for i, ln in enumerate(lines):
        start = float(ln.get("t") or 0)
        end = float(lines[i + 1]["t"]) if i + 1 < len(lines) and lines[i + 1].get("t") else start + 10.0
        if end <= start:
            end = start + 3.0
        en = (ln.get("text") or "").strip()
        if not en:
            continue
        # 中文：正文行取 zhs[i - body_offset]，非正文行（问题/标题/指令）留空
        zh = ""
        if i == 0 and question_zh:
            zh = question_zh  # lines[0] 约定为理解题行（L8 为标题行则无译文，正常）
        else:
            # body 从 index 1（无 instruction）或 3（有 instruction）开始
            pass
        blocks.append({"start": start, "end": end, "en": en, "zh": zh})
    # 重新按 body 对齐填中文（避开 L8 特例）
    return blocks


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(EN_ONLY, exist_ok=True)
    lessons = json.load(open(os.path.join(DATA, "nce2_lessons.json"), encoding="utf-8"))["lessons"]
    zhs_map = {l["no"]: l for l in json.load(open(os.path.join(DATA, "nce2_zh.json"), encoding="utf-8"))["lessons"]}

    n_srt = n_mp3 = 0
    for les in lessons:
        no = les["no"]
        audio_name = les["audio"]                       # 如 01－A Private Conversation.mp3
        srt_name = os.path.splitext(audio_name)[0] + ".srt"
        body_start = 3 if les.get("instruction") else 1
        zl = zhs_map.get(no, {})
        zhs = {int(x["i"]): x.get("zh", "") for x in zl.get("lines", [])}
        question_zh = zl.get("questionZh", "")

        blocks = []
        for i, ln in enumerate(les["lines"]):
            start = float(ln.get("t") or 0)
            nxt = les["lines"][i + 1] if i + 1 < len(les["lines"]) else None
            end = float(nxt["t"]) if nxt and nxt.get("t") else start + 10.0
            if end <= start:
                end = start + 3.0
            en = (ln.get("text") or "").strip()
            if not en:
                continue
            if i < body_start:
                zh = question_zh if i == body_start - 1 else ""   # 问题行（L8 为指令行则空）
            else:
                zh = zhs.get(i - body_start, "")
            blocks.append((start, end, en, zh))

        # 写双语 SRT（英文第一行，有译文时中文第二行）
        def render(bilingual):
            out = []
            for n, (s, e, en, zh) in enumerate(blocks, 1):
                txt = en + ("\n" + zh if bilingual and zh else "")
                out.append("%d\n%s --> %s\n%s\n" % (n, ts(s), ts(e), txt))
            return "\n".join(out)

        with open(os.path.join(OUT, srt_name), "w", encoding="utf-8") as f:
            f.write(render(True))
        with open(os.path.join(EN_ONLY, srt_name), "w", encoding="utf-8") as f:
            f.write(render(False))
        n_srt += 1

        # 复制 MP3
        src = os.path.join(AUDIO_DIR, audio_name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(OUT, audio_name))
            n_mp3 += 1
        else:
            print("!! 缺音频:", audio_name)

    print("SRT 双语 %d 份 + 纯英文备用 %d 份 + MP3 %d 个 -> %s" % (n_srt, n_srt, n_mp3, OUT))


if __name__ == "__main__":
    main()
