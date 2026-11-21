import os
import asyncio
import urllib.parse
import urllib.request
import time
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import yt_dlp

from .downloader import extract_video_info, download_video, sanitize_filename, get_base_ydl_opts

app = FastAPI(
    title="YouTube Downloader Web App",
    description="全球通用的 YouTube 高畫質影片與 MP3 下載服務",
    version="1.0.0"
)

# 允許所有跨域請求 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp_downloads")
os.makedirs(TEMP_DIR, exist_ok=True)

pot_process = None

@app.on_event("startup")
async def startup_event():
    global pot_process
    bin_path = "/usr/local/bin/bgutil-pot"
    if os.path.exists(bin_path):
        import subprocess
        try:
            pot_process = subprocess.Popen(
                [bin_path, "server", "--host", "127.0.0.1", "--port", "4416"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print(f"[INFO] 成功啟動 PO Token Server (PID: {pot_process.pid})")
        except Exception as e:
            print(f"[WARN] 啟動 PO Token Server 失敗: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    global pot_process
    if pot_process:
        try:
            pot_process.terminate()
        except Exception:
            pass

class InfoRequest(BaseModel):
    url: str

def cleanup_file(filepath: str):
    """下載傳輸完成後自動刪除伺服器上的暫存檔案"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"清理暫存檔失敗: {filepath}, 錯誤: {e}")

@app.get("/api/health")
@app.head("/api/health")
async def health_check():
    return {"status": "ok", "service": "YouTube Downloader", "version": "1.0.0"}

@app.get("/api/diag")
async def diag_check():
    """診斷端點：檢查內部 PO Token 伺服器狀態與環境設定"""
    pot_status = "unavailable"
    try:
        with urllib.request.urlopen("http://127.0.0.1:4416/ping", timeout=2) as r:
            pot_status = r.read().decode()
    except Exception as e:
        pot_status = f"error: {str(e)}"

    import yt_dlp.version
    cookie_exists = os.path.exists("/app/cookies.txt") or os.path.exists("cookies.txt")
    has_proxy = bool(os.environ.get("PROXY_URL") or os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY"))

    return {
        "status": "ok",
        "yt_dlp_version": yt_dlp.version.__version__,
        "pot_server_ping": pot_status,
        "cookie_file_configured": cookie_exists,
        "proxy_configured": has_proxy
    }

@app.get("/api/test_client")
async def test_client(
    url: str = Query("https://www.youtube.com/watch?v=jNQXAC9IVRw"),
    client: str = Query("web"),
    use_cookies: bool = Query(False)
):
    """快速測試特定客戶端的解析結果與詳細報錯"""
    t0 = time.time()
    opts = get_base_ydl_opts(client=client, with_cookies=use_cookies)
    opts.update({
        "skip_download": True,
        "extract_flat": False,
        "format": "all",
        "socket_timeout": 5,
        "retries": 1,
    })
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            elapsed = round(time.time() - t0, 2)
            formats = [f.get("format_id") for f in info.get("formats", []) if f.get("vcodec") != "none"]
            return {
                "success": True,
                "elapsed_sec": elapsed,
                "client": client,
                "use_cookies": use_cookies,
                "title": info.get("title"),
                "video_formats_count": len(formats),
                "example_formats": formats[:5]
            }
    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        return {
            "success": False,
            "elapsed_sec": elapsed,
            "client": client,
            "use_cookies": use_cookies,
            "error_type": type(e).__name__,
            "error_msg": str(e)
        }

@app.post("/api/info")
async def get_info(req: InfoRequest):
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="請提供有效的 YouTube 影片網址。")
    try:
        info = await asyncio.to_thread(extract_video_info, req.url.strip())
        return info
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/download")
async def download_endpoint(
    background_tasks: BackgroundTasks,
    url: str = Query(..., description="YouTube 影片網址"),
    format_type: str = Query("video", pattern="^(video|audio)$"),
    quality: str = Query("1080", description="畫質 (例如 1080, 720, best) 或 音質 (例如 320, 192, m4a)")
):
    try:
        filepath = await asyncio.to_thread(
            download_video, url.strip(), format_type, quality, TEMP_DIR
        )

        if not os.path.exists(filepath):
            raise HTTPException(status_code=500, detail="下載失敗，找不到產生的檔案。")

        filename = os.path.basename(filepath)
        display_filename = filename[9:] if len(filename) > 9 and filename[8] == "_" else filename
        display_filename = sanitize_filename(display_filename)

        quoted_filename = urllib.parse.quote(display_filename)

        # 請求完成後自動清理伺服器暫存
        background_tasks.add_task(cleanup_file, filepath)

        media_type = "video/mp4" if format_type == "video" else "audio/mpeg"
        if display_filename.endswith(".m4a"):
            media_type = "audio/mp4"

        headers = {
            "Content-Disposition": f"attachment; filename=\"{display_filename}\"; filename*=UTF-8''{quoted_filename}"
        }

        return FileResponse(
            path=filepath,
            media_type=media_type,
            filename=display_filename,
            headers=headers
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"下載過程發生錯誤: {str(e)}")

# 掛載前端靜態檔案
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
@app.head("/")
async def root():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "YouTube Downloader API is running."}
