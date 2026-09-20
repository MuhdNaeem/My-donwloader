import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import yt_dlp
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

SCRIPT_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = SCRIPT_DIR / "downloads"
STATIC_DIR = SCRIPT_DIR / "static"
COOKIES_FILE = SCRIPT_DIR / "cookies.txt"
HISTORY_FILE = DOWNLOAD_DIR / "history.json"

DOWNLOAD_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

jobs: dict[str, dict[str, Any]] = {}
jobs_lock = threading.Lock()
active_downloads = 0
active_lock = threading.Lock()
MAX_PARALLEL = 2


def detect_ffmpeg() -> Optional[str]:
    try:
        import imageio_ffmpeg

        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and Path(exe).exists():
            return exe
    except Exception:
        pass

    from shutil import which

    found = which("ffmpeg")
    return found


FFMPEG_PATH = detect_ffmpeg()


def load_history() -> list[dict[str, Any]]:
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_history(entries: list[dict[str, Any]]) -> None:
    HISTORY_FILE.write_text(json.dumps(entries[:80], indent=2), encoding="utf-8")


def append_history(entry: dict[str, Any]) -> None:
    entries = load_history()
    entries.insert(0, entry)
    save_history(entries)


def friendly_error(url: str, message: str) -> str:
    platform = detect_platform(url)
    text = message or "Download failed."
    lowered = text.lower()
    if platform == "tiktok" and ("ip address is blocked" in lowered or "status code 0" in lowered):
        return (
            "TikTok blocked this network. Put a cookies.txt export from a logged-in TikTok "
            "browser session in this app folder, or retry on another connection/VPN."
        )
    if platform == "youtube" and any(
        token in lowered for token in ("sign in to confirm", "bot", "confirm you’re not", "confirm you're not")
    ):
        return (
            "YouTube asked for a browser session. Export cookies.txt from Chrome/Firefox "
            "(logged into YouTube) and save it next to main.py, then try again."
        )
    if "ffmpeg" in lowered and "not found" in lowered:
        return "FFmpeg is needed to merge this quality. Restart the app so the bundled FFmpeg can load."
    return text


def detect_platform(url: str) -> str:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    mapping = {
        "youtube.com": "youtube",
        "m.youtube.com": "youtube",
        "youtu.be": "youtube",
        "music.youtube.com": "youtube",
        "tiktok.com": "tiktok",
        "vm.tiktok.com": "tiktok",
        "vt.tiktok.com": "tiktok",
        "facebook.com": "facebook",
        "fb.watch": "facebook",
        "m.facebook.com": "facebook",
        "instagram.com": "instagram",
        "x.com": "twitter",
        "twitter.com": "twitter",
        "vxtwitter.com": "twitter",
        "reddit.com": "reddit",
        "v.redd.it": "reddit",
        "vimeo.com": "vimeo",
        "dailymotion.com": "dailymotion",
        "twitch.tv": "twitch",
    }
    for domain, name in mapping.items():
        if host == domain or host.endswith("." + domain):
            return name
    return "generic"


def format_selector(quality: str) -> str:
    if quality == "audio":
        return "bestaudio/best"
    if quality == "best":
        if FFMPEG_PATH:
            return "bv*[ext=mp4]+ba[ext=m4a]/bv*+ba/b"
        return "b[ext=mp4]/b"
    height = int(quality)
    if FFMPEG_PATH:
        return (
            f"bv*[height<={height}][ext=mp4]+ba[ext=m4a]/"
            f"bv*[height<={height}]+ba/"
            f"b[height<={height}]/b"
        )
    return f"b[height<={height}][ext=mp4]/b[height<={height}]/b"


