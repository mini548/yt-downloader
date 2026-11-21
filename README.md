# YouTube Downloader Web App 🚀

這是一個全功能、現代化的 YouTube 影片與 MP3 下載網站專案。支援 4K / 1080p Full HD 高畫質影片、320kbps MP3 轉換、中英雙語切換與手機/平板自適應排版。

---

## 🌟 兩種全球公開運作模式

### 模式一：一鍵全球公開發布（⭐ 最推薦、100% 成功、零被擋）
利用本專案內建的 Cloudflare Tunnel 與您本地的家用寬頻原生連線：
1. **直接雙擊執行 `run_global.bat`**。
2. 系統會自動啟動後端伺服器並建立全世界皆可訪問的專屬加密網址（`https://*.trycloudflare.com`）。
3. 任何人在全世界點擊此網址，即可直接下載，**享有家用 IP 原生高速連線，100% 零驗證碼、零機房封鎖！**

### 模式二：Render 雲端容器託管
本專案已完整支援 Docker 容器化部署至 Render 等雲端平台：
- 服務網址：`https://yt-downloader-491k.onrender.com`
- 已預載 FFmpeg、Deno 執行環境與自動訪客憑證機制。
> 💡 註：由於各大雲端平台（如 Render、AWS、GCP）機房 IP 常遭 YouTube 嚴格風控，若在雲端遇到 Bot 驗證，強烈建議使用模式一，或在雲端掛載住宅代理 (Residential Proxy)。

---

## 📁 專案結構

```
yt-downloader/
├── app/
│   ├── main.py            # FastAPI 後端 API (包含解析、下載與暫存自動清理)
│   ├── downloader.py      # yt-dlp 核心引擎與 FFmpeg 整合封裝
│   ├── temp_downloads/    # 暫存下載目錄 (傳送完成後自動刪除)
│   └── static/
│       ├── index.html     # 現代化響應式 UI (支援暗黑主題、雙語切換)
│       ├── app.js         # 前端互動邏輯 (剪貼簿、非同步解析、下載觸發)
│       └── style.css      # 動畫與光暈樣式
├── Dockerfile             # 雲端伺服器生產環境 Docker 映像檔設定
├── docker-compose.yml     # 一鍵容器化部署設定
├── requirements.txt       # Python 依賴清單
├── cloudflared.exe        # Cloudflare 全球穿透工具
├── run_global.bat         # Windows 一鍵啟動全球公開網址
├── run_global.py          # 全球公開連線核心程序
├── run.bat                # Windows 本地啟動腳本
├── run.sh                 # Linux / Mac 啟動腳本
└── README.md              # 部署與使用說明文件
```

---

## ⚡ 本地開發與啟動

在終端機執行：
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
開啟瀏覽器訪問：👉 **http://127.0.0.1:8000**
