# Caraxis Eval Results

**Date:** 2026-09-15  
**Benchmark:** `evals/caraxis_bench_v0.jsonl` (12 cases)  
**Hardware:** NVIDIA GeForce RTX 4050 Laptop GPU (6 GB)

## Models

| Role | Model | Run file |
|------|-------|----------|
| Baseline | `unsloth/Llama-3.2-3B-Instruct-bnb-4bit` | `evals/runs/base_3b.jsonl` |
| Fine-tuned | Base + LoRA adapter `caraxis_lora_adapter` | `evals/runs/finetuned_3b.jsonl` |

Training: QLoRA on Caraxis-Analyst-v1 (~405 examples, 2 epochs, Colab T4).

---

## Executive Summary

Fine-tuning produced **clear gains on alert triage** — the primary product task:

- **Verdict accuracy:** 0% → **100%** (5/5 triage cases correct)
- **Evidence rate:** 53% → **73%**
- **Format compliance:** 4% → **31%**
- **MITRE F1 (overall):** 0% → **31%**
- **IOC extraction (incident summary):** 0% → **100%**
- **Hallucinations:** 0 in both runs

**Regressions:** Attack-mapping detection rate dropped (56% → 11%). CWE mapping unchanged at 0% for both models.

**Verdict:** First fine-tune is a success for triage behavior; attack mapping and vuln analysis need more targeted data in v2.

---

## Overall Metrics

| Metric | Base | Fine-tuned | Delta |
|--------|-----:|-----------:|------:|
| verdict_correct | 0.0000 | **1.0000** | +1.0000 |
| evidence_rate | 0.5333 | **0.7333** | +0.2000 |
| format_compliance | 0.0417 | **0.3125** | +0.2708 |
| mitre_f1 | 0.0000 | **0.3057** | +0.3057 |
| ioc_rate | 0.0000 | **1.0000** | +1.0000 |
| concept_rate | 0.7500 | 0.5000 | -0.2500 |
| detection_rate | 0.5556 | 0.1111 | -0.4445 |
| impact_rate | 0.7500 | 0.5000 | -0.2500 |
| cwe_f1 | 0.0000 | 0.0000 | 0.0000 |
| remediation_rate | 0.6667 | 0.6667 | 0.0000 |
| severity_correct | 1.0000 | 1.0000 | 0.0000 |
| hallucination | 0.0000 | 0.0000 | 0.0000 |

---

## Metrics by Task

### Alert Triage (5 cases)

| Metric | Base | Fine-tuned | Delta |
|--------|-----:|-----------:|------:|
| verdict_correct | 0.0000 | **1.0000** | +1.0000 |
| evidence_rate | 0.5333 | **0.7333** | +0.2000 |
| format_compliance | 0.0000 | **0.5000** | +0.5000 |
| mitre_f1 | 0.0000 | **0.3600** | +0.3600 |
| hallucination | 0.0000 | 0.0000 | 0.0000 |

### Attack Mapping (3 cases)

| Metric | Base | Fine-tuned | Delta |
|--------|-----:|-----------:|------:|
| mitre_f1 | 0.0000 | 0.0952 | +0.0952 |
| detection_rate | 0.5556 | 0.1111 | -0.4445 |
| format_compliance | 0.1111 | 0.0000 | -0.1111 |
| hallucination | 0.0000 | 0.0000 | 0.0000 |

### Vulnerability Analysis (2 cases)

| Metric | Base | Fine-tuned | Delta |
|--------|-----:|-----------:|------:|
| cwe_f1 | 0.0000 | 0.0000 | 0.0000 |
| remediation_rate | 0.6667 | 0.6667 | 0.0000 |
| severity_correct | 1.0000 | 1.0000 | 0.0000 |
| hallucination | 0.0000 | 0.0000 | 0.0000 |

### Detection Explain (1 case)

| Metric | Base | Fine-tuned | Delta |
|--------|-----:|-----------:|------:|
| concept_rate | 0.7500 | 0.5000 | -0.2500 |
| mitre_f1 | 0.0000 | **0.4000** | +0.4000 |
| hallucination | 0.0000 | 0.0000 | 0.0000 |

### Incident Summary (1 case)

| Metric | Base | Fine-tuned | Delta |
|--------|-----:|-----------:|------:|
| ioc_rate | 0.0000 | **1.0000** | +1.0000 |
| mitre_f1 | 0.0000 | **0.5714** | +0.5714 |
| impact_rate | 0.7500 | 0.5000 | -0.2500 |
| hallucination | 0.0000 | 0.0000 | 0.0000 |

---

## Per-Case Scores

### Alert Triage