def base_ydl_opts(url: str, proxy: Optional[str] = None) -> dict[str, Any]:
    platform = detect_platform(url)
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": True,
        "overwrites": False,
        "retries": 12,
        "fragment_retries": 12,
        "extractor_retries": 5,
        "file_access_retries": 5,
        "concurrent_fragment_downloads": 4,
        "socket_timeout": 30,
        "nocheckcertificate": True,
        "geo_bypass": True,
        "ignoreerrors": False,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": f"{urlparse(url).scheme}://{urlparse(url).netloc}/",
        },
        "extractor_args": {},
    }

    if platform == "youtube":
        opts["extractor_args"]["youtube"] = {
            "player_client": ["default", "ios", "web", "tv"],
        }
    elif platform == "tiktok":
        opts["extractor_args"]["tiktok"] = {
            "api_hostname": ["api16-normal-c-useast1a.tiktokv.com"],
        }

    try:
        import curl_cffi  # noqa: F401
        from yt_dlp.networking.impersonate import ImpersonateTarget

        opts["impersonate"] = ImpersonateTarget.from_str("chrome")
    except Exception:
        pass

    if COOKIES_FILE.exists():
        opts["cookiefile"] = str(COOKIES_FILE)

    if FFMPEG_PATH:
        opts["ffmpeg_location"] = FFMPEG_PATH

    if proxy:
        opts["proxy"] = proxy.strip()

    return opts


