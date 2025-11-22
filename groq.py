import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()  # Loads GROQ_API_KEY if stored in .env
GROQ_API_KEY = os.getenv("GROQ_API_KEY", None)
GROQ_COMPLETION_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "openai/gpt-oss-20b"  # Example model — swap with yours


def generate_llm_response(system_prompt: str, max_tokens: int = 512, temperature: float = 0.1):
    if not GROQ_API_KEY:
        raise RuntimeError("❌ GROQ_API_KEY not set in environment variables.")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": system_prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    # Send request
    response = requests.post(GROQ_COMPLETION_URL, headers=headers, json=payload)

    if response.status_code != 200:
        raise RuntimeError(f"Groq Error {response.status_code}: {response.text}")

    data = response.json()
    return data["choices"][0]["message"]["content"]

# Streaming version for FastAPI endpoints
def stream_llm_response(system_prompt: str, max_tokens: int = 80, temperature: float = 0.1):
    if not GROQ_API_KEY:
        raise RuntimeError("❌ GROQ_API_KEY not set in environment variables.")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": system_prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True
    }

    with requests.post(GROQ_COMPLETION_URL, headers=headers, json=payload, stream=True) as response:
        if response.status_code != 200:
            raise RuntimeError(f"Groq Error {response.status_code}: {response.text}")
        for line in response.iter_lines():
            if line:
                # OpenAI-style streaming: lines start with 'data: '
                if line.startswith(b'data: '):
                    data = line[len(b'data: '):]
                    if data == b'[DONE]':
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"].get("content", "")
                        if delta:
                            yield delta
                    except Exception:
                        continue

