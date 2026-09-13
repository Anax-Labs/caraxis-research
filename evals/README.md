# Craxis Evals

Evaluation harness for comparing base vs fine-tuned Craxis models.

## Layout

```text
evals/
  craxis_bench_v0.jsonl   # Primary product benchmark (12 cases)
  golden_set.jsonl        # Frozen regression set (5 cases)
  seceval_subset.jsonl    # Small MCQ knowledge check (10 cases)
  prompts/                # Prompt templates per task
  runs/                   # Raw model outputs
  reports/                # Scored JSON + comparison markdown
  run_eval.py             # Generate prompts or run inference
  score.py                # Score a run against a benchmark
  report.py               # Compare two scored reports
```

## Quick start (no GPU)

Score the included example run:

```bash
python evals/score.py --run evals/runs/example_base_3b.jsonl
```

Export prompts for manual testing in Ollama or a notebook:

```bash
python evals/run_eval.py --bench evals/craxis_bench_v0.jsonl --export-prompts --output evals/runs/prompts.jsonl
```

## Full workflow

### 1. Run base model

```bash
python evals/run_eval.py \
  --bench evals/craxis_bench_v0.jsonl \
  --model unsloth/Llama-3.2-3B-Instruct-bnb-4bit \
  --output evals/runs/base_3b.jsonl
```

### 2. Run fine-tuned model

Use the same command with your merged model or adapter-loaded checkpoint.

### 3. Score each run

```bash
python evals/score.py --run evals/runs/base_3b.jsonl --output evals/reports/base_3b_report.json
python evals/score.py --run evals/runs/finetuned_3b.jsonl --output evals/reports/finetuned_3b_report.json
```

### 4. Compare base vs fine-tuned

```bash
python evals/report.py \
  --baseline evals/reports/base_3b_report.json \
  --candidate evals/reports/finetuned_3b_report.json
```

### 5. Score knowledge retention

```bash
python evals/score.py --bench evals/seceval_subset.jsonl --run evals/runs/base_3b_seceval.jsonl
```

### 6. Regression test on golden set

```bash
python evals/score.py --bench evals/golden_set.jsonl --run evals/runs/finetuned_3b.jsonl
```

## Run file format

Each line in `runs/*.jsonl`:

```json
{"id": "bench-triage-001", "task": "alert_triage", "model": "unsloth/Llama-3.2-3B-Instruct-bnb-4bit", "prediction": "Verdict: true_positive\n..."}
```

You can also produce runs manually from Ollama or another UI, as long as `id` and `prediction` are present.

## Metrics

| Metric | Meaning |
|---|---|
| `verdict_correct` | Alert triage verdict matches gold |
| `mitre_f1` | F1 over MITRE technique IDs |
| `evidence_rate` | Fraction of required evidence points mentioned |
| `hallucination` | Model made a forbidden claim |
| `format_compliance` | Required output sections present |
| `mcq_correct` | Multiple-choice answer correct |

## Success bar for first fine-tune

- Measurable improvement on `craxis_bench_v0.jsonl` vs base
- No large drop on `seceval_subset.jsonl`
- Lower `hallucination` or higher `evidence_rate` on triage cases
- Golden set should not regress after model changes

## Adding cases

1. Add a new JSON object to `craxis_bench_v0.jsonl`
2. Keep `id`, `task`, `input`, and `gold` fields
3. Do not duplicate training examples
4. For injection tests, put malicious text inside `input`, not in instructions
