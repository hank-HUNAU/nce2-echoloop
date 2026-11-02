# Android SDK 命令行工具自动安装（Windows · 无需 Android Studio）
# 用法：右键"使用 PowerShell 运行"，或 powershell -ExecutionPolicy Bypass -File setup-sdk.ps1
$ErrorActionPreference = 'Stop'
$SdkHome = 'C:\Android'
New-Item -ItemType Directory -Force "$SdkHome\cmdline-tools" | Out-Null

Write-Host '[1/4] 下载 commandline-tools（约 130MB，dl.google.com 国内可直连）...'
$zip = "$env:TEMP\cmdtools.zip"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest 'https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip' -OutFile $zip

Write-Host '[2/4] 解压到 C:\Android\cmdline-tools\latest...'
Expand-Archive $zip -DestinationPath "$SdkHome\cmdline-tools" -Force
if (Test-Path "$SdkHome\cmdline-tools\latest") { Remove-Item "$SdkHome\cmdline-tools\latest" -Recurse -Force }
Rename-Item "$SdkHome\cmdline-tools\cmdline-tools" 'latest'

Write-Host '[3/4] 写入 ANDROID_HOME 用户环境变量...'
[Environment]::SetEnvironmentVariable('ANDROID_HOME', $SdkHome, 'User')
[Environment]::SetEnvironmentVariable('Path', $env:Path + ";$SdkHome\cmdline-tools\latest\bin;$SdkHome\platform-tools", 'User')

Write-Host '[4/4] 安装组件（platform-tools + platform 34 + build-tools 34，许可自动确认）...'
$sdkmgr = "$SdkHome\cmdline-tools\latest\bin\sdkmanager.bat"
$yes = ('y' + "`n") * 20
$yes | & $sdkmgr --licenses
& $sdkmgr 'platform-tools' 'platforms;android-34' 'build-tools;34.0.0'

Write-Host '完成！重新打开终端后，按 nce2-echoloop/android-build/README_构建说明.md 的四条命令构建 APK。'
