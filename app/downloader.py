import os
import shutil
import uuid
import re
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
    # Remove characters unsafe for filenames
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def get_base_ydl_opts() -> Dict[str, Any]:
    """Generates base yt-dlp options with multi-client fallbacks for cloud/datacenter IPs."""
    ffmpeg_bin = get_ffmpeg_path()
    opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "extractor_args": {
            "youtube": {
                # Fallback clients bypass datacenter IP player extraction block
                "player_client": ["android", "ios", "tv_samsung", "web"]
            }
        }
    }
    if ffmpeg_bin:
        opts["ffmpeg_location"] = ffmpeg_bin

    # Cookie support: Check YTDLP_COOKIES environment variable or cookies.txt file
    cookies_env = os.environ.get("YTDLP_COOKIES")
    cookie_file = os.path.join(os.path.dirname(__file__), "cookies.txt")
    if cookies_env and cookies_env.strip():
        temp_cookie = os.path.join(os.path.dirname(__file__), "temp_cookies.txt")
        try:
            with open(temp_cookie, "w", encoding="utf-8") as f:
                f.write(cookies_env.strip())
            opts["cookiefile"] = temp_cookie
        except Exception:
            pass
    elif os.path.exists(cookie_file):
        opts["cookiefile"] = cookie_file

    return opts

def extract_video_info(url: str) -> Dict[str, Any]:
    ydl_opts = get_base_ydl_opts()
    ydl_opts.update({
        "skip_download": True,
        "extract_flat": False,
    })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            raise ValueError("無法解析影片資訊，請確認網址是否正確。")

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
            if h and vcodec != "none":
                available_heights.add(h)

        common_resolutions = [2160, 1440, 1080, 720, 480, 360]
        video_options = []
        for res in common_resolutions:
            matched = [h for h in available_heights if h >= res]
            if matched or res <= 720:
                label = f"{res}p"
                if res >= 2160:
                    label = "4K (2160p)"
                elif res >= 1440:
                    label = "2K (1440p)"
                elif res == 1080:
                    label = "Full HD (1080p)"
                elif res == 720:
                    label = "HD (720p)"
                
                if any(h == res for h in available_heights) or (res in [720, 360] and len(available_heights) > 0):
                    video_options.append({
                        "quality": str(res),
                        "label": label,
                        "ext": "mp4"
                    })

        # If no specific heights found, at least provide "best"
        if not video_options:
            video_options.append({"quality": "best", "label": "最佳畫質 (Best)", "ext": "mp4"})

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

def download_video(url: str, format_type: str, quality: str, output_dir: str) -> str:
    """Downloads video or audio and returns the generated absolute file path."""
    os.makedirs(output_dir, exist_ok=True)
    file_id = uuid.uuid4().hex[:8]
    out_template = os.path.join(output_dir, f"{file_id}_%(title).100B.%(ext)s")

    ydl_opts = get_base_ydl_opts()
    ydl_opts["outtmpl"] = out_template

    if format_type == "audio":
        if quality == "m4a":
            ydl_opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
        else:
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": quality if quality in ["128", "192", "320"] else "192",
            }]
    else:
        # Video download
        if quality and quality.isdigit():
            h = int(quality)
            ydl_opts["format"] = (
                f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/"
                f"bestvideo[height<={h}]+bestaudio/"
                f"best[height<={h}]/best"
            )
        else:
            ydl_opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
        
        ydl_opts["merge_output_format"] = "mp4"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # Find the generated file with prefix file_id
        for fname in os.listdir(output_dir):
            if fname.startswith(file_id):
                return os.path.join(output_dir, fname)

        # Fallback using ydl.prepare_filename
        prepared = ydl.prepare_filename(info)
        if os.path.exists(prepared):
            return prepared
        base, _ = os.path.splitext(prepared)
        for ext in [".mp4", ".mp3", ".m4a", ".webm", ".mkv"]:
            if os.path.exists(base + ext):
                return base + ext

        raise FileNotFoundError("檔案下載完成但找不到輸出檔案。")
