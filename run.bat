@echo off
chcp 65001 >nul
cd /d %~dp0
echo [run] 启动 Flask 服务...
python app.py
pause
