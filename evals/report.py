#!/usr/bin/env python3
"""Compare two scored Craxis eval reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

EVALS_DIR = Path(__file__).resolve().parent
REPORTS_DIR = EVALS_DIR / "reports"


def load_report(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def delta(baseline: float | None, candidate: float | None) -> float | None:
    if baseline is None or candidate is None:
        return None
    return round(candidate - baseline, 4)


def compare_reports(base: dict[str, Any], cand: dict[str, Any]) -> dict[str, Any]:
    base_summary = base.get("summary", {}).get("metrics", {})
    cand_summary = cand.get("summary", {}).get("metrics", {})

    metric_deltas = {}
    for key in sorted(set(base_summary) | set(cand_summary)):
        metric_deltas[key] = delta(base_summary.get(key), cand_summary.get(key))

    base_by_id = {row["id"]: row for row in base.get("case_scores", [])}
    cand_by_id = {row["id"]: row for row in cand.get("case_scores", [])}

    regressions = []
    improvements = []

    for case_id in sorted(set(base_by_id) & set(cand_by_id)):
        base_row = base_by_id[case_id]
        cand_row = cand_by_id[case_id]
        task = base_row.get("task", "unknown")

        score_keys = [
            k
            for k in set(base_row) | set(cand_row)
            if k not in {"id", "task"} and isinstance(base_row.get(k), (bool, int, float))
        ]

        better = 0
        worse = 0
        for key in score_keys:
            base_val = float(base_row.get(key, 0))
            cand_val = float(cand_row.get(key, 0))
            if key == "hallucination":
                if cand_val > base_val:
                    worse += 1
                elif cand_val < base_val:
                    better += 1
            elif cand_val > base_val:
                better += 1
            elif cand_val < base_val:
                worse += 1

        if worse > better:
            regressions.append({"id": case_id, "task": task, "better": better, "worse": worse})
        elif better > worse:
            improvements.append({"id": case_id, "task": task, "better": better, "worse": worse})

    return {
        "baseline_run": base.get("run"),
        "candidate_run": cand.get("run"),
        "baseline_metrics": base_summary,
        "candidate_metrics": cand_summary,
        "metric_deltas": metric_deltas,
        "regressions": regressions,
        "improvements": improvements,
    }


def to_markdown(comparison: dict[str, Any]) -> str:
    lines = [
        "# Craxis Eval Comparison",
        "",
        f"- Baseline: `{comparison['baseline_run']}`",
        f"- Candidate: `{comparison['candidate_run']}`",
        "",
        "## Metric Deltas",
        "",
        "| Metric | Baseline | Candidate | Delta |",
        "|---|---:|---:|---:|",
    ]

    for key, delta_val in comparison["metric_deltas"].items():
        base_val = comparison["baseline_metrics"].get(key, "n/a")
        cand_val = comparison["candidate_metrics"].get(key, "n/a")
        delta_display = delta_val if delta_val is not None else "n/a"
        lines.append(f"| {key} | {base_val} | {cand_val} | {delta_display} |")

    lines.extend(["", "## Top Improvements", ""])
    if comparison["improvements"]:
        for row in comparison["improvements"][:10]:
            lines.append(f"- `{row['id']}` ({row['task']}): +{row['better']}/-{row['worse']}")
    else:
        lines.append("- None")

    lines.extend(["", "## Regressions", ""])
    if comparison["regressions"]:
        for row in comparison["regressions"][:10]:
            lines.append(f"- `{row['id']}` ({row['task']}): +{row['better']}/-{row['worse']}")
    else:
        lines.append("- None")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two Craxis eval score reports.")
    parser.add_argument("--baseline", type=Path, required=True, help="Baseline score report JSON")
    parser.add_argument("--candidate", type=Path, required=True, help="Candidate score report JSON")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional markdown output path",
    )
    args = parser.parse_args()

    comparison = compare_reports(load_report(args.baseline), load_report(args.candidate))

    if args.output is None:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        args.output = REPORTS_DIR / "comparison.md"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(to_markdown(comparison), encoding="utf-8")

    print(to_markdown(comparison))
    print(f"Wrote comparison to {args.output}")


if __name__ == "__main__":
    main()
