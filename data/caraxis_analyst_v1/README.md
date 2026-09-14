# Caraxis-Analyst-v1 Dataset

Instruction-tuning dataset for Caraxis security analyst models (3B and 8B).

## Directory layout

```text
data/caraxis_analyst_v1/
  seeds/                 # Authoritative source material (ATT&CK, CVE, Sigma)
    attack/techniques.json
    cve/samples.json
    sigma/samples.yaml
  examples/              # Hand-written gold examples (quality anchors)
    hand_written.jsonl
  raw/                   # Generated candidates (pre-validation)
    generated.jsonl
  processed/             # Final train/val/test splits
    train.jsonl
    val.jsonl
    test.jsonl
```

## Quick start

```bash
# 1. Optional: refresh seeds from MITRE ATT&CK + NVD
python scripts/fetch_seeds.py --output-dir data/caraxis_analyst_v1/seeds

# 2. Generate dataset from seeds (works offline with bundled samples)
python scripts/build_dataset.py \
  --seeds data/caraxis_analyst_v1/seeds \
  --examples data/caraxis_analyst_v1/examples/hand_written.jsonl \
  --output data/caraxis_analyst_v1/raw/generated.jsonl

# 3. Validate schema + decontaminate against eval benchmarks
python scripts/validate_dataset.py \
  data/caraxis_analyst_v1/raw/generated.jsonl \
  --reject-output data/caraxis_analyst_v1/raw/rejected.jsonl

# 4. Split into train/val/test (80/10/10, stratified by task)
python scripts/split_dataset.py \
  --input data/caraxis_analyst_v1/raw/generated.jsonl \
  --output-dir data/caraxis_analyst_v1/processed
```

## Task mix (target for v1)

| Task | Weight | Seed source |
|---|---|---|
| alert_triage | 40% | Parameterized alert templates |
| attack_mapping | 25% | ATT&CK techniques |
| vuln_analysis | 20% | NVD/CVE records |
| detection_explain | 10% | Sigma rules |
| incident_summary | 5% | Synthetic timelines |

## Record format

Each line is JSON with a `messages` array (ShareGPT / chat format):

```json
{
  "id": "caraxis-00001",
  "task": "alert_triage",
  "source": "synthetic",
  "seed_refs": ["T1110.001"],
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

## v1 vs v2 sizing

| Version | Examples | When |
|---|---|---|
| v1 | 300–500 | First 3B and 8B fine-tunes |
| v2 | 1,500–2,000 | After eval failure analysis |

## Rules

- Never train on `evals/caraxis_bench_v0.jsonl`, `evals/golden_set.jsonl`, or `evals/seceval_subset.jsonl`
- Run `validate_dataset.py` before every training run
- Manually review ~10% of generated examples before scaling to v2