def seconds_to_clock(value: Optional[float]) -> str:
    if not value:
        return "0:00"
    value = int(value)
    h, rem = divmod(value, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def compact_size(num: Optional[int]) -> str:
    if not num:
        return ""
    units = ["B", "KB", "MB", "GB"]
    size = float(num)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return ""


def pick_thumbnail(info: dict[str, Any]) -> Optional[str]:
    thumbs = info.get("thumbnails") or []
    if thumbs:
        best = max(thumbs, key=lambda t: (t.get("height") or 0) * (t.get("width") or 0))
        return best.get("url") or info.get("thumbnail")
    return info.get("thumbnail")


def summarize_info(info: dict[str, Any], url: str) -> dict[str, Any]:
    formats = []
    seen = set()
    for fmt in info.get("formats") or []:
        height = fmt.get("height")
        vcodec = fmt.get("vcodec")
        acodec = fmt.get("acodec")
        if not height or vcodec in (None, "none"):
            continue
        if height in seen:
            continue
        seen.add(height)
        has_audio = acodec not in (None, "none")
        formats.append(
            {
                "height": height,
                "note": f"{height}p" + ("" if has_audio or FFMPEG_PATH else " (video only)"),
            }
        )
    formats.sort(key=lambda f: f["height"], reverse=True)

    return {
        "id": info.get("id"),
        "title": info.get("title") or "Untitled",
        "uploader": info.get("uploader") or info.get("channel") or info.get("creator") or "",
        "duration": info.get("duration"),
        "duration_text": seconds_to_clock(info.get("duration")),
        "thumbnail": pick_thumbnail(info),
        "webpage_url": info.get("webpage_url") or url,
        "platform": detect_platform(url),
        "extractor": info.get("extractor_key") or info.get("extractor"),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "width": info.get("width"),
        "height": info.get("height"),
        "formats": formats[:12],
        "is_live": bool(info.get("is_live")),
        "ffmpeg": bool(FFMPEG_PATH),
    }


def parse_percent(hook_data: dict[str, Any]) -> float:
    downloaded = hook_data.get("downloaded_bytes") or 0
    total = hook_data.get("total_bytes") or hook_data.get("total_bytes_estimate") or 0
    if total:
        return round(min(100.0, downloaded * 100 / total), 1)
    raw = hook_data.get("_percent_str") or ""
    match = re.search(r"([\d.]+)", raw)
    return float(match.group(1)) if match else 0.0


def update_job(job_id: str, **fields: Any) -> None:
    with jobs_lock:
        if job_id in jobs:
            jobs[job_id].update(fields)
            jobs[job_id]["updated_at"] = time.time()


def make_progress_hook(job_id: str):
    def hook(d: dict[str, Any]) -> None:
        with jobs_lock:
            cancelled = jobs.get(job_id, {}).get("cancelled")
        if cancelled:
            raise yt_dlp.utils.DownloadError("Cancelled")

        status = d.get("status")
        if status == "downloading":
            update_job(
                job_id,
                status="downloading",
                percent=parse_percent(d),
                speed=d.get("_speed_str", "").strip(),
                eta=d.get("_eta_str", "").strip(),
                filename=os.path.basename(d.get("filename") or ""),
            )
        elif status == "finished":
            update_job(
                job_id,
                status="processing",
                percent=100,
                speed="",
                eta="",
                filename=os.path.basename(d.get("filename") or ""),
                message="Finishing file…",
            )

    return hook


def run_download(job_id: str, url: str, quality: str, proxy: Optional[str] = None) -> None:
    global active_downloads
    with active_lock:
        active_downloads += 1

    try:
        opts = base_ydl_opts(url, proxy=proxy)
        opts.update(
            {
                "format": format_selector(quality),
                "outtmpl": str(DOWNLOAD_DIR / "%(title).120s [%(id)s].%(ext)s"),
                "progress_hooks": [make_progress_hook(job_id)],
                "restrictfilenames": False,
                "windowsfilenames": True,
            }
        )
        if quality == "audio" and FFMPEG_PATH:
            opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]
        elif FFMPEG_PATH:
            opts["merge_output_format"] = "mp4"
            opts["postprocessor_args"] = {"default": ["-movflags", "+faststart"]}

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise yt_dlp.utils.DownloadError("No media was returned.")
            if info.get("_type") == "playlist":
                entries = [e for e in (info.get("entries") or []) if e]
                info = entries[0] if entries else info
            filepath = Path(ydl.prepare_filename(info))
            if quality == "audio" and FFMPEG_PATH:
                filepath = filepath.with_suffix(".mp3")
            if not filepath.exists():
                stem = filepath.with_suffix("")
                matches = list(DOWNLOAD_DIR.glob(stem.name + ".*"))
                if matches:
                    filepath = matches[0]

        size = filepath.stat().st_size if filepath.exists() else 0
        entry = {
            "id": job_id,
            "title": info.get("title") or filepath.name,
            "platform": detect_platform(url),
            "url": info.get("webpage_url") or url,
            "path": str(filepath),
            "filename": filepath.name,
            "size": size,
            "size_text": compact_size(size),
            "quality": quality,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
        }
        append_history(entry)
        update_job(job_id, status="done", percent=100, result=entry, message="Saved")
    except yt_dlp.utils.DownloadError as exc:
        update_job(job_id, status="error", error=friendly_error(url, str(exc)))
    except Exception as exc:
        update_job(job_id, status="error", error=friendly_error(url, str(exc)))
    finally:
        with active_lock:
            active_downloads -= 1


class ProbeRequest(BaseModel):
    url: str = Field(min_length=8)
    proxy: Optional[str] = None


class DownloadRequest(BaseModel):
    url: str = Field(min_length=8)
    quality: str = "best"
    proxy: Optional[str] = None


app = FastAPI(title="Pulse Downloader")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
def status() -> dict[str, Any]:
    return {
        "yt_dlp": yt_dlp.version.__version__,
        "ffmpeg": bool(FFMPEG_PATH),
        "ffmpeg_path": FFMPEG_PATH,
        "cookies": COOKIES_FILE.exists(),
        "download_dir": str(DOWNLOAD_DIR),
        "active": active_downloads,
    }


