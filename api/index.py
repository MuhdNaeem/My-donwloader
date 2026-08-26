from flask import Flask, request, jsonify, render_template_string
import yt_dlp

app = Flask(__name__)


HTML = """
<!DOCTYPE html>
<html lang="en">

<head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>Video Downloader</title>

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

            font-family:
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                sans-serif;

            background: #f1f5f9;
        }

        .card {
            width: 100%;
            max-width: 450px;

            padding: 30px;

            background: white;

            border-radius: 20px;

            box-shadow:
                0 10px 40px rgba(0,0,0,.10);
        }

        h1 {
            margin: 0;
            text-align: center;
            font-size: 28px;
        }

        .subtitle {
            text-align: center;
            color: #64748b;
            margin: 10px 0 25px;
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
            font-weight: 600;

            cursor: pointer;
        }

        button:disabled {
            opacity: .6;
        }

        #status {
            margin-top: 20px;

            text-align: center;

            display: none;

            line-height: 1.5;
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

    </style>

</head>


<body>

<div class="card">

    <h1>📥 Video Downloader</h1>

    <div class="subtitle">
        Facebook • YouTube • TikTok
    </div>


    <input
        id="url"
        type="url"
        placeholder="Paste video URL..."
        autocomplete="off"
    >


    <button id="downloadBtn">
        Download Video
    </button>


    <div id="status"></div>

</div>


<script>

const button =
    document.getElementById("downloadBtn");

const input =
    document.getElementById("url");

const status =
    document.getElementById("status");


function showStatus(message, type) {

    status.style.display = "block";

    status.className = type;

    status.textContent = message;

}


button.addEventListener("click", async () => {

    const url = input.value.trim();


    if (!url) {

        showStatus(
            "Please paste a video URL.",
            "error"
        );

        return;
    }


    button.disabled = true;

    button.textContent =
        "Finding video...";


    showStatus(
        "Getting video information...",
        "loading"
    );


    try {

        const response =
            await fetch("/download", {

                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    url: url
                })

            });


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.error ||
                "Download failed."
            );

        }


        showStatus(
            "Video found. Starting download...",
            "success"
        );


        /*
         * Open the direct media URL.
         *
         * The phone/browser handles
         * the actual download.
         */

        window.location.href =
            data.url;


    } catch (error) {

        showStatus(
            error.message ||
            "Something went wrong.",
            "error"
        );

    }


    button.disabled = false;

    button.textContent =
        "Download Video";

});

</script>

</body>

</html>
"""


@app.route("/", methods=["GET"])
def home():

    return render_template_string(HTML)


@app.route("/download", methods=["POST"])
def download():

    data = request.get_json(silent=True)


    if not data:

        return jsonify({
            "error": "Invalid request."
        }), 400


    url = data.get("url", "").strip()


    if not url:

        return jsonify({
            "error":
                "Please provide a video URL."
        }), 400


    try:

        print("Processing URL:", url)


        options = {

            # Best SINGLE file containing
            # video + audio.
            #
            # No FFmpeg required.

            "format": "best",

            "quiet": False,

            "no_warnings": False,

            "noplaylist": True,

            "skip_download": True,

        }


        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                url,
                download=False
            )


        video_url = info.get("url")


        if not video_url:

            return jsonify({
                "error":
                    "No downloadable video was found."
            }), 404


        return jsonify({

            "url": video_url,

            "title":
                info.get(
                    "title",
                    "video"
                )

        })


    except yt_dlp.utils.DownloadError as e:

        print(
            "yt-dlp error:",
            repr(e)
        )


        return jsonify({

            "error":
                "This video could not be accessed. "
                "It may be private, unavailable, "
                "login-protected, or unsupported."

        }), 400


    except Exception as e:

        print(
            "Unexpected error:",
            repr(e)
        )


        return jsonify({

            "error":
                "Something went wrong while "
                "processing the video."

        }), 500


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )