"""
Quick test: validate a Vertex AI API key can call Claude via Google Cloud.

Usage:
    python scripts/test_vertex_ai.py <API_KEY>
    # or set VERTEX_AI_API_KEY env var
"""

import asyncio
import os
import sys
import httpx

# Vertex AI config
PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "tmc-redacao")
REGION = os.environ.get("GCP_REGION", "southamerica-east1")
MODEL = "claude-sonnet-4-5"


async def test_vertex_key(api_key: str):
    """Test Vertex AI Anthropic endpoint with the given API key."""

    # Vertex AI Model Garden endpoint for Anthropic models
    endpoint = (
        f"https://{REGION}-aiplatform.googleapis.com/v1/"
        f"projects/{PROJECT_ID}/locations/{REGION}/"
        f"publishers/anthropic/models/{MODEL}:rawPredict"
    )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload = {
        "anthropic_version": "vertex-2023-10-16",
        "max_tokens": 100,
        "messages": [
            {"role": "user", "content": "Responda apenas: 'Vertex AI OK'. Nada mais."}
        ],
    }

    print(f"Endpoint: {endpoint}")
    print(f"Model:    {MODEL}")
    print(f"Project:  {PROJECT_ID}")
    print(f"Region:   {REGION}")
    print(f"Key:      {api_key[:8]}...{api_key[-4:]}")
    print()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(endpoint, json=payload, headers=headers)
            print(f"Status: {resp.status_code}")

            if resp.status_code == 200:
                data = resp.json()
                text = data.get("content", [{}])[0].get("text", "")
                model_used = data.get("model", "?")
                usage = data.get("usage", {})
                print(f"Model:  {model_used}")
                print(f"Usage:  in={usage.get('input_tokens', '?')} out={usage.get('output_tokens', '?')}")
                print(f"Reply:  {text}")
                print("\n*** SUCCESS - Vertex AI key is working! ***")
                return True
            else:
                print(f"Error body: {resp.text}")

                # Try alternative: API key as query param instead of Bearer
                if resp.status_code in (401, 403):
                    print("\n--- Trying API key as query parameter ---")
                    endpoint_with_key = f"{endpoint}?key={api_key}"
                    headers_no_auth = {"Content-Type": "application/json"}
                    resp2 = await client.post(endpoint_with_key, json=payload, headers=headers_no_auth)
                    print(f"Status: {resp2.status_code}")
                    if resp2.status_code == 200:
                        data = resp2.json()
                        text = data.get("content", [{}])[0].get("text", "")
                        print(f"Reply: {text}")
                        print("\n*** SUCCESS (via query param) - Key works! ***")
                        return True
                    else:
                        print(f"Error body: {resp2.text}")

                # Try streamRawPredict
                if resp.status_code in (400, 404):
                    print("\n--- Trying streamRawPredict endpoint ---")
                    stream_endpoint = endpoint.replace(":rawPredict", ":streamRawPredict")
                    resp3 = await client.post(stream_endpoint, json=payload, headers=headers)
                    print(f"Status: {resp3.status_code}")
                    if resp3.status_code == 200:
                        print(f"Reply: {resp3.text[:500]}")
                        print("\n*** SUCCESS (stream endpoint) ***")
                        return True
                    else:
                        print(f"Error: {resp3.text[:500]}")

                print("\n*** FAILED - Key did not work ***")
                return False

        except httpx.ConnectError as e:
            print(f"Connection error: {e}")
            return False
        except Exception as e:
            print(f"Error: {type(e).__name__}: {e}")
            return False


if __name__ == "__main__":
    key = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("VERTEX_AI_API_KEY", "")
    if not key:
        print("Usage: python scripts/test_vertex_ai.py <API_KEY>")
        print("   or: set VERTEX_AI_API_KEY env var")
        sys.exit(1)

    ok = asyncio.run(test_vertex_key(key))
    sys.exit(0 if ok else 1)
