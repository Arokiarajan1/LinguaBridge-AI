
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:1.5b"


def generate_response(prompt: str) -> str:
    """Generate AI responses using local Ollama."""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )

        response.raise_for_status()

        result = response.json()
        return result.get("response", "")

    except requests.exceptions.ConnectionError:
        return "Error: Ollama is not running."

    except requests.exceptions.Timeout:
        return "Error: Request timed out."

    except requests.exceptions.RequestException as error:
        return f"Ollama API error: {error}"
