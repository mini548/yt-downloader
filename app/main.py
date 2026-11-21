import os
import asyncio
import urllib.parse
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .downloader import extract_video_info, download_video, sanitize_filename

app = FastAPI(
    title="YouTube Downloader Web App",
    description="全球通用的 YouTube 高畫質影片與 MP3 下載服務",
    version="1.0.0"
)

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp_downloads")
os.makedirs(TEMP_DIR, exist_ok=True)

class InfoRequest(BaseModel):
    url: str

def cleanup_file(filepath: str):
    """Deletes temporary file after response is completed."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"清理暫存檔失敗: {filepath}, 錯誤: {e}")

@app.get("/api/health")
@app.head("/api/health")
async def health_check():
    return {"status": "ok", "service": "YouTube Downloader", "version": "2.0.1-diag"}

@app.get("/api/diag")
async def diag_check():
    cookies_env = os.environ.get("YTDLP_COOKIES")
    return {
        "has_ytdlp_cookies_env": bool(cookies_env and cookies_env.strip()),
        "ytdlp_cookies_len": len(cookies_env) if cookies_env else 0,
    }

@app.get("/api/test_client")
async def test_single_client(c: str = "web_embedded"):
    import yt_dlp
    opts = {
        "quiet": True,
        "format": "all",
        "extractor_args": {"youtube": {"player_client": [c]}}
    }
    try:
        def _extract():
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info("https://www.youtube.com/watch?v=jNQXAC9IVRw", download=False)
        info = await asyncio.to_thread(_extract)
        return {"client": c, "status": "ok", "title": info.get("title")}
    except Exception as e:
        return {"client": c, "status": "error", "error": str(e)[:120]}

@app.post("/api/info")
async def get_info(req: InfoRequest):
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="請提供有效的 YouTube 影片網址。")
    try:
        # Run synchronous yt-dlp call in threadpool
        info = await asyncio.to_thread(extract_video_info, req.url.strip())
        return info
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/download")
async def download_endpoint(
    background_tasks: BackgroundTasks,
    url: str = Query(..., description="YouTube 影片網址"),
    format_type: str = Query("video", pattern="^(video|audio)$"),
    quality: str = Query("1080", description="畫質 (例如 1080, 720) 或 音質 (例如 320, 192, m4a)")
):
    try:
        # Run download in threadpool
        filepath = await asyncio.to_thread(
            download_video, url.strip(), format_type, quality, TEMP_DIR
        )

        if not os.path.exists(filepath):
            raise HTTPException(status_code=500, detail="下載失敗，找不到產生的檔案。")

        filename = os.path.basename(filepath)
        # Strip internal uuid prefix (8 chars + underscore)
        display_filename = filename[9:] if len(filename) > 9 and filename[8] == "_" else filename
        display_filename = sanitize_filename(display_filename)

        # Encode filename for Content-Disposition (supports international characters)
        quoted_filename = urllib.parse.quote(display_filename)

        # Set cleanup task
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

# Mount static files for the web frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
@app.head("/")
async def root():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "YouTube Downloader API is running."}
