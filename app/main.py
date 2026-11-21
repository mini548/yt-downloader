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
    version="3.0.0"
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
    return {"status": "ok", "service": "YouTube Downloader", "version": "4.0.1-pot"}

@app.get("/api/ping_pot")
async def ping_pot():
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:4416/ping", timeout=3) as resp:
            return {"pot_status": resp.status, "pot_body": resp.read().decode()}
    except Exception as e:
        return {"pot_error": str(e)}

@app.get("/api/ping_yt")
async def ping_yt():
    import subprocess
    cmd_deno = ["deno", "--version"]
    cmd_curl = ["curl", "-sI", "--connect-timeout", "5", "https://www.youtube.com"]
    
    deno_res = subprocess.run(cmd_deno, capture_output=True, text=True)
    curl_res = subprocess.run(cmd_curl, capture_output=True, text=True)
    
    return {
        "deno": deno_res.stdout.strip() if deno_res.returncode == 0 else f"ERR: {deno_res.stderr}",
        "curl_yt": curl_res.stdout.strip() if curl_res.returncode == 0 else f"ERR: {curl_res.stderr}",
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
    quality: str = Query("1080", description="畫質 (例如 1080, 720) 或 音質 (例如 320, 192, m4a)")
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
