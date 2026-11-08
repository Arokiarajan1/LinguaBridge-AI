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


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/chat")
def chat():
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        app.logger.error("GEMINI_API_KEY is missing.")
        return jsonify({"error": "AI service is not configured."}), 503

    payload = request.get_json(silent=True) or {}
    prompt = payload.get("prompt", "")

    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify({"error": "Please enter a message."}), 400

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
                            {"text": prompt.strip()}
                        ]
                    }
                ]
            },
            timeout=90
        )

        # Log Google's error response without exposing your API key.
        if not result.ok:
            app.logger.error(
                "Gemini returned HTTP %s: %s",
                result.status_code,
                result.text[:2000]
            )

            if result.status_code == 401:
                return jsonify({
                    "error": "Gemini rejected the API key. Check the Render environment variable."
                }), 502

            if result.status_code == 403:
                return jsonify({
                    "error": "Gemini access denied. Check API key permissions and project settings."
                }), 502

            if result.status_code == 429:
                return jsonify({
                    "error": "Gemini request limit reached. Check your API quota."
                }), 429

            return jsonify({
                "error": "Gemini API request failed. Check Render logs."
            }), 502

        data = result.json()

        candidates = data.get("candidates", [])

        if not candidates:
            app.logger.error("Gemini returned no candidates: %s", str(data)[:2000])
            return jsonify({
                "error": "Gemini did not return a response. Please try again."
            }), 502

        answer = "".join(
            part.get("text", "")
            for part in candidates[0].get("content", {}).get("parts", [])
        ).strip()

        if not answer:
            app.logger.error("Gemini returned an empty answer.")
            return jsonify({
                "error": "Gemini returned an empty response."
            }), 502

        return jsonify({"response": answer})

    except requests.exceptions.Timeout:
        app.logger.error("Gemini request timed out.")
        return jsonify({
            "error": "The AI service took too long. Please try again."
        }), 504

    except requests.exceptions.RequestException:
        app.logger.exception("Gemini connection failed.")
        return jsonify({
            "error": "Could not connect to the AI service."
        }), 502

    except (ValueError, TypeError, KeyError, IndexError):
        app.logger.exception("Could not process Gemini response.")
        return jsonify({
            "error": "Could not process the AI response."
        }), 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)