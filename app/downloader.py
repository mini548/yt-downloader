import os
import shutil
import uuid
import re
import time
import http.cookiejar
import urllib.request
import tempfile
from typing import Dict, Any, Optional
import yt_dlp
import imageio_ffmpeg

GUEST_COOKIE_FILE = os.path.join(tempfile.gettempdir(), "yt_guest_cookies.txt")

def ensure_guest_cookies() -> str:
    """產生 YouTube 訪客憑證 (作為備用)"""
    now = time.time()
    if os.path.exists(GUEST_COOKIE_FILE) and (now - os.path.getmtime(GUEST_COOKIE_FILE)) < 21600:
        return GUEST_COOKIE_FILE

    try:
        cj = http.cookiejar.MozillaCookieJar(GUEST_COOKIE_FILE)
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        req = urllib.request.Request(
            "https://www.youtube.com",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            }
        )
        with opener.open(req, timeout=10) as resp:
            pass
        cj.save(ignore_discard=True, ignore_expires=True)
        return GUEST_COOKIE_FILE
    except Exception as e:
        print(f"[WARN] 產生訪客憑證失敗: {e}")
        return ""

def get_cookie_file() -> Optional[str]:
    """優先取得使用者提供的 cookies.txt，若無則降級為訪客憑證"""
    # 1. 專案根目錄的 cookies.txt
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root_cookie = os.path.join(project_root, "cookies.txt")
    if os.path.exists(root_cookie) and os.path.getsize(root_cookie) > 50:
        return root_cookie

    # 2. 容器根目錄 /app/cookies.txt
    if os.path.exists("/app/cookies.txt") and os.path.getsize("/app/cookies.txt") > 50:
        return "/app/cookies.txt"

    # 3. 訪客 Cookie
    guest = ensure_guest_cookies()
    if guest and os.path.exists(guest):
        return guest

    return None

def get_ffmpeg_path() -> Optional[str]:
    """尋找系統 FFmpeg 或 imageio-ffmpeg 二進位檔"""
    which_ffmpeg = shutil.which("ffmpeg")
    if which_ffmpeg:
        return which_ffmpeg
    try:
        ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        if ffmpeg_bin and os.path.exists(ffmpeg_bin):
            return ffmpeg_bin
    except Exception:
        pass
    return None

def format_duration(seconds: Optional[int]) -> str:
    if not seconds:
        return "未知"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def get_base_ydl_opts() -> Dict[str, Any]:
    """生成包含憑證、多客戶端與 PO Token 整合的 yt-dlp 核心參數"""
    ffmpeg_bin = get_ffmpeg_path()
    opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "source_address": "0.0.0.0",
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "android", "mweb", "web"]
            }
        }
    }
    if ffmpeg_bin:
        opts["ffmpeg_location"] = ffmpeg_bin

    cookie_file = get_cookie_file()
    if cookie_file and os.path.exists(cookie_file):
        opts["cookiefile"] = cookie_file

    return opts

def _parse_info_data(info: Dict[str, Any], url: str) -> Dict[str, Any]:
    if "entries" in info:
        entries = list(info["entries"])
        if not entries:
            raise ValueError("播放清單中未找到可用影片。")
        info = entries[0]

    formats = info.get("formats", [])
    
    available_heights = set()
    for f in formats:
        h = f.get("height")
        vcodec = f.get("vcodec", "none")
        if h and vcodec != "none" and isinstance(h, int):
            available_heights.add(h)

    max_h = max(available_heights) if available_heights else 720
    
    video_options = [
        {"quality": "best", "label": "最佳畫質 (自動最高 / Best)", "ext": "mp4"}
    ]

    tier_definitions = [
        (2160, "4K (2160p)"),
        (1440, "2K (1440p)"),
        (1080, "Full HD (1080p)"),
        (720, "HD (720p)"),
        (480, "標清 (480p)"),
        (360, "標準 (360p)"),
        (240, "輕量 (240p)"),
    ]

    for res, label in tier_definitions:
        if res <= max_h:
            video_options.append({
                "quality": str(res),
                "label": label,
                "ext": "mp4"
            })

    if len(video_options) == 1:
        video_options.append({"quality": "360", "label": "標準 (360p)", "ext": "mp4"})

    audio_options = [
        {"quality": "320", "label": "超高音質 (MP3 320kbps)", "ext": "mp3"},
        {"quality": "192", "label": "標準音質 (MP3 192kbps)", "ext": "mp3"},
        {"quality": "128", "label": "輕量音質 (MP3 128kbps)", "ext": "mp3"},
        {"quality": "m4a", "label": "原始音訊 (M4A / AAC)", "ext": "m4a"}
    ]

    return {
        "title": info.get("title", "YouTube 影片"),
        "uploader": info.get("uploader", "未知創作者"),
        "duration": format_duration(info.get("duration")),
        "duration_raw": info.get("duration", 0),
        "thumbnail": info.get("thumbnail") or (info.get("thumbnails")[-1]["url"] if info.get("thumbnails") else ""),
        "views": info.get("view_count", 0),
        "video_options": video_options,
        "audio_options": audio_options,
        "url": url
    }

