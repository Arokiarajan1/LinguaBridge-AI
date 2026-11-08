import os
from pathlib import Path

import requests
from flask import Flask, jsonify, request, send_file

app = Flask(__name__)

HTML_FILE = Path(__file__).parent / "voice_assistant.html"
GEMINI_MODEL = "gemini-3.8-flash"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/"
    f"models/{GEMINI_MODEL}:generateContent"
)


@app.get("/")
def home():
    return send_file(HTML_FILE)


@app.get("/voice_assistant.html")
def voice_page():
    return send_file(HTML_FILE)


@app.post("/chat")
def chat():
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        return jsonify({"error": "AI service is not configured."}), 503

    payload = request.get_json(silent=True) or {}
    prompt = payload.get("prompt", "").strip()

    if not prompt:
        return jsonify({"error": "Prompt is empty."}), 400

    try:
        result = requests.post(
            GEMINI_URL,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key
            },
            json={
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ]
            },
            timeout=90
        )

        result.raise_for_status()
        data = result.json()

        answer = data["candidates"][0]["content"]["parts"][0]["text"]

        return jsonify({"response": answer})

    except requests.exceptions.Timeout:
        return jsonify({"error": "The AI service took too long."}), 504

    except requests.exceptions.RequestException:
        app.logger.exception("Gemini API request failed")
        return jsonify({"error": "AI service connection failed."}), 502

    except (KeyError, IndexError, TypeError, ValueError):
        app.logger.exception("Unexpected Gemini response")
        return jsonify({"error": "Could not read the AI response."}), 502


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
