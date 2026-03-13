"""Quick end-to-end test of Anthropic API with both Haiku and Sonnet models."""

import httpx
import json
import re
import sys
import time

# Force UTF-8 output on Windows
sys.stdout.reconfigure(encoding="utf-8")

API_KEY = "REDACTED_USE_ENV_VAR"
BASE_URL = "https://api.anthropic.com/v1/messages"

HEADERS = {
    "x-api-key": API_KEY,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json",
}


def extract_json(text: str) -> dict:
    """Extract JSON from text, handling markdown code fences."""
    # Try raw first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting from code fences
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1).strip())
    raise json.JSONDecodeError("No JSON found", text, 0)


def test_haiku_classification():
    print("=" * 60)
    print("TEST 1: Claude Haiku 4.5 - Classification Task")
    print("=" * 60)

    payload = {
        "model": "claude-haiku-4-5",
        "max_tokens": 256,
        "messages": [
            {
                "role": "user",
                "content": (
                    'Classify this article title into one of these categories: '
                    'politica, economia, tecnologia, esportes, saude, cultura.\n\n'
                    'Title: "Banco Central eleva taxa Selic para 14,25% ao ano"\n\n'
                    'Return ONLY valid JSON: {"category": "...", "confidence": 0.0-1.0}'
                ),
            }
        ],
    }

    start = time.time()
    with httpx.Client(timeout=30) as client:
        resp = client.post(BASE_URL, headers=HEADERS, json=payload)
    elapsed = time.time() - start

    print(f"Model:        claude-haiku-4-5")
    print(f"Status:       {resp.status_code}")

    if resp.status_code == 200:
        data = resp.json()
        text = data["content"][0]["text"]
        usage = data.get("usage", {})
        print(f"Response:     {text[:200]}")
        print(f"Input tkns:   {usage.get('input_tokens', '?')}")
        print(f"Output tkns:  {usage.get('output_tokens', '?')}")
        print(f"Latency:      {elapsed:.2f}s")

        # Test JSON parsing (with code fence extraction)
        try:
            parsed = extract_json(text)
            print(f"JSON parse:   OK -> {parsed}")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"JSON parse:   FAILED -> {e}")
    else:
        print(f"ERROR:        {resp.text[:500]}")

    print()


def test_sonnet_generation():
    print("=" * 60)
    print("TEST 2: Claude Sonnet 4.5 - Generation Task (PT-BR)")
    print("=" * 60)

    payload = {
        "model": "claude-sonnet-4-5",
        "max_tokens": 256,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Escreva um resumo jornalistico de 2 frases em portugues brasileiro "
                    "sobre o seguinte tema: O impacto da inteligencia artificial no "
                    "jornalismo brasileiro em 2026. Seja conciso e factual."
                ),
            }
        ],
    }

    start = time.time()
    with httpx.Client(timeout=30) as client:
        resp = client.post(BASE_URL, headers=HEADERS, json=payload)
    elapsed = time.time() - start

    print(f"Model:        claude-sonnet-4-5")
    print(f"Status:       {resp.status_code}")

    if resp.status_code == 200:
        data = resp.json()
        text = data["content"][0]["text"]
        usage = data.get("usage", {})
        print(f"Response:     {text[:200]}")
        print(f"Input tkns:   {usage.get('input_tokens', '?')}")
        print(f"Output tkns:  {usage.get('output_tokens', '?')}")
        print(f"Latency:      {elapsed:.2f}s")
    else:
        print(f"ERROR:        {resp.text[:500]}")

    print()


if __name__ == "__main__":
    print("\nTMC Anthropic API End-to-End Test")
    print(f"Endpoint: {BASE_URL}\n")
    test_haiku_classification()
    test_sonnet_generation()
    print("Done.")
