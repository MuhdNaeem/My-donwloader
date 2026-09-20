from flask import Flask, request, jsonify, render_template_string
import yt_dlp

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="referrer" content="no-referrer">
    <title>Universal Video Downloader</title>
    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: #f1f5f9;
        }

        .card {
            width: 100%;
            max-width: 460px;
            padding: 32px 28px;
            background: white;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, .08);
        }

        h1 {
            margin: 0;
            text-align: center;
            font-size: 26px;
            color: #1e293b;
        }

        .subtitle {
            text-align: center;
            color: #64748b;
            font-size: 14px;
            margin: 10px 0 24px;
        }

        input {
            width: 100%;
            padding: 14px 16px;
            border: 1px solid #cbd5e1;
            border-radius: 12px;
            font-size: 15px;
            outline: none;
            transition: border-color 0.2s ease;
        }

        input:focus {
            border-color: #1877f2;
        }

        button {
            width: 100%;
            margin-top: 14px;
            padding: 14px;
            border: none;
            border-radius: 12px;
            background: #1877f2;
            color: white;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s ease, opacity 0.2s ease;
        }

        button:hover {
            background: #166fe5;
        }

        button:disabled {
            opacity: .6;
            cursor: not-allowed;
        }

        #status {
            margin-top: 20px;
            text-align: center;
            display: none;
            line-height: 1.5;
            font-size: 14px;
            word-break: break-word;
        }

        .error {
            color: #dc2626;
        }

        .success {
            color: #16a34a;
        }

        .loading {
            color: #2563eb;
        }

        .download-fallback-link {
            display: inline-block;
            margin-top: 10px;
            padding: 10px 18px;
            background: #16a34a;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            font-size: 14px;
        }

        .download-fallback-link:hover {
            background: #15803d;
        }
    </style>
</head>

<body>
<div class="card">
    <h1>📥 Video Downloader</h1>
    <div class="subtitle">
        YouTube • TikTok • Instagram • Facebook
    </div>

    <input
        id="url"
        type="url"
        placeholder="Paste video URL here..."
        autocomplete="off"
    >

    <button id="downloadBtn">
        Download Video
    </button>

    <div id="status"></div>
</div>

<script>
const button = document.getElementById("downloadBtn");
const input = document.getElementById("url");
const status = document.getElementById("status");

function showStatus(message, type, htmlContent = null) {
    status.style.display = "block";
    status.className = type;
    if (htmlContent) {
        status.innerHTML = htmlContent;
    } else {
        status.textContent = message;
    }
}

