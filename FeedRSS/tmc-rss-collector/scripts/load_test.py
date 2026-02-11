"""
Load test for TMC Generation API.

Simulates concurrent requests to /api/generate to verify:
1. Rate limiter returns 429 for excess requests
2. No race conditions on singletons
3. Thread-safe metrics don't corrupt under concurrency
4. Measure p95 latency under load

Usage:
    python scripts/load_test.py --url https://your-api.azurewebsites.net/api
    python scripts/load_test.py --url http://localhost:7071/api --concurrency 5
"""

import argparse
import asyncio
import json
import statistics
import sys
import time
from datetime import datetime

try:
    import aiohttp
except ImportError:
    print("ERROR: aiohttp required. Install with: pip install aiohttp")
    sys.exit(1)


# Minimal valid payload for /api/generate
GENERATE_PAYLOAD = {
    "texto_base": (
        "O presidente Lula anunciou nesta quarta-feira um novo pacote de medidas "
        "economicas para estimular o crescimento do PIB. O ministro da Fazenda, "
        "Fernando Haddad, apresentou detalhes do plano que inclui reducao de "
        "impostos para pequenas empresas e aumento de investimentos em "
        "infraestrutura. Segundo o governo, as medidas devem gerar cerca de "
        "500 mil novos empregos nos proximos 12 meses. Economistas consultados "
        "pelo jornal avaliam que o impacto fiscal sera de aproximadamente R$ 30 "
        "bilhoes. A oposicao criticou a proposta, alegando que os custos superam "
        "os beneficios estimados."
    ),
    "categoria": "economia",
    "tom": "formal",
    "tipo_materia": "destaque",
    "tags": ["economia", "governo", "pib"],
    "skip_enrichment": True,  # Skip Exa calls during load test
    "skip_verification": True,  # Skip verification during load test
}

HEALTH_ENDPOINT = "/health"
METRICS_ENDPOINT = "/metrics"
GENERATE_ENDPOINT = "/generate"


