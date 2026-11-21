# YouTube Downloader Web App 🚀

這是一個全功能、現代化的 YouTube 影片與 MP3 下載網站專案。支援 4K / 1080p Full HD 高畫質影片、320kbps MP3 轉換、中英雙語切換與手機/平板自適應排版。

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
├── run.bat                # Windows 一鍵啟動腳本
├── run.sh                 # Linux / Mac 啟動腳本
└── README.md              # 部署與使用說明文件
```

---

## ⚡ 本地快速啟動（Windows）

1. **直接雙擊執行 `run.bat`**，或在終端機執行：
   ```bash
   cd C:\Users\方家\.gemini\antigravity\scratch\yt-downloader
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
2. 開啟瀏覽器訪問：
   👉 **http://127.0.0.1:8000**
3. 貼上任意 YouTube 網址，即可解析與下載！

---

## 🌐 如何部署到雲端，讓「全世界人都看的到」？

要讓全球使用者連上你的網站，你需要將此專案部署到擁有公網 IP 的伺服器，並綁定網域名稱。

### 方案 A：使用 VPS 主機 + Docker（最推薦、穩定）

推薦雲端主機：**Hetzner**（CP值最高）、**DigitalOcean** 或 **AWS Lightsail**（月費約 4~6 美元）。

1. **購買 VPS**（建議選擇 Ubuntu 22.04 / 24.04 LTS）。
2. **安裝 Docker 與 Docker Compose**：
   ```bash
   curl -fsSL https://get.docker.com | sh
   ```
3. **上傳本專案檔案到 VPS**，進入專案目錄：
   ```bash
   docker compose up -d --build
   ```
4. 你的網站即在 `http://你的主機IP:8000` 運行！

---

### 方案 B：綁定專屬網址與免費 SSL 憑證（HTTPS）

全世界人要能方便記住並安全連線，需要網域和 HTTPS：

1. **購買網域**：在 Namecheap、GoDaddy 或 Cloudflare Registrar 購買網域（例如 `myytdownloader.com`，一年約 300~400 台幣）。
2. **透過 Cloudflare 託管（免費方案）**：
   - 將網域 DNS 指向 Cloudflare。
   - 新增 A 紀錄，指向你的 VPS 主機 IP。
   - 開啟橘色雲朵（Proxied），Cloudflare 會自動為你提供免費的 **全球 CDN 加速**、**DDoS 防禦** 以及 **自動 HTTPS 憑證**。

---

## 🛡️ 營運必讀：YouTube 防封鎖策略

當你把網站公開給全球使用者後，流量變大時，YouTube 可能會對機房 IP 限制下載（常見錯誤：`Sign in to confirm you’re not a bot` 或 `403 Forbidden`）。

### 應對方案：
1. **更新 yt-dlp**：
   YouTube 時常更新串流加密演算法，定期在伺服器執行更新：
   ```bash
   pip install --upgrade yt-dlp
   ```
2. **掛載住宅代理（Residential Proxy）**：
   在 `app/downloader.py` 的 `ydl_opts` 加入代理：
   ```python
   ydl_opts['proxy'] = 'http://username:password@proxy-server:port'
   ```
3. **匯入 YouTube 登入 Cookie**：
   使用瀏覽器擴充插件（如 *Get cookies.txt LOCALLY*）匯出 YouTube 的 `cookies.txt`，並在 `downloader.py` 加入：
   ```python
   ydl_opts['cookiefile'] = 'cookies.txt'
   ```
