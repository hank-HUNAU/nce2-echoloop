# 部署手册（3 条命令上线）

> **状态：已于 2026-10-21 01:46Z 上线完成。** 远程 `main` = `7d06152`（195 文件：应用 + 96 data + 96 audio），Pages 构建 `built`。
> 线上地址：**https://hank-hunau.github.io/nce2-echoloop/**（index.html / data/L01.json / audio/L01.mp3 抽样均 200）。
> 以下内容留作重建或迁移时的操作留档。

本仓库已完成：应用 + 数据 + 全部音频均已本地提交；GitHub 远程仓库已创建（public）。

## 在你自己的终端里执行（无需代理）

```bash
cd "E:\04 少儿原版课程\06 新概念英语\nce2-echoloop"
git push origin main
```

> 若单次推送被中断（172MB 较大），重复执行即可断点续传；或分批：
> ```bash
> git push origin HEAD~2:main && git push origin HEAD~1:main && git push origin HEAD:main
> ```

## 开启 GitHub Pages（二选一）

**网页操作**：仓库页 → Settings → Pages → Source 选 `main` + `/ (root)` → Save

**或命令行**：
```bash
gh api repos/hank-HUNAU/nce2-echoloop/pages -X POST -f "source[branch]=main" -f "source[path]=/"
```

完成后访问：`https://hank-hunau.github.io/nce2-echoloop/`

## 验证清单

- [ ] 首页显示 96 课网格 + 「今天要处理」
- [ ] 进 L01：精听逐句能播（音频 200）、点句子出意群/句型
- [ ] 跟读台：录音 → 回放 → A/B 对比
- [ ] 完成 4 步后首页出现「第 1 轮复习」到期项
- [ ] 手机/平板浏览器打开同一地址，登录 GitHub（私有数据在本地，无需登录也可用）

## 排障

| 症状 | 处理 |
|---|---|
| 音频播不出 | 确认 `audio/` 已推送（`git ls-remote` 后看 Actions/文件树）；本地用 `python -m http.server` 测 |
| 逐句定位不准 | 时间轴来自 LRC 正典；修订后重跑 `_build_webapp_data.py` |
| 换设备丢进度 | 统计页「导出 JSON」→ 新设备「导入恢复」 |
