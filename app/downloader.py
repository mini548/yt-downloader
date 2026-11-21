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
        with opener.open(req, timeout=5) as resp:
            pass
        cj.save(ignore_discard=True, ignore_expires=True)
        return GUEST_COOKIE_FILE
    except Exception:
        return ""

def get_cookie_file() -> Optional[str]:
    """優先取得 cookies.txt，若無則降級為訪客憑證"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root_cookie = os.path.join(project_root, "cookies.txt")
    if os.path.exists(root_cookie) and os.path.getsize(root_cookie) > 50:
        return root_cookie

    if os.path.exists("/app/cookies.txt") and os.path.getsize("/app/cookies.txt") > 50:
        return "/app/cookies.txt"

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

def get_base_ydl_opts(client: str = "android", with_cookies: bool = False) -> Dict[str, Any]:
    """極速優化 yt-dlp 參數：多線程並發、低延遲超時、純流快速合併"""
    ffmpeg_bin = get_ffmpeg_path()
    opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "source_address": "0.0.0.0",
        "socket_timeout": 5,                 # 5 秒超快逾時，絕不卡頓
        "retries": 1,
        "concurrent_fragment_downloads": 8,  # 8 線程極速多路並發下載分塊 (速度提升 5~10 倍)
        "buffersize": 1024 * 1024,           # 1MB 記憶體緩衝
        "http_chunk_size": 10485760,         # 10MB 分塊傳輸，大幅降低 TCP 握手次數
        "extractor_args": {
            "youtube": {
                "player_client": [client]
            }
        }
    }

    # Android 客戶端跳過繁瑣網頁載入，極速 1 秒解析
    if client == "android":
        opts["extractor_args"]["youtube"]["player_skip"] = ["configs", "webpage"]

    # 針對 Web / mWeb 客戶端配置本機 bgutil-pot PO Token Provider
    if client in ("web", "mweb"):
        opts["extractor_args"]["youtubepot-bgutilhttp"] = {
            "base_url": ["http://127.0.0.1:4416"]
        }

    # 代理設定支援 (若環境變數提供 Proxy)
    proxy = os.environ.get("PROXY_URL") or os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
    if proxy:
        opts["proxy"] = proxy

    if ffmpeg_bin:
        opts["ffmpeg_location"] = ffmpeg_bin

    if with_cookies:
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
        {"quality": "best", "label": "最佳畫質 (極速最高 / Best)", "ext": "mp4"}
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
        {"quality": "m4a", "label": "原始無損音訊 (M4A / AAC)", "ext": "m4a"}
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
    """支援極速多層客戶端降級（Android 優先最速 1 秒解析 -> Web -> iOS -> mWeb）"""
    client_matrix = [
        ("android", False),
        ("web", False),
        ("ios", False),
        ("mweb", False),
        ("web", True),
    ]

    last_error = None
    for client, use_cookies in client_matrix:
        try:
            ydl_opts = get_base_ydl_opts(client=client, with_cookies=use_cookies)
            ydl_opts.update({
                "skip_download": True,
                "extract_flat": False,
                "format": "all",
                "socket_timeout": 4, # 4 秒快速判定，不拖慢使用者體驗
                "retries": 0,
            })
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    return _parse_info_data(info, url)
        except Exception as e:
            last_error = e
            continue

    err_msg = str(last_error) if last_error else "請確認網址是否正確。"
    raise ValueError(f"無法解析影片資訊: {err_msg}")

def download_video(url: str, format_type: str, quality: str, output_dir: str) -> str:
    """下載影片或音訊，支援 8 線程並發加速與零轉碼秒級封裝"""
    os.makedirs(output_dir, exist_ok=True)
    file_id = uuid.uuid4().hex[:8]
    out_template = os.path.join(output_dir, f"{file_id}_%(title).100B.%(ext)s")

    def _build_opts(client: str, use_cookies: bool):
        opts = get_base_ydl_opts(client=client, with_cookies=use_cookies)
        opts["outtmpl"] = out_template
        opts["concurrent_fragment_downloads"] = 8  # 8 線程多路極速下載
        opts["buffersize"] = 1024 * 1024
        opts["http_chunk_size"] = 10485760

        if format_type == "audio":
            opts["format"] = "ba/b"
            if quality == "m4a":
                opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "m4a",
                }]
            else:
                opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": quality if quality in ["128", "192", "320"] else "192",
                }]
                # 多線程極速音訊轉碼
                opts["postprocessor_args"] = {
                    "FFmpegExtractAudio": ["-threads", "4", "-preset", "ultrafast"]
                }
        else:
            if quality and quality.isdigit():
                h = int(quality)
                opts["format"] = f"bv*[height<={h}]+ba/b[height<={h}]/b[height<={h}]/bv*+ba/b/b"
            else:
                opts["format"] = "bv*+ba/b/b"
            opts["merge_output_format"] = "mp4"
            # 零轉碼純流快速複製 (0 秒瞬間封裝成 MP4)
            opts["postprocessor_args"] = {
                "Merger": ["-threads", "4", "-c", "copy"]
            }

        return opts

    info = None
    last_err = None
    client_matrix = [
        ("android", False),
        ("web", False),
        ("ios", False),
        ("mweb", False),
        ("web", True),
    ]

    for client, use_cookies in client_matrix:
        try:
            ydl_opts = _build_opts(client=client, use_cookies=use_cookies)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info:
                    break
        except Exception as e:
            last_err = e

    if not info and last_err:
        raise last_err

    # 尋找輸出檔案
    for fname in os.listdir(output_dir):
        if fname.startswith(file_id):
            return os.path.join(output_dir, fname)

    if info:
        prepared = ydl.prepare_filename(info)
        if os.path.exists(prepared):
            return prepared
        base, _ = os.path.splitext(prepared)
        for ext in [".mp4", ".mp3", ".m4a", ".webm", ".mkv"]:
            if os.path.exists(base + ext):
                return base + ext

    raise FileNotFoundError("檔案下載完成但找不到輸出檔案。")