@app.post("/api/probe")
def probe(body: ProbeRequest) -> dict[str, Any]:
    url = body.url.strip()
    if not re.match(r"^https?://", url, re.I):
        raise HTTPException(400, "Paste a full http(s) video link.")
    opts = base_ydl_opts(url, proxy=body.proxy)
    opts["skip_download"] = True
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if info and info.get("_type") == "playlist":
            entries = [e for e in (info.get("entries") or []) if e]
            if not entries:
                raise HTTPException(400, "This playlist has no downloadable videos.")
            info = entries[0]
            summary = summarize_info(info, url)
            summary["playlist_note"] = "Playlist detected — only the first video will be fetched."
            return summary
        return summarize_info(info, url)
    except yt_dlp.utils.DownloadError as exc:
        raise HTTPException(400, friendly_error(url, str(exc))) from exc
    except HTTPException:
        raise
    except Exception as exc:
        message = str(exc) or f"{type(exc).__name__} while reading the video."
        raise HTTPException(500, friendly_error(url, message)) from exc


@app.post("/api/download")
def start_download(body: DownloadRequest) -> dict[str, Any]:
    url = body.url.strip()
    quality = body.quality.strip() or "best"
    if quality not in {"best", "audio", "2160", "1440", "1080", "720", "480", "360"}:
        raise HTTPException(400, "Unsupported quality.")
    with active_lock:
        if active_downloads >= MAX_PARALLEL:
            raise HTTPException(429, "Two downloads are already running. Wait a moment.")
    job_id = uuid.uuid4().hex[:12]
    with jobs_lock:
        jobs[job_id] = {
            "id": job_id,
            "status": "queued",
            "percent": 0,
            "url": url,
            "quality": quality,
            "cancelled": False,
            "created_at": time.time(),
        }
    threading.Thread(target=run_download, args=(job_id, url, quality, body.proxy), daemon=True).start()
    return {"id": job_id}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> dict[str, Any]:
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(404, "Job not found.")
        return job


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> dict[str, str]:
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(404, "Job not found.")
        job["cancelled"] = True
        job["status"] = "cancelling"
        job["message"] = "Stopping…"
    return {"ok": "cancelling"}


@app.get("/api/history")
def history() -> list[dict[str, Any]]:
    entries = load_history()
    for item in entries:
        path = Path(item.get("path") or "")
        item["exists"] = path.exists()
    return entries


@app.post("/api/open-folder")
def open_folder() -> dict[str, str]:
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    if sys.platform == "win32":
        os.startfile(DOWNLOAD_DIR)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(DOWNLOAD_DIR)])
    else:
        subprocess.Popen(["xdg-open", str(DOWNLOAD_DIR)])
    return {"ok": "opened"}


@app.post("/api/open-file")
def open_file(path: str = Query(...)) -> dict[str, str]:
    target = Path(path).resolve()
    if DOWNLOAD_DIR.resolve() not in target.parents and target.parent != DOWNLOAD_DIR.resolve():
        raise HTTPException(403, "File is outside the downloads folder.")
    if not target.exists():
        raise HTTPException(404, "File no longer exists.")
    if sys.platform == "win32":
        os.startfile(target)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(target)])
    else:
        subprocess.Popen(["xdg-open", str(target)])
    return {"ok": "opened"}


@app.get("/api/thumb")
async def proxy_thumb(url: str = Query(...)) -> Response:
    import urllib.request

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(400, "Invalid thumbnail URL.")
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
            content_type = resp.headers.get("Content-Type", "image/jpeg")
        return Response(content=data, media_type=content_type)
    except Exception as exc:
        raise HTTPException(502, f"Thumbnail failed: {exc}") from exc


def main() -> None:
    import uvicorn

    print("=" * 60)
    print(" Pulse Downloader")
    print(f" yt-dlp  {yt_dlp.version.__version__}")
    print(f" FFmpeg  {'yes' if FFMPEG_PATH else 'not found (progressive files only)'}")
    print(f" Cookies {'cookies.txt found' if COOKIES_FILE.exists() else 'optional — add cookies.txt for stubborn YouTube links'}")
    print(" Open    http://127.0.0.1:8765")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")


if __name__ == "__main__":
    main()
