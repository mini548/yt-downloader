@echo off
chcp 65001 >nul
title YouTube 全球下載站啟動器
cd /d "%~dp0"
echo 正在啟動 YouTube 全球下載站，請稍候...
python run_global.py
pause
