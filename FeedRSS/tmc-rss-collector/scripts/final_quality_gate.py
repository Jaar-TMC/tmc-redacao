"""
Final Quality Gate — Go/No-Go Decision

Runs audit_generation_v5.py --synthetic --repeat 3 and evaluates
results against production launch criteria.

Usage:
    python scripts/final_quality_gate.py

Requires:
    - ANTHROPIC_API_KEY or AZURE_AI_API_KEY
    - EXA_API_KEY (for enrichment)
    - SQL_SERVER, SQL_DATABASE, SQL_USERNAME, SQL_PASSWORD

Go/No-Go Criteria:
    | Metric            | Minimum  | Target  | Hard Block  |
    |-------------------|----------|---------|-------------|
    | Fabrication Rate  | <1%      | <0.5%   | >2% blocks  |
    | Avg Confidence    | >0.65    | >0.75   | <0.55 blocks|
    | Flesch Score      | >50      | >60     | <40 blocks  |
    | SEO Score         | >60      | >75     | <50 blocks  |
    | StdDev (SEO)      | <8       | <5      | >10 blocks  |
    | False Block Rate  | <5%      | <2%     | >10% blocks |
"""

import json
import os
import statistics
import subprocess
import sys
from datetime import datetime


# Go/No-Go thresholds
CRITERIA = {
    "fabrication_rate": {"min": 1.0, "target": 0.5, "hard_block": 2.0, "direction": "lower_is_better"},
    "avg_confidence": {"min": 0.65, "target": 0.75, "hard_block": 0.55, "direction": "higher_is_better"},
    "avg_flesch": {"min": 50.0, "target": 60.0, "hard_block": 40.0, "direction": "higher_is_better"},
    "avg_seo": {"min": 60.0, "target": 75.0, "hard_block": 50.0, "direction": "higher_is_better"},
    "stddev_seo": {"min": 8.0, "target": 5.0, "hard_block": 10.0, "direction": "lower_is_better"},
    "false_block_rate": {"min": 5.0, "target": 2.0, "hard_block": 10.0, "direction": "lower_is_better"},
}


def evaluate_metric(name: str, value: float) -> dict:
    """Evaluate a single metric against criteria."""
    c = CRITERIA[name]
    lower = c["direction"] == "lower_is_better"

    if lower:
        if value > c["hard_block"]:
            status = "HARD_BLOCK"
        elif value > c["min"]:
            status = "BELOW_MIN"
        elif value > c["target"]:
            status = "ACCEPTABLE"
        else:
            status = "TARGET_MET"
    else:
        if value < c["hard_block"]:
            status = "HARD_BLOCK"
        elif value < c["min"]:
            status = "BELOW_MIN"
        elif value < c["target"]:
            status = "ACCEPTABLE"
        else:
            status = "TARGET_MET"

    return {
        "name": name,
        "value": round(value, 3),
        "status": status,
        "target": c["target"],
        "minimum": c["min"],
        "hard_block": c["hard_block"],
    }


