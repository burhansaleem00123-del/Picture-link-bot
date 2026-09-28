import os
import time
import secrets
import threading
import requests
from flask import Flask, request, render_template_string

app = Flask(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
BASE_URL = os.environ["BASE_URL"]

links = {}


def telegram(method, data=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    return requests.post(url, data=data or {}).json()


def bot_loop():
    offset = None

    while True:
        try:
            params = {"timeout": 30}

            if offset is not None:
                params["offset"] = offset

            result = telegram("getUpdates", params)

            for update in result.get("result", []):
                offset = update["update_id"] + 1

                message = update.get("message", {})
                chat = message.get("chat", {})
                text = message.get("text", "")

                if text == "/start":
                    token = secrets.token_urlsafe(16)

                    links[token] = chat["id"]

                    link = f"{BASE_URL}/photo/{token}"

                    keyboard = (
                        '{"inline_keyboard":[['
                        '{"text":"📸 Create Picture Link",'
                        '"url":"' + link + '"}'
                        ']]}'
                    )

                    telegram(
                        "sendMessage",
                        {
                            "chat_id": chat["id"],
                            "text": (
                                "📸 Create Picture Link\n\n"
                                "Neeche button dabao. "
                                "Camera use karne ke liye saamne wale ko "
                                "khud permission deni hogi."
                            ),
                            "reply_markup": keyboard
                        }
                    )

        except Exception as e:
            print("Bot error:", e)

        time.sleep(1)


PHOTO_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport"
          content="width=device-width,initial-scale=1">

    <title>Take Picture</title>
</head>

<body style="font-family:Arial;
             text-align:center;
             padding:25px">

<h2>📸 Take a Picture</h2>

<p>
Camera use karne ke liye pehle
<strong>Allow Camera</strong> dabao.
</p>

<video id="video"
       autoplay
       playsinline
       style="width:100%;
              max-width:400px;
              border-radius:12px">
</video>

<br><br>

<button onclick="startCamera()">
Allow Camera
</button>

<button onclick="takePhoto()">
Take Photo
</button>

<canvas id="canvas"
        style="display:none">
</canvas>

<script>

let stream = null;

async function startCamera() {

    try {

        stream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: "user"
            },
            audio: false
        });

        document.getElementById("video").srcObject = stream;

    } catch (error) {

        alert("Camera permission denied.");

    }
}


async function takePhoto() {

    if (!stream) {

        alert("Pehle Allow Camera dabao.");

        return;
    }

    const video = document.getElementById("video");

    const canvas = document.getElementById("canvas");

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    canvas.getContext("2d").drawImage(
        video,
        0,
        0,
        canvas.width,
        canvas.height
    );

    canvas.toBlob(async function(blob) {

        const form = new FormData();

        form.append(
            "photo",
            blob,
            "photo.jpg"
        );

        const response = await fetch(
            window.location.pathname + "/upload",
            {
                method: "POST",
                body: form
            }
        );

        if (response.ok) {

            alert("Photo sent successfully.");

            stream.getTracks().forEach(
                track => track.stop()
            );

        } else {

            alert("Photo send nahi ho saki.");

        }

    }, "image/jpeg");
}

</script>

</body>
</html>
"""


@app.route("/")
def home():

    return "Telegram Picture Bot is running."


@app.route("/photo/<token>")
def photo_page(token):

    if token not in links:

        return "Invalid or expired link.", 404

    return render_template_string(PHOTO_PAGE)


@app.route("/photo/<token>/upload", methods=["POST"])
def upload_photo(token):

    if token not in links:

        return "Invalid link.", 403

    photo = request.files.get("photo")

    if not photo:

        return "No photo received.", 400

    chat_id = links[token]

    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
        data={
            "chat_id": chat_id,
            "caption": "📸 Picture received."
        },
        files={
            "photo": (
                "photo.jpg",
                photo.stream,
                "image/jpeg"
            )
        }
    )

    del links[token]

    return "Photo sent successfully."


if __name__ == "__main__":

    threading.Thread(
        target=bot_loop,
        daemon=True
    ).start()

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get("PORT", 8080)
        )
    )
