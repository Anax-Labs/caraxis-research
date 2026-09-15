#!/usr/bin/env python3
"""Generate prompts for benchmark cases and optionally run a local model.

Usage:
  # Export prompts only (no model required)
  python evals/run_eval.py --bench evals/caraxis_bench_v0.jsonl --export-prompts

  # Run with a HuggingFace / Unsloth model (requires GPU + deps)
  python evals/run_eval.py --bench evals/caraxis_bench_v0.jsonl --model unsloth/Llama-3.2-3B-Instruct-bnb-4bit --output evals/runs/base_3b.jsonl

  # Run base + downloaded LoRA adapter
  python evals/run_eval.py --bench evals/caraxis_bench_v0.jsonl --model unsloth/Llama-3.2-3B-Instruct-bnb-4bit --adapter caraxis_lora_adapter --output evals/runs/finetuned_3b.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

EVALS_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = EVALS_DIR / "prompts"
RUNS_DIR = EVALS_DIR / "runs"

TASK_PROMPT_FILES = {
    "alert_triage": "triage.txt",
    "attack_mapping": "attack_mapping.txt",
    "vuln_analysis": "vuln_analysis.txt",
    "detection_explain": "detection_explain.txt",
    "incident_summary": "incident_summary.txt",
    "mcq": "mcq.txt",
}


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_prompt(case: dict[str, Any], system_prompt: str) -> str:
    task = case["task"]
    template_name = TASK_PROMPT_FILES[task]
    template = load_text(PROMPTS_DIR / template_name)

    if task == "mcq":
        payload = case["input"]
        user_prompt = template.format(
            question=payload["question"],
            choice_a=payload["choices"]["A"],
            choice_b=payload["choices"]["B"],
            choice_c=payload["choices"]["C"],
            choice_d=payload["choices"]["D"],
        )
    else:
        user_prompt = template.format(input_json=json.dumps(case["input"], indent=2))

    return f"{system_prompt.strip()}\n\n{user_prompt.strip()}"


def export_prompts(bench_path: Path, output_path: Path) -> None:
    system_prompt = load_text(PROMPTS_DIR / "system.txt")
    rows = []
    for case in load_jsonl(bench_path):
        rows.append(
            {
                "id": case["id"],
                "task": case["task"],
                "prompt": build_prompt(case, system_prompt),
            }
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    print(f"Exported {len(rows)} prompts to {output_path}")


def run_model(
    bench_path: Path,
    model_name: str,
    output_path: Path,
    max_new_tokens: int,
    adapter_path: Path | None = None,
) -> None:
    try:
        from peft import PeftModel
        from unsloth import FastLanguageModel
        import torch
    except ImportError as exc:
        raise SystemExit(
            "Unsloth + peft are required for --model runs. "
            "Install with: pip install -r requirements-eval.txt"
        ) from exc

    system_prompt = load_text(PROMPTS_DIR / "system.txt")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=2048,
        load_in_4bit=True,
    )
    run_label = model_name
    if adapter_path is not None:
        if not adapter_path.exists():
            raise SystemExit(f"Adapter path not found: {adapter_path}")
        model = PeftModel.from_pretrained(model, str(adapter_path))
        run_label = f"{model_name}+{adapter_path.name}"
    FastLanguageModel.for_inference(model)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cases = load_jsonl(bench_path)

    with output_path.open("w", encoding="utf-8") as f:
        for case in cases:
            prompt = build_prompt(case, system_prompt)
            messages = [{"role": "user", "content": prompt}]
            inputs = tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt",
            ).to(model.device)

            with torch.no_grad():
                outputs = model.generate(
                    inputs=inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=0.0,
                    do_sample=False,
                )

            prediction = tokenizer.decode(outputs[0][inputs.shape[1] :], skip_special_tokens=True)
            row = {
                "id": case["id"],
                "task": case["task"],
                "model": run_label,
                "prediction": prediction.strip(),
            }
            f.write(json.dumps(row) + "\n")
            print(f"Completed {case['id']}")

    print(f"Wrote run to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Caraxis benchmark prompts against a model.")
    parser.add_argument("--bench", type=Path, default=EVALS_DIR / "caraxis_bench_v0.jsonl")
    parser.add_argument("--model", type=str, default=None, help="HF model name or Unsloth checkpoint")
    parser.add_argument(
        "--adapter",
        type=Path,
        default=None,
        help="Path to LoRA adapter directory (loads on top of --model base)",
    )
    parser.add_argument("--output", type=Path, default=RUNS_DIR / "run.jsonl")
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument(
        "--export-prompts",
        action="store_true",
        help="Export prompts only; do not run inference",
    )
    args = parser.parse_args()

    if args.export_prompts:
        export_prompts(args.bench, args.output)
        return

    if not args.model:
        raise SystemExit("Provide --model or use --export-prompts")

    run_model(args.bench, args.model, args.output, args.max_new_tokens, args.adapter)


if __name__ == "__main__":
    main()
