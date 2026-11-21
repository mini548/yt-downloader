import os
import shutil
import uuid
import re
import tempfile
from typing import Dict, Any, Optional
import yt_dlp
import imageio_ffmpeg

def get_ffmpeg_path() -> Optional[str]:
    """Finds ffmpeg from system PATH or falls back to imageio-ffmpeg binary."""
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

def get_base_ydl_opts(use_cookies: bool = True, force_android: bool = False) -> Dict[str, Any]:
    """
    Generates base yt-dlp options.
    If force_android is True or no valid cookies exist, falls back to Android client
    which reliably avoids datacenter bot blocks without requiring browser cookies.
    """
    ffmpeg_bin = get_ffmpeg_path()
    opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "source_address": "0.0.0.0",  # Force IPv4 to avoid datacenter IPv6 blocks
        "js_runtimes": {"node": {}},
    }
    if ffmpeg_bin:
        opts["ffmpeg_location"] = ffmpeg_bin

    cookie_path = None
    if use_cookies and not force_android:
        cookies_env = os.environ.get("YTDLP_COOKIES")
        cookie_candidates = [
            os.path.join(os.path.dirname(__file__), "cookies.txt"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "cookies.txt"),
            os.path.abspath("cookies.txt"),
            "cookies.txt"
        ]
        
        if cookies_env and cookies_env.strip():
            cleaned_cookies = cookies_env.strip().replace("\\n", "\n").replace("\\t", "\t")
            temp_cookie = os.path.join(tempfile.gettempdir(), "yt_cookies.txt")
            try:
                with open(temp_cookie, "w", encoding="utf-8") as f:
                    f.write(cleaned_cookies)
                cookie_path = temp_cookie
            except Exception as e:
                print(f"[WARN] 寫入暫存 Cookie 失敗: {e}")
        else:
            for cp in cookie_candidates:
                if os.path.exists(cp) and os.path.getsize(cp) > 0:
                    cookie_path = cp
                    break

    if cookie_path and not force_android:
        opts["cookiefile"] = cookie_path
    else:
        # Default to Android client which bypasses bot challenges on cloud servers
        opts["extractor_args"] = {
            "youtube": {
                "player_client": ["android"]
            }
        }

    return opts

def _parse_info_data(info: Dict[str, Any], url: str) -> Dict[str, Any]:
    # In case of playlist, take first entry
    if "entries" in info:
        entries = list(info["entries"])
        if not entries:
            raise ValueError("播放清單中未找到可用影片。")
        info = entries[0]

    formats = info.get("formats", [])
    
    # Determine available resolutions
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
    # First attempt: standard opts (with cookies if available, otherwise android client)
    ydl_opts = get_base_ydl_opts(use_cookies=True, force_android=False)
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
        # If bot check, cookie expiration, or format error occurred, retry with forced Android client
        if any(keyword in err_msg for keyword in ["Sign in", "bot", "cookie", "format", "unavailable"]):
            print(f"[INFO] 遭遇限制 ({err_msg[:60]}...)，自動切換至 Android Client 重試...")
            fallback_opts = get_base_ydl_opts(use_cookies=False, force_android=True)
            fallback_opts.update({
                "skip_download": True,
                "extract_flat": False,
                "format": "all",
            })
            with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise ValueError("無法解析影片資訊，請確認網址是否正確。")
                return _parse_info_data(info, url)
        raise e

def _execute_download(url: str, format_type: str, quality: str, output_dir: str, ydl_opts: Dict[str, Any], file_id: str) -> str:
    out_template = os.path.join(output_dir, f"{file_id}_%(title).100B.%(ext)s")
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

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # Find the generated file with prefix file_id
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

def download_video(url: str, format_type: str, quality: str, output_dir: str) -> str:
    """Downloads video or audio and returns the generated absolute file path."""
    os.makedirs(output_dir, exist_ok=True)
    file_id = uuid.uuid4().hex[:8]

    # Attempt 1: standard options
    ydl_opts = get_base_ydl_opts(use_cookies=True, force_android=False)
    try:
        return _execute_download(url, format_type, quality, output_dir, ydl_opts, file_id)
    except Exception as e:
        err_msg = str(e)
        if any(keyword in err_msg for keyword in ["Sign in", "bot", "cookie", "format", "unavailable"]):
            print(f"[INFO] 下載時遭遇限制 ({err_msg[:60]}...)，切換至 Android Client 重試...")
            file_id_fallback = uuid.uuid4().hex[:8]
            fallback_opts = get_base_ydl_opts(use_cookies=False, force_android=True)
            return _execute_download(url, format_type, quality, output_dir, fallback_opts, file_id_fallback)
        raise e
