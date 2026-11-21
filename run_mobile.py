import os
import sys
import time
import subprocess
import re
import shutil
import signal
import urllib.request

def log(msg="", **kwargs):
    print(msg, flush=True, **kwargs)

BANNER = """
=================================================================================
  🚀 YouTube 萬能下載站 (Android 手機 全球公開模式)
=================================================================================
"""

def check_dependencies():
    required = ["fastapi", "uvicorn", "yt-dlp"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            missing.append(pkg)
    if missing:
        log(f"[安裝中] 正在安裝必要套件: {', '.join(missing)}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
        log("[完成] 必要套件安裝完畢！\n")

def get_cloudflared_path():
    # 優先尋找系統 PATH 中的 cloudflared (例如由 pkg install cloudflared 安裝)
    which_cf = shutil.which("cloudflared")
    if which_cf:
        return which_cf

    base_dir = os.path.dirname(os.path.abspath(__file__))
    local_cf = os.path.join(base_dir, "cloudflared")
    if os.path.exists(local_cf):
        return local_cf

    log("[下載中] 正在下載適用於 Android (Linux ARM64) 的 Cloudflare 全球穿透工具...")
    cf_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
    try:
        urllib.request.urlretrieve(cf_url, local_cf)
        os.chmod(local_cf, 0o755)
        log("[完成] cloudflared 下載並授權成功！")
        return local_cf
    except Exception as e:
        log(f"[警告] 下載 cloudflared 失敗: {e}，請嘗試在 Termux 執行: pkg install cloudflared")
        return None

def main():
    log(BANNER)
    check_dependencies()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    cf_bin = get_cloudflared_path()

    log("步驟 1/3: 正在啟動手機端後端下載伺服器 (FastAPI / Uvicorn)...")
    server_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "warning"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # 等待本地伺服器就緒
    server_ready = False
    for _ in range(30):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=1) as resp:
                if resp.status == 200:
                    server_ready = True
                    break
        except Exception:
            time.sleep(0.5)

    if not server_ready:
        log("[錯誤] 本地伺服器啟動超時，請檢查端口 8000 是否被佔用。")
        server_proc.terminate()
        return

    log("步驟 2/3: 手機本機伺服器已就緒 (http://127.0.0.1:8000)！")

    tunnel_proc = None
    public_url = None

    if cf_bin:
        log("步驟 3/3: 正在連接 Cloudflare 全球高速網路，建立全球公開 HTTPS 網址...")
        tunnel_proc = subprocess.Popen(
            [cf_bin, "tunnel", "--url", "http://127.0.0.1:8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
            bufsize=1
        )

        start_time = time.time()
        while True:
            line = tunnel_proc.stdout.readline()
            if not line and tunnel_proc.poll() is not None:
                break
            match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
            if match:
                public_url = match.group(0)
                break
            if time.time() - start_time > 35:
                break

    log("\n" + "=" * 80)
    log("  🎉 手機端 YouTube 下載服務啟動成功！")
    log("=" * 80)
    if public_url:
        log(f"\n  🌐 全球公開網址 (全世界皆可開):  {public_url}")
        target_open_url = public_url
    else:
        log("\n  ⚠️ 尚未取得全球網址，您仍可使用本機網址。")
        target_open_url = "http://127.0.0.1:8000"

    log(f"  📱 手機本機網址:                http://127.0.0.1:8000\n")
    log("  💡 特點：")
    log("     1. 使用手機 4G/5G 或 家用 Wi-Fi，100% 免驗證碼、零被擋！")
    log("     2. 支援 4K/1080p 高畫質 MP4 與 320kbps MP3 下載！")
    log("     3. 將「全球公開網址」傳給全世界的朋友，他們都能直接使用！")
    log("=" * 80)

    # 嘗試在 Android 上自動打開瀏覽器
    log("\n正在為您在手機瀏覽器開啟網站...")
    try:
        if shutil.which("termux-open-url"):
            subprocess.Popen(["termux-open-url", target_open_url])
        elif shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", target_open_url])
    except Exception:
        pass

    log("\n[系統運作中] 請保持 Termux 視窗運作 (可切至背景)。若要關閉請按 Ctrl+C。\n")

    def shutdown(signum=None, frame=None):
        log("\n正在關閉服務...")
        if tunnel_proc:
            try:
                tunnel_proc.terminate()
            except Exception:
                pass
        try:
            server_proc.terminate()
        except Exception:
            pass
        log("服務已安全結束。")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            if server_proc.poll() is not None:
                log("[提示] 本地伺服器已停止。")
                break
            if tunnel_proc and tunnel_proc.poll() is not None:
                log("[提示] Cloudflare Tunnel 連線中斷。")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown()
    finally:
        if tunnel_proc:
            try:
                tunnel_proc.terminate()
            except Exception:
                pass
        try:
            server_proc.terminate()
        except Exception:
            pass

if __name__ == "__main__":
    main()