| Case ID | Base verdict | FT verdict | Base MITRE F1 | FT MITRE F1 | Base evidence | FT evidence | Base format | FT format |
|---------|:------------:|:--------:|:-------------:|:-----------:|:-------------:|:-----------:|:-----------:|:---------:|
| bench-triage-001 | ✗ | ✓ | 0.00 | 0.50 | 0.67 | **1.00** | 0.00 | **0.50** |
| bench-triage-002 | ✗ | ✓ | 0.00 | 0.00 | 0.67 | 0.67 | 0.00 | **0.50** |
| bench-triage-003 | ✗ | ✓ | 0.00 | **0.50** | 0.00 | **0.67** | 0.00 | **0.50** |
| bench-triage-004 | ✗ | ✓ | 0.00 | 0.00 | 0.33 | 0.33 | 0.00 | **0.50** |
| bench-triage-005 | ✗ | ✓ | 0.00 | **0.80** | 1.00 | 1.00 | 0.00 | **0.50** |

### Attack Mapping

| Case ID | Base MITRE F1 | FT MITRE F1 | Base detection | FT detection | Base format | FT format |
|---------|:-------------:|:-----------:|:--------------:|:------------:|:-----------:|:---------:|
| bench-attack-001 | 0.00 | 0.00 | 0.33 | 0.33 | 0.33 | 0.00 |
| bench-attack-002 | 0.00 | **0.29** | **1.00** | 0.00 | 0.00 | 0.00 |
| bench-attack-003 | 0.00 | 0.00 | 0.33 | 0.00 | 0.00 | 0.00 |

### Vulnerability Analysis

| Case ID | Base CWE F1 | FT CWE F1 | Base severity | FT severity | Base remediation | FT remediation |
|---------|:-----------:|:---------:|:-------------:|:-----------:|:----------------:|:--------------:|
| bench-vuln-001 | 0.00 | 0.00 | ✓ | ✓ | 0.67 | 0.67 |
| bench-vuln-002 | 0.00 | 0.00 | ✓ | ✓ | 0.67 | 0.67 |

### Detection Explain & Incident Summary

| Case ID | Task | Base key metrics | Fine-tuned key metrics |
|---------|------|------------------|------------------------|
| bench-detect-001 | detection_explain | concept 0.75, MITRE F1 0.00 | concept 0.50, MITRE F1 **0.40** |
| bench-summary-001 | incident_summary | impact 0.75, IOC 0.00, MITRE F1 0.00 | impact 0.50, IOC **1.00**, MITRE F1 **0.57** |

---

## Improvements vs Regressions

### Top Improvements

| Case ID | Task | Notes |
|---------|------|-------|
| bench-triage-001 | alert_triage | +4 metrics improved |
| bench-triage-002 | alert_triage | +2 metrics improved |
| bench-triage-003 | alert_triage | +4 metrics improved |
| bench-triage-004 | alert_triage | +2 metrics improved |
| bench-triage-005 | alert_triage | +3 metrics improved |
| bench-summary-001 | incident_summary | +2 metrics improved, -1 regressed |

### Regressions

| Case ID | Task | Notes |
|---------|------|-------|
| bench-attack-001 | attack_mapping | -1 metric |
| bench-attack-003 | attack_mapping | -1 metric |

---

## Recommendations

1. **Ship triage improvements** — verdict and evidence gains align with Phase 1 goals.
2. **Expand attack_mapping examples** in Caraxis-Analyst-v2 (dataset skew may explain detection_rate drop).
3. **Add CWE-focused training** — both models score 0 on CWE F1.
4. **Run SecEval subset** — confirm no knowledge regression on `evals/seceval_subset.jsonl`.
5. **Freeze golden set** — regression-test future runs against `evals/golden_set.jsonl`.

---

## Artifacts

| File | Description |
|------|-------------|
| `evals/runs/base_3b.jsonl` | Raw base model predictions |
| `evals/runs/finetuned_3b.jsonl` | Raw fine-tuned predictions |
| `evals/reports/base_3b_report.json` | Scored base report |
| `evals/reports/finetuned_3b_report.json` | Scored fine-tuned report |
| `evals/reports/comparison.md` | Auto-generated comparison |

**Regenerate:**

```bash
.venv/bin/python evals/score.py --run evals/runs/base_3b.jsonl --output evals/reports/base_3b_report.json
.venv/bin/python evals/score.py --run evals/runs/finetuned_3b.jsonl --output evals/reports/finetuned_3b_report.json
.venv/bin/python evals/report.py \
  --baseline evals/reports/base_3b_report.json \
  --candidate evals/reports/finetuned_3b_report.json
```