button.addEventListener("click", async () => {
    const url = input.value.trim();

    if (!url) {
        showStatus("Please paste a video URL.", "error");
        return;
    }

    button.disabled = true;
    button.textContent = "Finding video...";
    showStatus("Extracting video information...", "loading");

    try {
        const response = await fetch("/download", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ url: url })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Download failed.");
        }

        showStatus("Video found! Starting download...", "success");

        // Trigger direct browser download
        window.location.href = data.url;

        // Also display clickable fallback button in case auto-download is blocked or handled inline
        setTimeout(() => {
            const cleanTitle = (data.title || "video").replace(/[/\\\\?%*:|"<>]/g, "");
            showStatus(
                "",
                "success",
                `<div>✅ Video ready! If download didn't start automatically:</div>` +
                `<a class="download-fallback-link" href="${data.url}" download="${cleanTitle}.mp4" target="_blank" rel="noreferrer">` +
                `📥 Click Here to Download</a>`
            );
        }, 1200);

    } catch (error) {
        showStatus(error.message || "Something went wrong.", "error");
    } finally {
        button.disabled = false;
        button.textContent = "Download Video";
    }
});
</script>
</body>
</html>
"""


def extract_best_media_url(info):
    """
    Extracts the best direct, downloadable media URL from yt-dlp metadata.
    Handles YouTube, TikTok, Instagram, Facebook, and generic sites.
    """
    if not info:
        return None, "video"

    # Handle playlists / carousels / multi-item posts (e.g. Instagram carousels)
    if "entries" in info and info["entries"]:
        for entry in info["entries"]:
            if entry:
                info = entry
                break

    title = info.get("title") or "video"
    formats = info.get("formats") or []

    # 1. Search formats for progressive streams (combined video + audio)
    progressive_formats = []
    for f in formats:
        f_url = f.get("url")
        if not f_url or not isinstance(f_url, str):
            continue

        vcodec = f.get("vcodec")
        acodec = f.get("acodec")
        has_video = vcodec and vcodec != "none"
        has_audio = acodec and acodec != "none"

        if has_video and has_audio:
            protocol = (f.get("protocol") or "").lower()
            # Filter out HLS/DASH manifests that browsers cannot download as a single file
            if "m3u8" in protocol or "dash" in protocol:
                continue
            clean_url = f_url.split("?")[0].lower()
            if clean_url.endswith(".m3u8") or clean_url.endswith(".mpd"):
                continue

            progressive_formats.append(f)

    if progressive_formats:
        def rank_format(f):
            ext = (f.get("ext") or "").lower()
            is_mp4 = 1 if ext == "mp4" else 0

            # Prefer watermark-free streams (especially for TikTok)
            format_id = (f.get("format_id") or "").lower()
            no_watermark = 1 if "watermark" not in format_id else 0

            height = f.get("height") or 0
            width = f.get("width") or 0
            tbr = f.get("tbr") or f.get("vbr") or 0
            filesize = f.get("filesize") or f.get("filesize_approx") or 0

            return (no_watermark, is_mp4, height, width, tbr, filesize)

        best = max(progressive_formats, key=rank_format)
        return best.get("url"), title

    # 2. Check if a direct media URL is at root (common for Facebook and direct extractors)
    root_url = info.get("url")
    if root_url and isinstance(root_url, str):
        clean_root = root_url.split("?")[0].lower()
        if not (clean_root.endswith(".m3u8") or clean_root.endswith(".mpd")):
            return root_url, title

    # 3. Fallback: Search for any direct video stream (even without audio codec specified)
    video_formats = []
    for f in formats:
        f_url = f.get("url")
        if not f_url or not isinstance(f_url, str):
            continue
        vcodec = f.get("vcodec")
        if vcodec and vcodec != "none":
            protocol = (f.get("protocol") or "").lower()
            if "m3u8" not in protocol and "dash" not in protocol:
                clean_url = f_url.split("?")[0].lower()
                if not (clean_url.endswith(".m3u8") or clean_url.endswith(".mpd")):
                    video_formats.append(f)

    if video_formats:
        best_v = max(
            video_formats,
            key=lambda f: (
                1 if (f.get("ext") or "").lower() == "mp4" else 0,
                f.get("height") or 0,
                f.get("tbr") or 0,
            ),
        )
        return best_v.get("url"), title

    # 4. Ultimate fallback: root url or last format in list
    if root_url:
        return root_url, title

    if formats:
        for f in reversed(formats):
            if f.get("url"):
                return f.get("url"), title

    return None, title


@app.route("/", methods=["GET"])
@app.route("/api", methods=["GET"])
@app.route("/api/", methods=["GET"])
@app.route("/api/index", methods=["GET"])
@app.route("/api/index.py", methods=["GET"])
def home():
    return render_template_string(HTML)


@app.route("/download", methods=["POST"])
@app.route("/api/download", methods=["POST"])
@app.route("/api", methods=["POST"])
@app.route("/api/index", methods=["POST"])
@app.route("/api/index.py", methods=["POST"])
def download():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Invalid request."}), 400

    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "Please provide a video URL."}), 400

    try:
        print("Processing URL:", url)

        options = {
            # Prefer single progressive file containing video + audio
            "format": "best[ext=mp4]/best",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "skip_download": True,
            # Use mobile client fallback for YouTube to get progressive streams & bypass bot checks
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "ios", "web"],
                }
            },
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)

        video_url, title = extract_best_media_url(info)

        if not video_url:
            return jsonify({
                "error": "No downloadable video stream was found for this link."
            }), 404

        return jsonify({
            "url": video_url,
            "title": title
        })

    except yt_dlp.utils.DownloadError as e:
        print("yt-dlp error:", repr(e))
        return jsonify({
            "error": "This video could not be accessed. It may be private, unavailable, login-protected, or unsupported."
        }), 400

    except Exception as e:
        print("Unexpected error:", repr(e))
        return jsonify({
            "error": "Something went wrong while processing the video."
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )