# NCE2 Loop · 新概念英语（二）听说训练 Web App

Echo Loop 方法论的 Web 复刻（自研实现，未使用其源码），跑在自己的 NCE2 音频数据上。  
纯前端单文件应用，无构建步骤、无外部依赖，GitHub Pages 直接托管。

## 训练闭环

**盲听 → 跟读 → 精听 → 复述 → 间隔复习（7 轮：6小时 → 1天 → 2天 → 4天 → 7天 → 14天 → 28天）**

> 顺序依据（2026-10-22 定）：整体理解先行 + 语音感知 + 语言聚焦 + 输出，对应 Vandergrift 元认知听力序列与 Nation 四线框架；盲听台内置听前预测问题（听前支撑）。
- 盲听：整段播放（先读本课问题做预测），字幕模糊遮罩

- 精听：逐句播放 + 意群/句型/语法点提示 + 难句收藏
- 跟读：录音 → 原声/录音 A/B 对比 → 循环 ×1/×3/×5 计数 → 自评星级；Chrome 环境可用「识别评分」（Web Speech API 词命中评级），不支持的平台优雅降级为自评
- 盲听：整段播放，字幕模糊遮罩
- 复述：录音 + 结构自检三问
- 复习：App 自动排程，首页「今天要处理」出队列；难句专项补练
- 闪卡：难句自动生成（正面中文回忆 / 背面原句 + 语境重听）
- 统计：已学/通关/复习完成度环图 + 近 7 天练习柱图 + 收听时长
- 断点续学 + 数据导出/导入（localStorage + IndexedDB 录音）

## 目录

```
index.html        应用（全部内联）
data/L01..96.json 逐课载荷（时间轴/译文/意群语块/句型语法点）
audio/L01..96.mp3 音频
```

## 部署（GitHub Pages）

1. Push 本仓库到 GitHub
2. Settings → Pages → Source: `main` 分支 `/ (root)`
3. 打开 `https://<user>.github.io/nce2-echoloop/`

本地预览：`python -m http.server` 后访问 localhost（音频需 HTTP 服务，file:// 下 fetch 受限）。

## 数据来源与再生成

- 英文/时间轴：`nce2_lessons.json`（LRC 清洗正典）
- 译文：`nce2_zh.json`（全书 1289 句）
- 意群语块/句型语法点：spaCy 三层标注数据库（`_grammar_annotate.py`）
- 再生成：`python ../_build_webapp_data.py`（在上级项目目录）

## 版权说明

代码 MIT。`audio/` 内音频为新概念英语（二）配套录音，仅限个人学习使用，请勿商用或再分发。
