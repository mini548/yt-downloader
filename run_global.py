import os
import sys
import time
import subprocess
import re
import webbrowser
import signal

# 強制無緩衝輸出
def log(msg="", **kwargs):
    print(msg, flush=True, **kwargs)

BANNER = """
=================================================================================
  🚀 YouTube 萬能下載站 (全球公開發布模式)
=================================================================================
"""

def check_dependencies():
    required = ["fastapi", "uvicorn", "yt-dlp", "imageio-ffmpeg"]
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

def main():
    log(BANNER)
    check_dependencies()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    cloudflared_exe = os.path.join(base_dir, "cloudflared.exe")
    if not os.path.exists(cloudflared_exe):
        log("[下載中] 正在下載 Cloudflare 全球穿透工具 (cloudflared.exe)...")
        cf_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        import urllib.request
        urllib.request.urlretrieve(cf_url, cloudflared_exe)
        log("[完成] cloudflared.exe 下載成功！")

    log("步驟 1/3: 正在啟動後端下載伺服器 (FastAPI / Uvicorn)...")
    server_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--log-level", "warning"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # 等待本地伺服器就緒
    import urllib.request
    server_ready = False
    for _ in range(20):
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

    log("步驟 2/3: 本地伺服器已就緒 (http://127.0.0.1:8000)！")
    log("步驟 3/3: 正在連接 Cloudflare 全球高速網路，建立全球公開 HTTPS 網址...")

    tunnel_proc = subprocess.Popen(
        [cloudflared_exe, "tunnel", "--url", "http://127.0.0.1:8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="ignore",
        bufsize=1
    )

    public_url = None
    start_time = time.time()
    while True:
        line = tunnel_proc.stdout.readline()
        if not line and tunnel_proc.poll() is not None:
            break
        match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
        if match:
            public_url = match.group(0)
            break
        if time.time() - start_time > 30:
            break

    if not public_url:
        log("[警告] 未能及時取得 trycloudflare 網址，您仍可使用本地網址: http://127.0.0.1:8000")
    else:
        log("\n" + "=" * 80)
        log("  🎉 服務已成功連線至全球網路！全世界任何地方都能直接連入使用！")
        log("=" * 80)
        log(f"\n  🌐 全球公開網址 (全世界皆可開):  {public_url}")
        log(f"  🏠 本地電腦專用網址:            http://127.0.0.1:8000\n")
        log("  💡 特點：")
        log("     1. 透過您的家用寬頻連線，100% 免驗證碼、零被擋、零失敗！")
        log("     2. 支援 4K/1080p 高畫質 MP4 與 320kbps MP3 下載！")
        log("     3. 將上方「全球公開網址」傳給全世界的朋友，他們都能直接使用！")
        log("=" * 80)
        log("\n正在為您在瀏覽器開啟網站...")
        try:
            webbrowser.open(public_url)
        except Exception:
            pass

    log("\n[系統運作中] 請保持此視窗開啟。若要關閉服務，請直接關閉此視窗或按下 Ctrl+C。\n")

    def shutdown(signum=None, frame=None):
        log("\n正在關閉服務...")
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
            if tunnel_proc.poll() is not None:
                log("[提示] Cloudflare Tunnel 連線中斷。")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown()
    finally:
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
