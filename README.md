# Caraxis Research

Research and evaluation tooling for **Caraxis**, an AI cybersecurity analyst that monitors authorized environments, investigates alerts, maps threats to MITRE ATT&CK, and produces structured security findings.

This repository is the research foundation for Phase 1 (model selection, dataset design, fine-tuning) and the evaluation harness used to measure whether training actually improves analyst behavior.

## Project status (2026-09-15)

| Milestone | Status |
|---|---|
| Caraxis-Analyst-v1 dataset (501 examples → 405 train) | Done |
| Caraxis-Bench v0 (12 held-out scenarios) | Done |
| QLoRA fine-tune on Llama-3.2-3B (Colab T4, 2 epochs) | Done |
| Base vs fine-tuned eval on Caraxis-Bench | Done — see [`evalresult.md`](evalresult.md) |
| SecEval subset knowledge check | Not run yet |
| Caraxis-Bench v1 (50+ scenarios) | Planned |
| Phase 2 (RAG + tools + agent) | Planned |

**LoRA adapter:** saved locally as `caraxis_lora_adapter/` (~97 MB). This directory is in [`.gitignore`](.gitignore) and is not committed — download or copy it from your training run before running fine-tuned inference.

## What is in this repo

| Component | Description |
|---|---|
| [`CARAXIS_RESEARCH_ROADMAP.md`](CARAXIS_RESEARCH_ROADMAP.md) | Full research plan: model choice, QLoRA training, dataset strategy, RAG, and Phase 2 agent architecture |
| [`data/caraxis_analyst_v1/`](data/caraxis_analyst_v1/) | Training dataset seeds, generated examples, and processed train/val/test splits |
| [`scripts/`](scripts/) | Seed fetch, dataset build, validation, and split utilities |
| [`evals/`](evals/) | Benchmarks, prompt templates, inference runner, scoring, and comparison reports |
| [`notebooks/caraxis_finetune_3b_colab.ipynb`](notebooks/caraxis_finetune_3b_colab.ipynb) | End-to-end 3B QLoRA training notebook for Google Colab |
| [`evalresult.md`](evalresult.md) | First fine-tune evaluation report (base vs LoRA on Caraxis-Bench v0) |

## First fine-tune results

On **Caraxis-Bench v0** (12 cases), QLoRA on Caraxis-Analyst-v1 produced clear gains on the primary task — alert triage:

| Metric | Base 3B | Fine-tuned | Delta |
|---|---:|---:|---:|
| `verdict_correct` | 0% | **100%** | +100% |
| `evidence_rate` | 53% | **73%** | +20% |
| `format_compliance` | 4% | **31%** | +27% |
| `mitre_f1` | 0% | **31%** | +31% |
| `hallucination` | 0% | 0% | — |

Attack-mapping `detection_rate` regressed (56% → 11%); CWE mapping remains at 0% for both models. Full per-task breakdown: [`evalresult.md`](evalresult.md) and [`evals/reports/comparison.md`](evals/reports/comparison.md).

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

## Dataset pipeline

Build **Caraxis-Analyst-v1** from ATT&CK, CVE, and Sigma seeds:

```bash
# Optional: refresh seeds from MITRE + NVD (requires network)
python scripts/fetch_seeds.py --output-dir data/caraxis_analyst_v1/seeds

# Generate 500 training examples (works offline with bundled seeds)
python scripts/build_dataset.py --total 500

# Validate and reject benchmark overlaps
python scripts/validate_dataset.py \
  data/caraxis_analyst_v1/raw/generated.jsonl \
  --clean-output data/caraxis_analyst_v1/raw/clean.jsonl

# Split into train/val/test
python scripts/split_dataset.py --input data/caraxis_analyst_v1/raw/clean.jsonl
```

Training files: `data/caraxis_analyst_v1/processed/train.jsonl` (405 examples in the default 500-run).

See [`data/caraxis_analyst_v1/README.md`](data/caraxis_analyst_v1/README.md) for record format and task mix.

### Colab notebook

Use [`notebooks/caraxis_finetune_3b_colab.ipynb`](notebooks/caraxis_finetune_3b_colab.ipynb) for end-to-end 3B QLoRA training on Google Colab (install → train → save → download).

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

**2. Run the fine-tuned model** (requires local `caraxis_lora_adapter/`)

```bash
python evals/run_eval.py \
  --bench evals/caraxis_bench_v0.jsonl \
  --model unsloth/Llama-3.2-3B-Instruct-bnb-4bit \
  --adapter caraxis_lora_adapter \
  --output evals/runs/finetuned_3b.jsonl
```

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
| Dataset generation | Python 3.10+, PyYAML (`pip install -r requirements-data.txt`) |
| Model inference (`run_eval.py --model`) | Python 3.12, CUDA GPU, see [`requirements-eval.txt`](requirements-eval.txt) |

```bash
# Scoring only — no GPU
python evals/score.py --run evals/runs/base_3b.jsonl

# GPU inference (see requirements-eval.txt for full setup)
.venv/bin/python evals/run_eval.py \
  --model unsloth/Llama-3.2-3B-Instruct-bnb-4bit \
  --adapter caraxis_lora_adapter \
  --output evals/runs/finetuned_3b.jsonl
```

First fine-tune used Google Colab (T4). Local training on an RTX 4050 (6 GB VRAM) is supported for 3B; see [`CARAXIS_RESEARCH_ROADMAP.md`](CARAXIS_RESEARCH_ROADMAP.md) for configuration and the Colab notebook for a full walkthrough.

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
├── evalresult.md                  # First fine-tune eval report
├── .gitignore                     # Excludes caraxis_lora_adapter/ weights
├── requirements-data.txt          # PyYAML for dataset scripts
├── requirements-eval.txt          # Unsloth + torch for GPU inference
├── data/caraxis_analyst_v1/       # Seeds, raw, processed splits
├── scripts/                       # fetch_seeds, build_dataset, validate, split
├── notebooks/                     # Colab fine-tuning notebook
├── caraxis_lora_adapter/          # LoRA weights (local only, gitignored)
└── evals/
    ├── README.md
    ├── caraxis_bench_v0.jsonl     # Primary benchmark (12 cases)
    ├── golden_set.jsonl           # Frozen regression set (5 cases)
    ├── seceval_subset.jsonl       # MCQ knowledge check (10 cases)
    ├── prompts/                   # Per-task prompt templates
    ├── runs/                      # Raw model outputs (JSONL)
    ├── reports/                   # Scored JSON + comparison markdown
    ├── run_eval.py                # Prompt export and model inference
    ├── score.py                   # Score a run against gold labels
    └── report.py                  # Compare two scored reports
```

## Research direction

Phase 1 v1 is complete — QLoRA SFT on Caraxis-Analyst-v1 measurably improved alert triage on Caraxis-Bench v0. Next steps:

- Expand **Caraxis-Bench** to 50+ scenarios (v1) with more attack-mapping and CWE cases
- Build **Caraxis-Analyst-v2** with targeted examples for failure modes (attack mapping, CWE)
- Run **SecEval subset** to confirm no knowledge regression
- **Colab scale-up:** compare 3B vs 8B on the same dataset

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