def extract_video_info(url: str) -> Dict[str, Any]:
    ydl_opts = get_base_ydl_opts()
    ydl_opts.update({
        "skip_download": True,
        "extract_flat": False,
        "format": "all",
    })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise ValueError("無法解析影片資訊，請確認網址是否正確。")
            return _parse_info_data(info, url)
    except Exception as e:
        err_msg = str(e)
        if "not a bot" in err_msg or "Sign in" in err_msg:
            # 遭遇風控時，依序使用備用客戶端重試
            for fallback_client in [["android"], ["ios"], ["mweb"]]:
                try:
                    retry_opts = get_base_ydl_opts()
                    retry_opts.update({
                        "skip_download": True,
                        "extract_flat": False,
                        "format": "all",
                        "extractor_args": {
                            "youtube": {
                                "player_client": fallback_client
                            }
                        }
                    })
                    with yt_dlp.YoutubeDL(retry_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        if info:
                            return _parse_info_data(info, url)
                except Exception:
                    continue
        raise e

def download_video(url: str, format_type: str, quality: str, output_dir: str) -> str:
    """下載影片或音訊，支援自動重試與客戶端降級"""
    os.makedirs(output_dir, exist_ok=True)
    file_id = uuid.uuid4().hex[:8]
    out_template = os.path.join(output_dir, f"{file_id}_%(title).100B.%(ext)s")

    ydl_opts = get_base_ydl_opts()
    ydl_opts["outtmpl"] = out_template

    if format_type == "audio":
        ydl_opts["format"] = "ba/b"
        if quality == "m4a":
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
            }]
        else:
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": quality if quality in ["128", "192", "320"] else "192",
            }]
    else:
        if quality and quality.isdigit():
            h = int(quality)
            ydl_opts["format"] = f"bv*[height<={h}]+ba/b[height<={h}]/b[height<={h}]/bv*+ba/b/b"
        else:
            ydl_opts["format"] = "bv*+ba/b/b"
        
        ydl_opts["merge_output_format"] = "mp4"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as e:
        err_msg = str(e)
        if "not a bot" in err_msg or "Sign in" in err_msg:
            # 降級重試
            retry_opts = ydl_opts.copy()
            retry_opts["extractor_args"] = {"youtube": {"player_client": ["android"]}}
            with yt_dlp.YoutubeDL(retry_opts) as ydl:
                info = ydl.extract_info(url, download=True)
        else:
            raise e

    # 尋找產生檔案
    for fname in os.listdir(output_dir):
        if fname.startswith(file_id):
            return os.path.join(output_dir, fname)

    prepared = ydl.prepare_filename(info)
    if os.path.exists(prepared):
        return prepared
    base, _ = os.path.splitext(prepared)
    for ext in [".mp4", ".mp3", ".m4a", ".webm", ".mkv"]:
        if os.path.exists(base + ext):
            return base + ext

    raise FileNotFoundError("檔案下載完成但找不到輸出檔案。")
