#!/usr/bin/env python3
"""Score Caraxis eval runs against benchmark gold labels."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

EVALS_DIR = Path(__file__).resolve().parent
RUNS_DIR = EVALS_DIR / "runs"
REPORTS_DIR = EVALS_DIR / "reports"

MITRE_RE = re.compile(r"\bT\d{4}(?:\.\d{3})?\b", re.IGNORECASE)
CWE_RE = re.compile(r"\bCWE-\d+\b", re.IGNORECASE)
VERDICT_RE = re.compile(
    r"verdict\s*:\s*(true_positive|false_positive|needs_human_review)",
    re.IGNORECASE,
)
CHOICE_RE = re.compile(r"\b([ABCD])\b")
SECTION_RE = re.compile(r"^([A-Za-z /]+):\s*(.*)$")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def extract_field(text: str, field_name: str) -> str:
    target = field_name.lower()
    for raw_line in text.splitlines():
        match = SECTION_RE.match(raw_line.strip())
        if match and match.group(1).strip().lower() == target:
            return match.group(2).strip()
    return ""


def extract_verdict(text: str) -> str | None:
    match = VERDICT_RE.search(text)
    return match.group(1).lower() if match else None


def extract_mitre_ids(text: str) -> set[str]:
    return {m.upper() for m in MITRE_RE.findall(text)}


def extract_cwe_ids(text: str) -> set[str]:
    return {c.upper() for c in CWE_RE.findall(text)}


def extract_choice(text: str) -> str | None:
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    match = CHOICE_RE.search(first_line)
    return match.group(1).upper() if match else None


def f1_score(pred: set[str], gold: set[str]) -> float:
    if not gold and not pred:
        return 1.0
    if not gold or not pred:
        return 0.0
    tp = len(pred & gold)
    precision = tp / len(pred)
    recall = tp / len(gold)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def point_hit_rate(text: str, points: list[str]) -> float:
    if not points:
        return 1.0
    lowered = normalize_text(text)
    hits = sum(1 for point in points if normalize_text(point) in lowered)
    return hits / len(points)


def has_forbidden_claim(text: str, forbidden: list[str]) -> bool:
    lowered = normalize_text(text)
    return any(normalize_text(claim) in lowered for claim in forbidden)


def format_compliance(text: str, required_sections: list[str]) -> float:
    if not required_sections:
        return 1.0
    present = sum(1 for section in required_sections if extract_field(text, section))
    return present / len(required_sections)


def score_case(case: dict[str, Any], prediction: str) -> dict[str, Any]:
    task = case["task"]
    gold = case["gold"]
    scores: dict[str, Any] = {"id": case["id"], "task": task}

    if task == "alert_triage":
        verdict = extract_verdict(prediction)
        acceptable = {v.lower() for v in gold.get("acceptable_verdicts", [gold["verdict"]])}
        scores["verdict_correct"] = verdict in acceptable if verdict else False
        scores["mitre_f1"] = f1_score(
            extract_mitre_ids(prediction),
            {m.upper() for m in gold.get("acceptable_mitre", gold.get("mitre_techniques", []))},
        )
        scores["evidence_rate"] = point_hit_rate(
            prediction, gold.get("required_evidence_points", [])
        )
        scores["hallucination"] = has_forbidden_claim(
            prediction, gold.get("forbidden_claims", [])
        )
        scores["format_compliance"] = format_compliance(
            prediction,
            ["Verdict", "Confidence", "Hypothesis", "Evidence", "MITRE ATT&CK", "Recommended Actions"],
        )

    elif task == "attack_mapping":
        scores["mitre_f1"] = f1_score(
            extract_mitre_ids(prediction),
            {m.upper() for m in gold.get("acceptable_mitre", gold.get("mitre_techniques", []))},
        )
        scores["detection_rate"] = point_hit_rate(
            prediction, gold.get("required_detection_ideas", [])
        )
        scores["hallucination"] = has_forbidden_claim(
            prediction, gold.get("forbidden_claims", [])
        )
        scores["format_compliance"] = format_compliance(
            prediction, ["MITRE ATT&CK", "Reasoning", "Detection Ideas"]
        )

    elif task == "vuln_analysis":
        pred_cwe = extract_cwe_ids(prediction)
        gold_cwe = {c.upper() for c in gold.get("acceptable_cwe", gold.get("cwe_ids", []))}
        scores["cwe_f1"] = f1_score(pred_cwe, gold_cwe)
        severity_text = normalize_text(extract_field(prediction, "Severity") or prediction)
        acceptable = {s.lower() for s in gold.get("acceptable_severity", [gold["severity_band"]])}
        scores["severity_correct"] = any(s in severity_text for s in acceptable)
        scores["remediation_rate"] = point_hit_rate(
            prediction, gold.get("required_remediation_points", [])
        )
        scores["hallucination"] = has_forbidden_claim(
            prediction, gold.get("forbidden_claims", [])
        )

    elif task == "detection_explain":
        scores["concept_rate"] = point_hit_rate(
            prediction, gold.get("required_concepts", [])
        )
        scores["mitre_f1"] = f1_score(
            extract_mitre_ids(prediction),
            {m.upper() for m in gold.get("acceptable_mitre", [])},
        )
        scores["hallucination"] = has_forbidden_claim(
            prediction, gold.get("forbidden_claims", [])
        )

    elif task == "incident_summary":
        scores["impact_rate"] = point_hit_rate(
            prediction, gold.get("required_impact_points", [])
        )
        scores["ioc_rate"] = point_hit_rate(prediction, gold.get("required_iocs", []))
        scores["mitre_f1"] = f1_score(
            extract_mitre_ids(prediction),
            {m.upper() for m in gold.get("acceptable_mitre", [])},
        )
        scores["hallucination"] = has_forbidden_claim(
            prediction, gold.get("forbidden_claims", [])
        )

    elif task == "mcq":
        choice = extract_choice(prediction)
        scores["mcq_correct"] = choice == gold["answer"].upper()

    return scores


def aggregate(case_scores: list[dict[str, Any]]) -> dict[str, Any]:
    metrics: dict[str, list[float]] = defaultdict(list)
    bool_metrics: dict[str, list[bool]] = defaultdict(list)

    for row in case_scores:
        for key, value in row.items():
            if key in {"id", "task"}:
                continue
            if isinstance(value, bool):
                bool_metrics[key].append(value)
            elif isinstance(value, (int, float)):
                metrics[key].append(float(value))

    summary: dict[str, Any] = {"num_cases": len(case_scores), "metrics": {}, "by_task": {}}

    for key, values in metrics.items():
        summary["metrics"][key] = round(sum(values) / len(values), 4)

    for key, values in bool_metrics.items():
        summary["metrics"][key] = round(sum(values) / len(values), 4)

    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in case_scores:
        by_task[row["task"]].append(row)

    for task, rows in by_task.items():
        task_summary: dict[str, Any] = {"num_cases": len(rows), "metrics": {}}
        task_metrics: dict[str, list[float]] = defaultdict(list)
        task_bool: dict[str, list[bool]] = defaultdict(list)
        for row in rows:
            for key, value in row.items():
                if key in {"id", "task"}:
                    continue
                if isinstance(value, bool):
                    task_bool[key].append(value)
                elif isinstance(value, (int, float)):
                    task_metrics[key].append(float(value))
        for key, values in task_metrics.items():
            task_summary["metrics"][key] = round(sum(values) / len(values), 4)
        for key, values in task_bool.items():
            task_summary["metrics"][key] = round(sum(values) / len(values), 4)
        summary["by_task"][task] = task_summary

    return summary


def score_run(bench_path: Path, run_path: Path) -> dict[str, Any]:
    bench = {row["id"]: row for row in load_jsonl(bench_path)}
    run_rows = load_jsonl(run_path)

    case_scores: list[dict[str, Any]] = []
    missing: list[str] = []

    for case_id, case in bench.items():
        match = next((row for row in run_rows if row.get("id") == case_id), None)
        if not match or "prediction" not in match:
            missing.append(case_id)
            continue
        case_scores.append(score_case(case, match["prediction"]))

    return {
        "benchmark": str(bench_path),
        "run": str(run_path),
        "missing_cases": missing,
        "case_scores": case_scores,
        "summary": aggregate(case_scores),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Score a Caraxis eval run.")
    parser.add_argument(
        "--bench",
        type=Path,
        default=EVALS_DIR / "caraxis_bench_v0.jsonl",
        help="Benchmark JSONL path",
    )
    parser.add_argument(
        "--run",
        type=Path,
        required=True,
        help="Run JSONL with fields: id, prediction",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output JSON report path",
    )
    args = parser.parse_args()

    report = score_run(args.bench, args.run)

    if args.output is None:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        args.output = REPORTS_DIR / f"{args.run.stem}_report.json"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(json.dumps(report["summary"], indent=2))
    print(f"\nWrote report to {args.output}")


if __name__ == "__main__":
    main()
