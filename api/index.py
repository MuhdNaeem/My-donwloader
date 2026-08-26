from flask import Flask, request, jsonify, render_template_string
import yt_dlp

app = Flask(__name__)


HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FB Video Downloader</title>

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

            font-family: Arial, sans-serif;
            background: #f1f5f9;
        }

        .card {
            width: 100%;
            max-width: 450px;
            background: white;
            padding: 30px;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,.1);
        }

        h1 {
            text-align: center;
            margin-bottom: 10px;
        }

        p {
            text-align: center;
            color: #64748b;
            margin-bottom: 25px;
        }

        input {
            width: 100%;
            padding: 15px;
            border: 1px solid #cbd5e1;
            border-radius: 10px;
            font-size: 16px;
            outline: none;
        }

        input:focus {
            border-color: #1877f2;
        }

        button {
            width: 100%;
            margin-top: 15px;
            padding: 15px;

            border: none;
            border-radius: 10px;

            background: #1877f2;
            color: white;

            font-size: 16px;
            font-weight: bold;

            cursor: pointer;
        }

        button:disabled {
            opacity: .6;
        }

        #status {
            margin-top: 20px;
            text-align: center;
            display: none;
        }

        .error {
            color: #dc2626;
        }

        .success {
            color: #16a34a;
        }
    </style>
</head>

<body>

<div class="card">

    <h1>📥 FB Downloader</h1>

    <p>
        Paste a Facebook video or Reel URL
    </p>

    <input
        id="url"
        type="url"
        placeholder="Paste Facebook URL here"
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


button.addEventListener("click", async () => {

    const url = input.value.trim();

    if (!url) {
        showStatus(
            "Please paste a Facebook URL.",
            "error"
        );
        return;
    }


    button.disabled = true;
    button.innerText = "Getting video...";

    showStatus(
        "Finding video...",
        ""
    );


    try {

        const response = await fetch("/api/video", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                url: url
            })

        });


        const data = await response.json();


        if (!response.ok) {
            throw new Error(
                data.error || "Download failed."
            );
        }


        showStatus(
            "Video found! Starting download...",
            "success"
        );


        /*
         * Tell the browser to download the
         * returned video.
         */
        window.location.href = data.url;


    } catch (error) {

        showStatus(
            error.message,
            "error"
        );

    } finally {

        button.disabled = false;
        button.innerText = "Download Video";

    }

});


function showStatus(message, type) {

    status.style.display = "block";
    status.innerText = message;

    status.className = type;

}

</script>

</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(HTML)


@app.route("/api/video", methods=["POST"])
def get_video():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No data received."
        }), 400


    url = data.get("url", "").strip()


    if not url:
        return jsonify({
            "error": "Please provide a Facebook URL."
        }), 400


    if "facebook.com" not in url.lower():
        return jsonify({
            "error": "Please enter a Facebook URL."
        }), 400


    try:

        ydl_opts = {

            # Best SINGLE file containing
            # video + audio.
            #
            # No FFmpeg required.
            "format": "best",

            "quiet": True,

            "no_warnings": True,

            "noplaylist": True,

            # We only want information.
            "skip_download": True,
        }


        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                url,
                download=False
            )


        video_url = info.get("url")


        if not video_url:

            return jsonify({
                "error": "No downloadable video found."
            }), 404


        return jsonify({
            "url": video_url,
            "title": info.get(
                "title",
                "facebook_video"
            )
        })


    except yt_dlp.utils.DownloadError as e:

        print("yt-dlp error:", e)

        return jsonify({
            "error":
                "Could not access this Facebook video."
        }), 400


    except Exception as e:

        print("Error:", e)

        return jsonify({
            "error": "Something went wrong."
        }), 500


# IMPORTANT:
# This makes "python index.py" actually start Flask.

if __name__ == "__main__":

    print("")
    print("=" * 50)
    print("       FACEBOOK VIDEO DOWNLOADER")
    print("=" * 50)
    print("")
    print("Open this URL in your browser:")
    print("")
    print("http://127.0.0.1:5000")
    print("")
    print("Press CTRL+C to stop.")
    print("=" * 50)
    print("")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )