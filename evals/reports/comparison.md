# Caraxis Eval Comparison

- Baseline: `evals/runs/base_3b.jsonl`
- Candidate: `evals/runs/finetuned_3b.jsonl`

## Metric Deltas

| Metric | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| concept_rate | 0.75 | 0.5 | -0.25 |
| cwe_f1 | 0.0 | 0.0 | 0.0 |
| detection_rate | 0.5556 | 0.1111 | -0.4445 |
| evidence_rate | 0.5333 | 0.7333 | 0.2 |
| format_compliance | 0.0417 | 0.3125 | 0.2708 |
| hallucination | 0.0 | 0.0 | 0.0 |
| impact_rate | 0.75 | 0.5 | -0.25 |
| ioc_rate | 0.0 | 1.0 | 1.0 |
| mitre_f1 | 0.0 | 0.3057 | 0.3057 |
| remediation_rate | 0.6667 | 0.6667 | 0.0 |
| severity_correct | 1.0 | 1.0 | 0.0 |
| verdict_correct | 0.0 | 1.0 | 1.0 |

## Top Improvements

- `bench-summary-001` (incident_summary): +2/-1
- `bench-triage-001` (alert_triage): +4/-0
- `bench-triage-002` (alert_triage): +2/-0
- `bench-triage-003` (alert_triage): +4/-0
- `bench-triage-004` (alert_triage): +2/-0
- `bench-triage-005` (alert_triage): +3/-0

## Regressions

- `bench-attack-001` (attack_mapping): +0/-1
- `bench-attack-003` (attack_mapping): +0/-1
