import httpx
from dotenv import load_dotenv
import os

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "60.0"))


class OllamaUnavailableError(Exception):
    pass


def call_ollama(messages: list[dict]) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }
    try:
        with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
            resp = client.post(
    f"{OLLAMA_BASE_URL}/api/chat",
    json=payload,
    timeout=120.0        # 2 minutes — generous for a 3B model on CPU
)
    except httpx.ConnectError:
        raise OllamaUnavailableError(
            "Cannot reach Ollama at localhost:11434. Is it running?"
        )

    if resp.status_code == 404:
        return (
            f"Model '{OLLAMA_MODEL}' not found. "
            f"Run: ollama pull {OLLAMA_MODEL}"
        )
    if resp.status_code != 200:
        return f"Ollama returned an error (HTTP {resp.status_code}). Please try again."

    data = resp.json()
    return data.get("message", {}).get("content", "").strip()
