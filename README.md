# Caraxis Research

Research and evaluation tooling for **Caraxis**, an AI cybersecurity analyst that monitors authorized environments, investigates alerts, maps threats to MITRE ATT&CK, and produces structured security findings.

This repository is the research foundation for Phase 1 (model selection, dataset design, fine-tuning) and the evaluation harness used to measure whether training actually improves analyst behavior.

## What is in this repo

| Component | Description |
|---|---|
| [`CARAXIS_RESEARCH_ROADMAP.md`](CARAXIS_RESEARCH_ROADMAP.md) | Full research plan: model choice, QLoRA training, dataset strategy, RAG, and Phase 2 agent architecture |
| [`evals/`](evals/) | Benchmarks, prompt templates, inference runner, scoring, and comparison reports |

Training scripts and datasets are planned as part of the roadmap; the evaluation harness is ready to use today.

## Caraxis-Bench

**Caraxis-Bench** is a custom benchmark of security analyst scenarios. It is the primary metric for deciding whether fine-tuning helps — not generic MCQ scores alone.

| File | Cases | Purpose |
|---|---:|---|
| `evals/caraxis_bench_v0.jsonl` | 12 | Primary product benchmark (triage, ATT&CK mapping, vuln analysis, detection explain, incident summary) |
| `evals/golden_set.jsonl` | 5 | Frozen regression set — do not change after first successful fine-tune |
| `evals/seceval_subset.jsonl` | 10 | Small SecEval-style MCQ subset for knowledge retention checks |

Task families covered:

- **Alert triage** — verdict, confidence, evidence, MITRE mapping, recommended actions
- **ATT&CK mapping** — map behavior descriptions to technique IDs
- **Vulnerability analysis** — CWE mapping, severity, remediation
- **Detection explanation** — explain what a Sigma rule detects
- **Incident summarization** — executive summary, IOCs, blast radius

Adversarial cases (e.g. prompt injection in log fields) are included from day one.

## Quick start

### Score the included example run (no GPU)

```bash
python evals/score.py --run evals/runs/example_base_3b.jsonl
```

### Export prompts for manual testing

Useful with Ollama, a notebook, or any chat UI:

```bash
python evals/run_eval.py \
  --bench evals/caraxis_bench_v0.jsonl \
  --export-prompts \
  --output evals/runs/prompts.jsonl
```

### Full evaluation workflow

**1. Run the base model**

```bash
python evals/run_eval.py \
  --bench evals/caraxis_bench_v0.jsonl \
  --model unsloth/Llama-3.2-3B-Instruct-bnb-4bit \
  --output evals/runs/base_3b.jsonl
```

**2. Run the fine-tuned model** (same command, different checkpoint)

**3. Score each run**

```bash
python evals/score.py --run evals/runs/base_3b.jsonl --output evals/reports/base_3b_report.json
python evals/score.py --run evals/runs/finetuned_3b.jsonl --output evals/reports/finetuned_3b_report.json
```

**4. Compare base vs fine-tuned**

```bash
python evals/report.py \
  --baseline evals/reports/base_3b_report.json \
  --candidate evals/reports/finetuned_3b_report.json
```

**5. Check knowledge retention**

```bash
python evals/score.py --bench evals/seceval_subset.jsonl --run evals/runs/base_3b_seceval.jsonl
```

**6. Regression test on the golden set**

```bash
python evals/score.py --bench evals/golden_set.jsonl --run evals/runs/finetuned_3b.jsonl
```

See [`evals/README.md`](evals/README.md) for run file format, metrics, and how to add new cases.

## Requirements

| Task | Dependencies |
|---|---|
| Scoring and reporting | Python 3.10+ (stdlib only) |
| Model inference (`run_eval.py --model`) | Python 3.11, CUDA GPU, [Unsloth](https://unsloth.ai/) |

```bash
pip install unsloth
```

For local QLoRA fine-tuning (planned), the roadmap recommends an RTX 4050 (6 GB VRAM) or Google Colab for 7B–8B experiments. See [`CARAXIS_RESEARCH_ROADMAP.md`](CARAXIS_RESEARCH_ROADMAP.md) for training configuration.

## Metrics

| Metric | Meaning |
|---|---|
| `verdict_correct` | Alert triage verdict matches gold |
| `mitre_f1` | F1 over MITRE ATT&CK technique IDs |
| `evidence_rate` | Fraction of required evidence points mentioned |
| `hallucination` | Model made a forbidden claim |
| `format_compliance` | Required output sections present |
| `mcq_correct` | Multiple-choice answer correct |

### Success bar for the first fine-tune

- Measurable improvement on `caraxis_bench_v0.jsonl` vs the base model (target: ≥10% relative gain)
- No large regression on `seceval_subset.jsonl`
- Lower `hallucination` or higher `evidence_rate` on triage cases
- Golden set scores must not regress after model changes

## Project structure

```text
caraxis_theLLM/
├── README.md
├── CARAXIS_RESEARCH_ROADMAP.md    # Research plan and architecture
└── evals/
    ├── README.md
    ├── caraxis_bench_v0.jsonl     # Primary benchmark
    ├── golden_set.jsonl          # Frozen regression set
    ├── seceval_subset.jsonl      # MCQ knowledge check
    ├── prompts/                  # Per-task prompt templates
    ├── runs/                     # Raw model outputs (JSONL)
    ├── reports/                  # Scored JSON + comparison markdown
    ├── run_eval.py               # Prompt export and model inference
    ├── score.py                  # Score a run against gold labels
    └── report.py                 # Compare two scored reports
```

## Research direction

Phase 1 focuses on teaching analyst behavior via QLoRA supervised fine-tuning:

- **Base model:** `unsloth/Llama-3.2-3B-Instruct-bnb-4bit`
- **Dataset:** Caraxis-Analyst-v1 (300–500 synthetic instruction pairs)
- **Method:** QLoRA + SFT on consumer GPU hardware

Phase 2 adds a minimal AI security analyst prototype:

```text
Logs → Sigma detection → Alert → Agent (fine-tuned model + RAG) → Investigation JSON → Slack
```

The roadmap covers dataset sources (MITRE ATT&CK, NVD, Sigma), license constraints, RAG with ChromaDB, read-only enrichment tools, and adversarial testing. Read [`CARAXIS_RESEARCH_ROADMAP.md`](CARAXIS_RESEARCH_ROADMAP.md) for the full plan.

## Data and license notes

- **Caraxis-Bench** scenarios are synthetic and held out from training.
- **SecEval** and **CTIBench** are evaluation-only — never include them in training data.
- Production model bases should use commercially licensed checkpoints (e.g. Llama 3.2, Foundation-Sec-8B). See Appendix B in the roadmap for a license quick reference.

## Contributing

When adding benchmark cases:

1. Add a JSON object to the appropriate `.jsonl` file with `id`, `task`, `input`, and `gold` fields.
2. Do not duplicate training examples.
3. For injection tests, embed malicious text inside `input`, not in system instructions.