class LoadTestResult:
    def __init__(self):
        self.successes = 0
        self.rate_limited = 0
        self.errors = 0
        self.latencies_ms = []
        self.status_codes = {}
        self.error_messages = []

    def record(self, status_code: int, latency_ms: float, error_msg: str = None):
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
        self.latencies_ms.append(latency_ms)
        if status_code == 200:
            self.successes += 1
        elif status_code == 429:
            self.rate_limited += 1
        else:
            self.errors += 1
            if error_msg:
                self.error_messages.append(error_msg)

    def summary(self) -> dict:
        latencies = sorted(self.latencies_ms)
        n = len(latencies)
        return {
            "total_requests": n,
            "successes": self.successes,
            "rate_limited_429": self.rate_limited,
            "errors": self.errors,
            "status_codes": self.status_codes,
            "latency_ms": {
                "min": round(latencies[0], 1) if latencies else 0,
                "max": round(latencies[-1], 1) if latencies else 0,
                "avg": round(statistics.mean(latencies), 1) if latencies else 0,
                "p50": round(latencies[n // 2], 1) if n > 0 else 0,
                "p95": round(latencies[int(n * 0.95)], 1) if n >= 20 else (round(latencies[-1], 1) if latencies else 0),
                "p99": round(latencies[int(n * 0.99)], 1) if n >= 100 else (round(latencies[-1], 1) if latencies else 0),
            },
            "error_messages": self.error_messages[:5],
        }


async def check_health(session: aiohttp.ClientSession, base_url: str) -> bool:
    """Check API health before starting load test."""
    try:
        async with session.get(f"{base_url}{HEALTH_ENDPOINT}", timeout=aiohttp.ClientTimeout(total=10)) as resp:
            data = await resp.json()
            status = data.get("status", "unknown")
            print(f"  Health: {status} (DB: {data.get('database')}, LLM: {data.get('llm_service')}, Exa: {data.get('exa_enrichment')})")
            return status != "unhealthy"
    except Exception as e:
        print(f"  Health check failed: {e}")
        return False


async def get_metrics(session: aiohttp.ClientSession, base_url: str, label: str) -> dict:
    """Fetch current metrics snapshot."""
    try:
        async with session.get(f"{base_url}{METRICS_ENDPOINT}", timeout=aiohttp.ClientTimeout(total=10)) as resp:
            data = await resp.json()
            print(f"  Metrics ({label}): uptime={data.get('uptime_seconds')}s, counters={data.get('counters', {})}")
            return data
    except Exception as e:
        print(f"  Metrics fetch failed ({label}): {e}")
        return {}


async def send_generate_request(
    session: aiohttp.ClientSession,
    base_url: str,
    request_id: int,
    result: LoadTestResult,
):
    """Send a single /api/generate request and record results."""
    start = time.time()
    try:
        async with session.post(
            f"{base_url}{GENERATE_ENDPOINT}",
            json=GENERATE_PAYLOAD,
            timeout=aiohttp.ClientTimeout(total=120),
        ) as resp:
            latency_ms = (time.time() - start) * 1000
            body = await resp.text()
            error_msg = None
            if resp.status != 200:
                try:
                    error_msg = json.loads(body).get("error", body[:200])
                except Exception:
                    error_msg = body[:200]
            result.record(resp.status, latency_ms, error_msg)
            status_label = "OK" if resp.status == 200 else f"HTTP {resp.status}"
            print(f"  [req-{request_id:02d}] {status_label} in {latency_ms:.0f}ms")
    except asyncio.TimeoutError:
        latency_ms = (time.time() - start) * 1000
        result.record(504, latency_ms, "Timeout after 120s")
        print(f"  [req-{request_id:02d}] TIMEOUT in {latency_ms:.0f}ms")
    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        result.record(0, latency_ms, str(e))
        print(f"  [req-{request_id:02d}] ERROR: {e}")


async def run_load_test(base_url: str, concurrency: int, total_requests: int):
    """Run the full load test suite."""
    print(f"\n{'='*60}")
    print(f"TMC Generation API Load Test")
    print(f"{'='*60}")
    print(f"  Target:      {base_url}")
    print(f"  Concurrency: {concurrency}")
    print(f"  Total:       {total_requests} requests")
    print(f"  Started:     {datetime.now().isoformat()}")
    print()

    async with aiohttp.ClientSession() as session:
        # Step 1: Health check
        print("[1/5] Health Check")
        healthy = await check_health(session, base_url)
        if not healthy:
            print("  WARNING: API is unhealthy. Proceeding anyway for diagnostic purposes.")
        print()

        # Step 2: Pre-test metrics
        print("[2/5] Pre-Test Metrics")
        metrics_before = await get_metrics(session, base_url, "before")
        print()

        # Step 3: Concurrent load test
        print(f"[3/5] Sending {total_requests} concurrent requests (max {concurrency} at a time)")
        result = LoadTestResult()
        semaphore = asyncio.Semaphore(concurrency)

        async def limited_request(req_id):
            async with semaphore:
                await send_generate_request(session, base_url, req_id, result)

        test_start = time.time()
        tasks = [limited_request(i + 1) for i in range(total_requests)]
        await asyncio.gather(*tasks)
        test_duration = time.time() - test_start
        print()

        # Step 4: Post-test metrics
        print("[4/5] Post-Test Metrics")
        metrics_after = await get_metrics(session, base_url, "after")
        print()

        # Step 5: Results
        print(f"[5/5] Results")
        summary = result.summary()
        summary["test_duration_seconds"] = round(test_duration, 1)
        summary["requests_per_second"] = round(total_requests / test_duration, 2) if test_duration > 0 else 0

        print(f"\n{'='*60}")
        print("LOAD TEST RESULTS")
        print(f"{'='*60}")
        print(f"  Duration:        {summary['test_duration_seconds']}s")
        print(f"  Throughput:      {summary['requests_per_second']} req/s")
        print(f"  Total requests:  {summary['total_requests']}")
        print(f"  Successes:       {summary['successes']}")
        print(f"  Rate limited:    {summary['rate_limited_429']}")
        print(f"  Errors:          {summary['errors']}")
        print(f"  Status codes:    {summary['status_codes']}")
        print()
        print("  Latency (ms):")
        for k, v in summary["latency_ms"].items():
            print(f"    {k:>4}: {v}ms")
        print()

        # Validation checks
        print("VALIDATION")
        print("-" * 40)

        # Check 1: Rate limiter works
        if concurrency > 3:
            if summary["rate_limited_429"] > 0:
                print("  [PASS] Rate limiter returned 429 for excess requests")
            else:
                print("  [WARN] No 429s seen - rate limiter may not be working")
        else:
            print("  [SKIP] Concurrency too low to test rate limiting (need >3)")

        # Check 2: No server errors
        server_errors = sum(v for k, v in summary["status_codes"].items() if k >= 500)
        if server_errors == 0:
            print("  [PASS] No 5xx server errors (singletons/thread-safety OK)")
        else:
            print(f"  [FAIL] {server_errors} server errors detected")

        # Check 3: p95 latency
        p95 = summary["latency_ms"]["p95"]
        if p95 < 60000:
            print(f"  [PASS] p95 latency {p95}ms < 60000ms threshold")
        else:
            print(f"  [WARN] p95 latency {p95}ms exceeds 60000ms threshold")

        # Check 4: At least some successes
        if summary["successes"] > 0:
            print(f"  [PASS] {summary['successes']} successful generations")
        elif summary["rate_limited_429"] == summary["total_requests"]:
            print("  [PASS] All requests rate limited (expected at high concurrency)")
        else:
            print("  [FAIL] No successful generations")

        print()

        # Metrics diff
        if metrics_before and metrics_after:
            gen_before = metrics_before.get("counters", {}).get("generation.blocked", 0)
            gen_after = metrics_after.get("counters", {}).get("generation.blocked", 0)
            ver_before = metrics_before.get("counters", {}).get("verification.failures", 0)
            ver_after = metrics_after.get("counters", {}).get("verification.failures", 0)
            print("METRICS DIFF")
            print("-" * 40)
            print(f"  generation.blocked: {gen_before} -> {gen_after} (+{gen_after - gen_before})")
            print(f"  verification.failures: {ver_before} -> {ver_after} (+{ver_after - ver_before})")
            gen_stats = metrics_after.get("histograms", {}).get("generation.total_ms")
            if gen_stats:
                print(f"  generation.total_ms: avg={gen_stats.get('avg', 0):.0f}ms p95={gen_stats.get('p95', 0):.0f}ms")

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"scripts/load_test_results_{timestamp}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "test_config": {
                    "base_url": base_url,
                    "concurrency": concurrency,
                    "total_requests": total_requests,
                    "timestamp": datetime.now().isoformat(),
                    "skip_enrichment": True,
                    "skip_verification": True,
                },
                "results": summary,
                "metrics_before": metrics_before,
                "metrics_after": metrics_after,
            }, f, indent=2)
        print(f"\nResults saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="TMC Generation API Load Test")
    parser.add_argument("--url", required=True, help="Base API URL (e.g. http://localhost:7071/api)")
    parser.add_argument("--concurrency", type=int, default=5, help="Max concurrent requests (default: 5)")
    parser.add_argument("--total", type=int, default=10, help="Total requests to send (default: 10)")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    asyncio.run(run_load_test(base_url, args.concurrency, args.total))


if __name__ == "__main__":
    main()
