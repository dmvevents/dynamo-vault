#!/usr/bin/env python3
"""
Simple benchmark for TensorRT-LLM inference throughput.

Usage:
    python benchmark.py                              # Default settings
    python benchmark.py --requests 100               # 100 requests
    python benchmark.py --concurrent 4               # 4 concurrent requests
"""

import argparse
import json
import sys
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def send_request(
    url: str,
    model: str,
    prompt: str,
    max_tokens: int,
    timeout: int,
) -> dict:
    """Send a single inference request."""

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

    # Count output tokens
    output_tokens = 0
    if "choices" in result and len(result["choices"]) > 0:
        text = result["choices"][0].get("text", "")
        output_tokens = len(text.split())  # Approximate

    return {
        "elapsed": elapsed,
        "output_tokens": output_tokens,
        "success": True,
    }


def run_benchmark(
    url: str,
    model: str,
    prompt: str,
    max_tokens: int,
    num_requests: int,
    concurrent: int,
    timeout: int,
) -> dict:
    """Run the benchmark."""

    results = []
    errors = 0

    print(f"Running {num_requests} requests with {concurrent} concurrent...")
    print()

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=concurrent) as executor:
        futures = [
            executor.submit(send_request, url, model, prompt, max_tokens, timeout)
            for _ in range(num_requests)
        ]

        for i, future in enumerate(as_completed(futures), 1):
            try:
                result = future.result()
                results.append(result)
                if i % 10 == 0:
                    print(f"  Completed {i}/{num_requests}")
            except Exception as e:
                errors += 1
                print(f"  Request {i} failed: {e}")

    total_time = time.time() - start_time

    # Calculate statistics
    if results:
        latencies = [r["elapsed"] for r in results]
        tokens = [r["output_tokens"] for r in results]

        stats = {
            "total_requests": num_requests,
            "successful_requests": len(results),
            "failed_requests": errors,
            "total_time_seconds": total_time,
            "requests_per_second": len(results) / total_time if total_time > 0 else 0,
            "latency": {
                "min": min(latencies),
                "max": max(latencies),
                "mean": statistics.mean(latencies),
                "median": statistics.median(latencies),
                "p95": sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) >= 20 else max(latencies),
            },
            "output_tokens": {
                "total": sum(tokens),
                "mean": statistics.mean(tokens) if tokens else 0,
            },
        }
    else:
        stats = {
            "total_requests": num_requests,
            "successful_requests": 0,
            "failed_requests": errors,
            "total_time_seconds": total_time,
            "error": "All requests failed",
        }

    return stats


def main():
    parser = argparse.ArgumentParser(description="TensorRT-LLM inference benchmark")
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
        default="Write a short story about",
        help="Prompt text",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=50,
        help="Maximum tokens to generate",
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=20,
        help="Number of requests to send",
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        default=2,
        help="Number of concurrent requests",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Request timeout in seconds",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("TensorRT-LLM Inference Benchmark")
    print("=" * 60)
    print(f"URL: {args.url}")
    print(f"Model: {args.model}")
    print(f"Requests: {args.requests}")
    print(f"Concurrent: {args.concurrent}")
    print(f"Max tokens: {args.max_tokens}")
    print()

    try:
        stats = run_benchmark(
            url=args.url,
            model=args.model,
            prompt=args.prompt,
            max_tokens=args.max_tokens,
            num_requests=args.requests,
            concurrent=args.concurrent,
            timeout=args.timeout,
        )

        print()
        print("=" * 60)
        print("Results")
        print("=" * 60)
        print(json.dumps(stats, indent=2))
        print()

        if stats.get("successful_requests", 0) > 0:
            print(f"Throughput: {stats['requests_per_second']:.2f} req/s")
            print(f"Mean latency: {stats['latency']['mean']:.3f}s")
            print(f"P95 latency: {stats['latency']['p95']:.3f}s")
            return 0
        else:
            print("FAILED: No successful requests")
            return 1

    except Exception as e:
        print(f"Benchmark failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
