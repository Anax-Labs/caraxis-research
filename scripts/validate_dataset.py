#!/usr/bin/env python3
"""Validate Caraxis dataset records and reject benchmark overlaps."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.records import instruction_hash, load_jsonl, write_jsonl

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVAL_PATHS = [
    PROJECT_ROOT / "evals" / "caraxis_bench_v0.jsonl",
    PROJECT_ROOT / "evals" / "golden_set.jsonl",
    PROJECT_ROOT / "evals" / "seceval_subset.jsonl",
]

REQUIRED_TOP_LEVEL = {"id", "task", "messages"}
REQUIRED_ROLES = {"system", "user", "assistant"}
VALID_TASKS = {
    "alert_triage",
    "attack_mapping",
    "vuln_analysis",
    "detection_explain",
    "incident_summary",
}


def load_eval_hashes() -> set[str]:
    hashes: set[str] = set()
    for path in EVAL_PATHS:
        if not path.exists():
            continue
        for row in load_jsonl(path):
            if "messages" in row:
                hashes.add(instruction_hash(row))
                continue
            payload = json.dumps(row.get("input", {}), sort_keys=True)
            hashes.add(instruction_hash({"messages": [{"role": "user", "content": payload}]}))
    return hashes


def validate_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    missing = REQUIRED_TOP_LEVEL - set(record)
    if missing:
        errors.append(f"missing fields: {sorted(missing)}")

    task = record.get("task")
    if task not in VALID_TASKS:
        errors.append(f"invalid task: {task}")

    messages = record.get("messages", [])
    if len(messages) < 3:
        errors.append("messages must include system, user, and assistant")
        return errors

    roles = {message.get("role") for message in messages}
    if not REQUIRED_ROLES.issubset(roles):
        errors.append(f"missing roles: {sorted(REQUIRED_ROLES - roles)}")

    for message in messages:
        content = message.get("content", "")
        if not isinstance(content, str) or not content.strip():
            errors.append(f"empty content for role={message.get('role')}")
        if message.get("role") == "assistant" and len(content) < 40:
            errors.append("assistant response too short")

    record_id = record.get("id", "")
    if not re.match(r"^[a-z0-9][a-z0-9._-]+$", record_id):
        errors.append(f"invalid id: {record_id}")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Caraxis dataset JSONL.")
    parser.add_argument("input", type=Path)
    parser.add_argument(
        "--reject-output",
        type=Path,
        default=None,
        help="Write rejected records with reasons",
    )
    parser.add_argument(
        "--clean-output",
        type=Path,
        default=None,
        help="Write accepted records to this path",
    )
    args = parser.parse_args()

    eval_hashes = load_eval_hashes()
    rows = load_jsonl(args.input)

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()

    for row in rows:
        errors = validate_record(row)
        row_hash = instruction_hash(row)
        if row_hash in eval_hashes:
            errors.append("overlaps eval benchmark instruction")
        if row_hash in seen_hashes:
            errors.append("duplicate instruction hash")
        seen_hashes.add(row_hash)

        if errors:
            rejected.append({**row, "validation_errors": errors})
        else:
            accepted.append(row)

    if args.clean_output:
        write_jsonl(args.clean_output, accepted)
    if args.reject_output:
        write_jsonl(args.reject_output, rejected)

    print(
        json.dumps(
            {
                "input": str(args.input),
                "total": len(rows),
                "accepted": len(accepted),
                "rejected": len(rejected),
            },
            indent=2,
        )
    )

    if rejected:
        print("\nFirst rejection:")
        print(json.dumps(rejected[0].get("validation_errors"), indent=2))


if __name__ == "__main__":
    main()
