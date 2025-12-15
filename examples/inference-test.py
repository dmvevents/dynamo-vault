#!/usr/bin/env python3
"""
Simple inference test client for TensorRT-LLM with Dynamo.

Usage:
    python inference-test.py                              # Default settings
    python inference-test.py --url http://localhost:8000  # Custom URL
    python inference-test.py --prompt "Tell me a joke"    # Custom prompt
"""

import argparse
import json
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def test_inference(
    url: str,
    model: str = "Qwen/Qwen3-0.6B",
    prompt: str = "Hello, how are you?",
    max_tokens: int = 30,
    timeout: int = 60,
) -> dict:
    """Send an inference request and return the response."""

    endpoint = f"{url.rstrip('/')}/v1/completions"

    payload = {
        "model": model,
        "prompt": prompt,
        "max_tokens": max_tokens,
    }

    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    start_time = time.time()
    response = urlopen(request, timeout=timeout)
    elapsed = time.time() - start_time

    result = json.loads(response.read().decode("utf-8"))
    result["_elapsed_time"] = elapsed

    return result


def main():
    parser = argparse.ArgumentParser(description="TensorRT-LLM inference test client")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the inference server",
    )
    parser.add_argument(
        "--model",
        default="Qwen/Qwen3-0.6B",
        help="Model name",
    )
    parser.add_argument(
        "--prompt",
        default="Hello, how are you?",
        help="Prompt text",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=30,
        help="Maximum tokens to generate",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Request timeout in seconds",
    )

    args = parser.parse_args()

    print(f"Testing inference at {args.url}")
    print(f"Model: {args.model}")
    print(f"Prompt: {args.prompt}")
    print(f"Max tokens: {args.max_tokens}")
    print()

    try:
        result = test_inference(
            url=args.url,
            model=args.model,
            prompt=args.prompt,
            max_tokens=args.max_tokens,
            timeout=args.timeout,
        )

        elapsed = result.pop("_elapsed_time", 0)

        print("Response:")
        print(json.dumps(result, indent=2))
        print()
        print(f"Elapsed time: {elapsed:.2f}s")
        print()

        # Extract and display the generated text
        if "choices" in result and len(result["choices"]) > 0:
            text = result["choices"][0].get("text", "")
            print(f"Generated text: {text}")

        print()
        print("SUCCESS: Inference test passed")
        return 0

    except HTTPError as e:
        print(f"HTTP Error: {e.code} {e.reason}")
        try:
            error_body = e.read().decode("utf-8")
            print(f"Response: {error_body}")
        except:
            pass
        return 1

    except URLError as e:
        print(f"Connection Error: {e.reason}")
        print()
        print("Make sure the server is running and accessible.")
        print("You may need to run: kubectl port-forward svc/<service> 8000:8000")
        return 1

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
