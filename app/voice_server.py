from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import json
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:1.5b"
HTML_FILE = Path(__file__).parent / "voice_assistant.html"


class VoiceHandler(BaseHTTPRequestHandler):

    def send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path not in ("/", "/voice_assistant.html"):
            self.send_error(404)
            return

        try:
            html = HTML_FILE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
        except OSError as error:
            self.send_error(500, str(error))

    def do_POST(self):
        if self.path != "/chat":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            prompt = payload.get("prompt", "").strip()

            if not prompt:
                self.send_json(400, {"error": "Prompt is empty"})
                return

            result = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL_NAME,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120
            )

            result.raise_for_status()
            answer = result.json().get("response", "")
            self.send_json(200, {"response": answer})

        except requests.exceptions.RequestException as error:
            self.send_json(500, {"error": f"Ollama connection failed: {error}"})
        except (ValueError, KeyError) as error:
            self.send_json(400, {"error": f"Invalid request: {error}"})


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8000), VoiceHandler)
    print("LinguaBridge AI is running at http://localhost:8000")
    print("Keep this PowerShell window open.")
    server.serve_forever()
