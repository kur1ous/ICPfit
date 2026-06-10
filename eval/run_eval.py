"""The trust check (habit 3).

Run the pipeline over a hand-labeled set and measure agreement with your own
judgment. This is the single biggest predictor of whether the pipeline is
trustworthy. Run it BEFORE scaling, and again every time you change the prompt
or ICP definition.

Usage:
    python eval/run_eval.py [labels.csv]
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

# Make `icp` importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from icp import pipeline  # noqa: E402


def main(labels_path: str = "eval/labels.csv") -> None:
    with open(labels_path, newline="", encoding="utf-8") as f:
        labeled = [
            (row["domain"].strip(), int(row["human_score"]))
            for row in csv.DictReader(f)
            if row.get("domain", "").strip()
        ]

    if not labeled:
        print("No labeled rows found.")
        return

    print(f"Running pipeline over {len(labeled)} labeled domains...\n")

    pairs: list[tuple[str, int, int, str]] = []  # domain, human, model, reasoning
    for domain, human in labeled:
        try:
            rec = pipeline.enrich_domain(domain)
            pairs.append((domain, human, rec.result.icp_fit_score, rec.result.icp_fit_reasoning))
        except Exception as exc:  # noqa: BLE001
            print(f"  [{domain}] FAILED: {exc}")

    if not pairs:
        print("No results to evaluate.")
        return

    n = len(pairs)
    exact = sum(1 for _, h, m, _ in pairs if h == m)
    within1 = sum(1 for _, h, m, _ in pairs if abs(h - m) <= 1)
    mae = sum(abs(h - m) for _, h, m, _ in pairs) / n

    print("\n=== AGREEMENT ===")
    print(f"  n               : {n}")
    print(f"  exact match     : {exact}/{n} ({100*exact/n:.0f}%)")
    print(f"  within +/- 1    : {within1}/{n} ({100*within1/n:.0f}%)")
    print(f"  mean abs error  : {mae:.2f}")

    print("\n=== CONFUSION (rows=human, cols=model, 1..5) ===")
    matrix = [[0] * 5 for _ in range(5)]
    for _, h, m, _ in pairs:
        if 1 <= h <= 5 and 1 <= m <= 5:
            matrix[h - 1][m - 1] += 1
    print("        m1  m2  m3  m4  m5")
    for i, row in enumerate(matrix, start=1):
        print(f"  h{i} | " + "  ".join(f"{c:2d}" for c in row))

    disagreements = [(d, h, m, r) for d, h, m, r in pairs if h != m]
    if disagreements:
        print(f"\n=== DISAGREEMENTS ({len(disagreements)}) ===")
        for d, h, m, r in sorted(disagreements, key=lambda x: -abs(x[1] - x[2])):
            print(f"\n  {d}: human={h} model={m} (delta {abs(h-m)})")
            print(f"    model reasoning: {r}")
    else:
        print("\nNo disagreements.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "eval/labels.csv")
