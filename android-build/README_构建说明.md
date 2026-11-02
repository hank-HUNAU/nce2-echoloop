# NCE2 Loop · Capacitor 安卓打包说明（配套训练工具 · 私有分发）

## 前置（本机缺 Android SDK，需一次性安装）
1. JDK 21 ✅（已有）
2. Android Studio（推荐，含 SDK/Gradle）或仅命令行工具：
   - 下载 commandline-tools → sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0"
   - 设 ANDROID_HOME 环境变量
3. Node.js ✅（已有）

## 构建（四条命令）
```bash
cd nce2-echoloop
npm i @capacitor/core @capacitor/cli @capacitor/android
npx cap add android
cd android && ./gradlew assembleDebug
```
产物：`android/app/build/outputs/apk/debug/app-debug.apk`（可直接装学生平板）

## 二维码分发
APK 传到仓库 Release 或直接提交进仓库后，用 GitHub Pages 地址生成二维码：
`python -c "import qrcode;qrcode.make('https://hank-hunau.github.io/nce2-echoloop/app.apk').save('qr-apk.png')"`
（当前 `qr-pwa.png` 已生成，指向 PWA 安装页——苹果端/未装 APK 的安卓端先扫码用网页版）

## 注意
- capacitor.config.json 的 server.url 指向 GitHub Pages：App 本体永远在线加载（离线靠 SW 缓存 + 离线包按钮）
- 版本更新：网页端发布即生效；APK 壳本身极少需要重打
- 若要离线打包全部资产进 APK：把 www 换成本地完整拷贝并去掉 server.url（后续可选）
