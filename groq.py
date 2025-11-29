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
def stream_llm_response(system_prompt: str, max_tokens: int = 512, temperature: float = 0.1):
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

    print("[GROQ] Sending streaming request...")
    with requests.post(GROQ_COMPLETION_URL, headers=headers, json=payload, stream=True) as response:
        print(f"[GROQ] Response status: {response.status_code}")
        if response.status_code != 200:
            error_text = response.text
            print(f"[GROQ ERROR] Status {response.status_code}: {error_text}")
            raise RuntimeError(f"Groq Error {response.status_code}: {error_text}")
        
        print("[GROQ] Starting to read streaming lines...")
        line_count = 0
        for line in response.iter_lines(decode_unicode=False):
            line_count += 1
            if line:
                # OpenAI-style streaming: lines start with 'data: '
                if line.startswith(b'data: '):
                    data = line[len(b'data: '):]
                    if data == b'[DONE]':
                        print("[GROQ] Received [DONE] signal")
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"].get("content", "")
                        if delta:
                            print(f"[GROQ] Yielding delta: {repr(delta)}")
                            yield delta
                        else:
                            print(f"[GROQ] Empty delta in chunk: {chunk}")
                    except Exception as parse_err:
                        print(f"[GROQ] JSON parse error on line {line_count}: {parse_err}")
                        print(f"[GROQ] Raw line: {line}")
                        continue
        print(f"[GROQ] Finished reading {line_count} lines")

