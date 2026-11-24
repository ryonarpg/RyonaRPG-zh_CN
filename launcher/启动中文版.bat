@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "EasyRPG Player.exe" (
  echo 请把本压缩包解压到 RyonaRPG 游戏根目录，并确认 EasyRPG Player.exe 存在。
  pause
  exit /b 1
)
start "" "EasyRPG Player.exe" --language zh_CN
