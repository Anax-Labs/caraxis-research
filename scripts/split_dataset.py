#!/usr/bin/env python3
"""Split validated dataset into train/val/test JSONL files."""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.records import load_jsonl, write_jsonl

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "caraxis_analyst_v1" / "raw" / "generated.jsonl"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "caraxis_analyst_v1" / "processed"


def split_records(
    rows: list[dict[str, Any]],
    train_ratio: float,
    val_ratio: float,
    seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rng = random.Random(seed)
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_task[row["task"]].append(row)

    train: list[dict[str, Any]] = []
    val: list[dict[str, Any]] = []
    test: list[dict[str, Any]] = []

    for task_rows in by_task.values():
        rng.shuffle(task_rows)
        n = len(task_rows)
        val_count = max(1, int(n * val_ratio)) if n >= 3 else (1 if n > 1 else 0)
        test_count = max(1, int(n * (1.0 - train_ratio - val_ratio))) if n >= 3 else 0
        if n <= 2:
            train.extend(task_rows)
            continue
        remaining = n - val_count - test_count
        if remaining < 1:
            val_count = 1
            test_count = 1
            remaining = n - 2
        train.extend(task_rows[:remaining])
        val.extend(task_rows[remaining : remaining + val_count])
        test.extend(task_rows[remaining + val_count :])

    return train, val, test


def main() -> None:
    parser = argparse.ArgumentParser(description="Split Caraxis dataset.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rows = load_jsonl(args.input)
    train, val, test = split_records(rows, args.train_ratio, args.val_ratio, args.seed)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_dir / "train.jsonl", train)
    write_jsonl(args.output_dir / "val.jsonl", val)
    write_jsonl(args.output_dir / "test.jsonl", test)

    summary = {
        "input": str(args.input),
        "output_dir": str(args.output_dir),
        "train": len(train),
        "val": len(val),
        "test": len(test),
        "by_task": {
            split_name: dict(
                sorted(
                    {
                        task: sum(1 for row in split_rows if row["task"] == task)
                        for task in {r["task"] for r in split_rows}
                    }.items()
                )
            )
            for split_name, split_rows in {
                "train": train,
                "val": val,
                "test": test,
            }.items()
        },
    }
    (args.output_dir / "split_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
