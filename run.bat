@echo off
chcp 65001 >nul
title YouTube Downloader Web App

echo ======================================================
echo    正在啟動 YouTube Downloader 本地伺服器...
echo ======================================================

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

pause
