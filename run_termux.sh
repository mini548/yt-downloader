#!/data/data/com.termux/files/usr/bin/bash

# 防止手機待機時進程被 Android 系統終眠
if command -v termux-wake-lock >/dev/null 2>&1; then
    termux-wake-lock
fi

echo "================================================================="
echo "  🚀 YouTube 萬能下載站 (Android 手機一鍵全球公開部署)"
echo "================================================================="

echo "[1/4] 正在檢查並更新系統套件 (Python, FFmpeg, Git, Cloudflared)..."
pkg update -y
pkg install -y python ffmpeg git cloudflared termux-tools

REPO_DIR="$HOME/yt-downloader"

if [ ! -d "$REPO_DIR" ]; then
    echo "[2/4] 正在下載下載站原始碼..."
    git clone https://github.com/mini548/yt-downloader.git "$REPO_DIR"
else
    echo "[2/4] 正在同步最新版本代碼..."
    cd "$REPO_DIR" && git pull
fi

cd "$REPO_DIR"

echo "[3/4] 正在配置 Python 依賴環境..."
pip install --upgrade pip
pip install fastapi uvicorn yt-dlp

echo "[4/4] 正在啟動服務並建立 Cloudflare 全球穿透通道..."
python run_mobile.py
