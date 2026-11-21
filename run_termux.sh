#!/data/data/com.termux/files/usr/bin/bash

# 防止手機待機時進程被 Android 系統睡眠
if command -v termux-wake-lock >/dev/null 2>&1; then
    termux-wake-lock
fi

echo "================================================================="
echo "  ⚡ YouTube 萬能下載站 (Android 極速秒級啟動模式)"
echo "================================================================="

# 智慧檢測：只有缺少套件才進行安裝，避免每次浪費數分鐘重複更新
NEED_PKG=0
for pkg in python ffmpeg git cloudflared; do
    if ! command -v "$pkg" >/dev/null 2>&1; then
        NEED_PKG=1
        break
    fi
done

if [ "$NEED_PKG" -eq 1 ]; then
    echo "[⚡] 首次設定：正在快速安裝底層核心 (Python, FFmpeg, Cloudflared)..."
    pkg install -y python ffmpeg git cloudflared termux-tools
fi

REPO_DIR="$HOME/yt-downloader"

if [ ! -d "$REPO_DIR" ]; then
    echo "[⚡] 正在下載專案程式庫..."
    git clone https://mini548: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@github.com/mini548/yt-downloader.git "$REPO_DIR"
else
    cd "$REPO_DIR"
    # 背景安靜檢查更新，不卡住啟動流程
    git pull -q 2>/dev/null &
fi

cd "$REPO_DIR"

# 智慧檢測 Python 依賴：只有首次才安裝
if ! python -c "import fastapi, uvicorn, yt_dlp" >/dev/null 2>&1; then
    echo "[⚡] 首次設定：正在配置 Python 模組..."
    pip install fastapi uvicorn yt-dlp --no-warn-script-location -q
fi

echo "[🚀] 環境就緒！立即啟動後端與 Cloudflare 全球穿透..."
python run_mobile.py