def run_audit(run_number: int) -> dict:
    """Run a single audit_generation_v5.py --synthetic execution."""
    print(f"\n  --- Run {run_number} ---")
    try:
        result = subprocess.run(
            [sys.executable, "scripts/audit_generation_v5.py", "--synthetic"],
            capture_output=True,
            text=True,
            timeout=600,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        if result.returncode != 0:
            print(f"  WARNING: audit exited with code {result.returncode}")
            print(f"  stderr: {result.stderr[:500]}")

        # Parse the JSON output (last line or saved file)
        output = result.stdout.strip()

        # Try to find JSON in output
        json_start = output.rfind("{")
        if json_start >= 0:
            json_str = output[json_start:]
            return json.loads(json_str)

        # Try to find the most recent results file
        import glob
        files = sorted(glob.glob("scripts/audit_v5_results_*.json"))
        if files:
            with open(files[-1], "r", encoding="utf-8") as f:
                return json.load(f)

        print(f"  ERROR: Could not parse audit output")
        return None

    except subprocess.TimeoutExpired:
        print(f"  ERROR: Audit timed out after 600s")
        return None
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def main():
    print("=" * 60)
    print("TMC Final Quality Gate — Go/No-Go Decision")
    print("=" * 60)
    print(f"  Timestamp: {datetime.now().isoformat()}")
    print(f"  Runs: 3 (for consistency)")
    print()

    # Step 1: Run pytest
    print("[1/3] Running test suite...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=line"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        test_output = result.stdout.strip().split("\n")[-1]
        print(f"  Result: {test_output}")
        tests_pass = result.returncode == 0
        if not tests_pass:
            print("  HARD BLOCK: Test suite has failures")
            print(result.stdout[-500:])
    except Exception as e:
        print(f"  ERROR: Could not run tests: {e}")
        tests_pass = False

    print()

    # Step 2: Run 3 synthetic audits
    print("[2/3] Running synthetic quality audits (3 runs)...")
    runs = []
    for i in range(3):
        audit_result = run_audit(i + 1)
        if audit_result:
            runs.append(audit_result)
            # Print key metrics
            summary = audit_result.get("summary", audit_result)
            print(f"    Confidence: {summary.get('avg_confidence', '?')}")
            print(f"    SEO: {summary.get('avg_seo_score', '?')}")
            print(f"    Fabricated: {summary.get('total_fabricated', '?')}")
            print(f"    Flesch: {summary.get('avg_flesch', '?')}")
        else:
            print(f"    Run {i+1} failed — skipping")

    if len(runs) < 2:
        print("\n  HARD BLOCK: Not enough successful audit runs (need at least 2)")
        sys.exit(1)

    print()

    # Step 3: Aggregate metrics across runs
    print("[3/3] Evaluating go/no-go criteria...")
    print()

    # Extract metrics from runs
    all_confidence = []
    all_seo = []
    all_flesch = []
    all_fabricated = []
    all_total = []
    all_blocked = []

    for r in runs:
        s = r.get("summary", r)
        if "avg_confidence" in s:
            all_confidence.append(s["avg_confidence"])
        if "avg_seo_score" in s:
            all_seo.append(s["avg_seo_score"])
        if "avg_flesch" in s:
            all_flesch.append(s["avg_flesch"])
        all_fabricated.append(s.get("total_fabricated", 0))
        all_total.append(s.get("total_articles", s.get("total_tested", 10)))
        all_blocked.append(s.get("total_blocked", 0))

    # Calculate aggregated metrics
    total_articles = sum(all_total) if all_total else 1
    total_fabricated = sum(all_fabricated)
    total_blocked = sum(all_blocked)

    metrics = {}
    if all_confidence:
        metrics["avg_confidence"] = statistics.mean(all_confidence)
    if all_seo:
        metrics["avg_seo"] = statistics.mean(all_seo)
        metrics["stddev_seo"] = statistics.stdev(all_seo) if len(all_seo) > 1 else 0
    if all_flesch:
        metrics["avg_flesch"] = statistics.mean(all_flesch)
    metrics["fabrication_rate"] = (total_fabricated / total_articles * 100) if total_articles else 0
    # False block rate: articles blocked that had 0 fabrications
    # Approximation: blocked articles / total * 100 (conservative)
    metrics["false_block_rate"] = (total_blocked / total_articles * 100) if total_articles else 0

    # Evaluate each metric
    evaluations = []
    hard_blocks = []
    below_min = []
    targets_met = []

    for metric_name, value in metrics.items():
        if metric_name in CRITERIA:
            ev = evaluate_metric(metric_name, value)
            evaluations.append(ev)
            if ev["status"] == "HARD_BLOCK":
                hard_blocks.append(ev)
            elif ev["status"] == "BELOW_MIN":
                below_min.append(ev)
            elif ev["status"] == "TARGET_MET":
                targets_met.append(ev)

    # Print results table
    print(f"{'Metric':<20} {'Value':>8} {'Status':<12} {'Target':>8} {'Min':>8} {'Block':>8}")
    print("-" * 72)
    for ev in evaluations:
        status_icon = {
            "TARGET_MET": "PASS",
            "ACCEPTABLE": "OK",
            "BELOW_MIN": "WARN",
            "HARD_BLOCK": "BLOCK",
        }.get(ev["status"], "?")
        print(
            f"{ev['name']:<20} {ev['value']:>8.2f} {status_icon:<12} "
            f"{ev['target']:>8.2f} {ev['minimum']:>8.2f} {ev['hard_block']:>8.2f}"
        )

    print()
    print("=" * 60)

    # Final decision
    if not tests_pass:
        print("DECISION: NO-GO")
        print("  Reason: Test suite has failures")
        decision = "NO-GO"
    elif hard_blocks:
        print("DECISION: NO-GO")
        print(f"  Hard blocks: {', '.join(e['name'] for e in hard_blocks)}")
        decision = "NO-GO"
    elif below_min:
        print("DECISION: CONDITIONAL GO")
        print(f"  Below minimum: {', '.join(e['name'] for e in below_min)}")
        print("  These metrics should be improved before full production launch.")
        decision = "CONDITIONAL"
    else:
        print("DECISION: GO")
        print(f"  All {len(evaluations)} metrics meet minimum criteria.")
        print(f"  {len(targets_met)}/{len(evaluations)} metrics meet target.")
        decision = "GO"

    print("=" * 60)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = {
        "timestamp": datetime.now().isoformat(),
        "decision": decision,
        "tests_pass": tests_pass,
        "runs_completed": len(runs),
        "metrics": metrics,
        "evaluations": evaluations,
        "hard_blocks": [e["name"] for e in hard_blocks],
        "below_minimum": [e["name"] for e in below_min],
        "targets_met": [e["name"] for e in targets_met],
    }
    output_file = f"scripts/quality_gate_results_{timestamp}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to: {output_file}")

    sys.exit(0 if decision == "GO" else 1)


if __name__ == "__main__":
    main()
