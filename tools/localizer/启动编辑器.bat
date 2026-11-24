@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动 RyonaRPG 本地化编辑器...
echo 浏览器打开 http://127.0.0.1:5010/
python app.py
pause
