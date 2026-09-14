#!/usr/bin/env python3
"""Generate Caraxis-Analyst instruction dataset from seeds."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.records import load_json, load_jsonl, make_record, wrap_untrusted, write_jsonl

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEEDS = PROJECT_ROOT / "data" / "caraxis_analyst_v1" / "seeds"
DEFAULT_EXAMPLES = PROJECT_ROOT / "data" / "caraxis_analyst_v1" / "examples" / "hand_written.jsonl"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "caraxis_analyst_v1" / "raw" / "generated.jsonl"

ALERT_SCENARIOS = [
    {
        "suffix": "ssh-brute",
        "alert": {
            "alert_id": "ALRT-{n:04d}",
            "severity": "high",
            "title": "Multiple failed SSH authentications",
            "source_ip": "203.0.113.{octet}",
            "host": "prod-web-{host}",
            "failed_attempts": 847,
            "targeted_accounts": ["root", "admin", "deploy"],
        },
        "verdict": "true_positive",
        "confidence": "high",
        "hypothesis": "Automated SSH brute-force activity targeting privileged accounts.",
        "evidence": [
            "847 failed authentication attempts exceed normal login noise.",
            "Targeted accounts include root, admin, and deploy.",
            "External source IP requires reputation enrichment.",
        ],
        "mitre": ["T1110.001"],
        "actions": [
            "Block or rate-limit the source IP at the perimeter.",
            "Verify no successful authentication occurred from this source.",
            "Enable MFA for SSH-accessible accounts.",
        ],
        "seed_refs": ["T1110.001", "sigma:ssh-bruteforce"],
    },
    {
        "suffix": "rdp-brute",
        "alert": {
            "alert_id": "ALRT-{n:04d}",
            "severity": "high",
            "title": "RDP brute force from external IP",
            "source_ip": "198.51.100.{octet}",
            "host": "win-dc-{host}",
            "failed_attempts": 1203,
            "targeted_accounts": ["Administrator", "admin", "backup"],
            "port": 3389,
        },
        "verdict": "true_positive",
        "confidence": "high",
        "hypothesis": "External RDP credential guessing against privileged Windows accounts.",
        "evidence": [
            "More than 1,200 failed attempts on port 3389 indicate automated guessing.",
            "Administrator and backup accounts are common brute-force targets.",
        ],
        "mitre": ["T1110.001", "T1021.001"],
        "actions": [
            "Block the source IP and restrict RDP exposure.",
            "Audit for successful RDP logons from this address.",
        ],
        "seed_refs": ["T1110.001", "T1021.001"],
    },
    {
        "suffix": "password-change-fp",
        "alert": {
            "alert_id": "ALRT-{n:04d}",
            "severity": "low",
            "title": "Single failed login after password change",
            "source_ip": "10.0.5.{octet}",
            "host": "dev-laptop-{host}",
            "failed_attempts": 1,
            "targeted_accounts": ["jsmith"],
            "user_context": "Employee mistyped new password per helpdesk ticket HD-{ticket}",
        },
        "verdict": "false_positive",
        "confidence": "medium",
        "hypothesis": "Likely user error after a legitimate password change.",
        "evidence": [
            "Only one failed attempt was observed.",
            "Helpdesk ticket context supports a benign explanation.",
        ],
        "mitre": [],
        "actions": [
            "Monitor briefly for additional failures.",
            "No escalation required unless activity repeats.",
        ],
        "seed_refs": [],
    },
    {
        "suffix": "off-hours-login",
        "alert": {
            "alert_id": "ALRT-{n:04d}",
            "severity": "medium",
            "title": "Unusual login time for finance user",
            "source_ip": "203.0.113.{octet}",
            "host": "vpn-gateway",
            "user": "finance_mgr_{host}",
            "login_time": "03:14 UTC",
            "user_timezone": "US/Eastern",
            "historical_pattern": "weekday 09:00-17:00 only",
        },
        "verdict": "needs_human_review",
        "confidence": "medium",
        "hypothesis": "Off-hours VPN authentication may be legitimate travel or unauthorized access.",
        "evidence": [
            "Login occurred outside the user's normal working-hours pattern.",
            "Additional context is required to confirm user intent.",
        ],
        "mitre": ["T1078"],
        "actions": [
            "Contact the user or manager to verify the login.",
            "Review recent authentication history and MFA status.",
        ],
        "seed_refs": ["T1078"],
    },
]

TIMELINE_SCENARIOS = [
    {
        "title": "Phishing to mailbox rule",
        "events": [
            {"time": "2026-03-10T08:12Z", "event": "Phishing email received by finance users"},
            {"time": "2026-03-10T08:45Z", "event": "User submitted credentials on fake O365 page"},
            {"time": "2026-03-10T09:02Z", "event": "Successful login from 198.51.100.44"},
            {"time": "2026-03-10T09:15Z", "event": "Mailbox forwarding rule created"},
        ],
        "summary": "A finance user was phished, leading to account compromise and malicious mailbox forwarding.",
        "iocs": ["198.51.100.44"],
        "mitre": ["T1566.002", "T1078", "T1114.003"],
        "seed_refs": ["T1566.002", "T1114.003"],
    }
]


def format_list_section(title: str, items: list[str]) -> str:
    if not items:
        return f"{title}:\n- None identified"
    lines = [f"{title}:"]
    for item in items:
        lines.append(f"- {item}")
    return "\n".join(lines)


def build_triage_response(scenario: dict[str, Any]) -> str:
    mitre_lines = scenario["mitre"] or ["None identified from available evidence"]
    return "\n".join(
        [
            f"Verdict: {scenario['verdict']}",
            f"Confidence: {scenario['confidence']}",
            f"Hypothesis: {scenario['hypothesis']}",
            format_list_section("Evidence", scenario["evidence"]),
            "MITRE ATT&CK:\n" + "\n".join(f"- {tid}" for tid in mitre_lines),
            format_list_section("Recommended Actions", scenario["actions"]),
        ]
    )


def generate_alert_triage(count: int, start_id: int, rng: random.Random) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for i in range(count):
        scenario = dict(rng.choice(ALERT_SCENARIOS))
        n = start_id + i
        alert = {}
        for key, value in scenario["alert"].items():
            if isinstance(value, str):
                alert[key] = value.format(
                    n=n,
                    octet=rng.randint(1, 254),
                    host=rng.randint(1, 99),
                    ticket=rng.randint(1000, 9999),
                )
            else:
                alert[key] = value

        user = (
            "Investigate this alert:\n\n"
            + wrap_untrusted(json.dumps(alert, indent=2))
        )
        records.append(
            make_record(
                record_id=f"caraxis-triage-{n:05d}",
                task="alert_triage",
                user_content=user,
                assistant_content=build_triage_response(scenario),
                seed_refs=scenario["seed_refs"],
            )
        )
    return records


def generate_attack_mapping(
    techniques: list[dict[str, Any]], count: int, start_id: int, rng: random.Random
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    contexts = [
        "on a domain controller",
        "from a compromised workstation",
        "through a VPN session",
        "during off-hours activity",
        "after a phishing email was opened",
        "following a suspicious service account login",
    ]
    for i in range(count):
        technique = techniques[i % len(techniques)]
        behavior = (
            f"Case {start_id + i}: An adversary {technique['description'].lower()} "
            f"This was observed {rng.choice(contexts)} on host srv-{rng.randint(10, 99)}.internal "
            f"from source 10.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}."
        )
        user = (
            "Map the following adversary behavior to MITRE ATT&CK techniques. "
            "Explain your reasoning and suggest detection ideas.\n\n"
            + wrap_untrusted(behavior)
        )
        assistant = "\n".join(
            [
                f"MITRE ATT&CK:\n- {technique['id']} - {technique['name']}",
                "Reasoning:\n"
                f"- The behavior matches {technique['name']} under the {technique['tactic']} tactic.",
                "Detection Ideas:\n"
                f"- {technique['detection']}",
                "Recommended Actions:\n"
                f"- {technique['mitigation']}",
            ]
        )
        records.append(
            make_record(
                record_id=f"caraxis-attack-{start_id + i:05d}",
                task="attack_mapping",
                user_content=user,
                assistant_content=assistant,
                seed_refs=[technique["id"]],
            )
        )
    return records


def generate_vuln_analysis(
    cves: list[dict[str, Any]], count: int, start_id: int, rng: random.Random
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    assets = ["web-gateway-01", "vpn-concentrator-02", "file-server-07", "dc-01", "app-cluster-03"]
    for i in range(count):
        cve = dict(cves[i % len(cves)])
        cve["affected_asset"] = rng.choice(assets)
        cve["case_id"] = f"VULN-{start_id + i:05d}"
        user = (
            "Analyze this vulnerability:\n\n"
            + wrap_untrusted(json.dumps(cve, indent=2))
        )
        cwe_text = ", ".join(cve["cwe_ids"])
        assistant = "\n".join(
            [
                f"CWE: {cwe_text}",
                f"Severity: {cve['severity']}",
                "Reasoning:\n"
                f"- {cve['id']} is rated CVSS {cve['cvss_score']} and involves {cve['description']}",
                "Remediation:\n"
                f"- Apply vendor patches for {cve['id']} as soon as possible.\n"
                "- Verify affected assets and prioritize internet-exposed systems.",
            ]
        )
        records.append(
            make_record(
                record_id=f"caraxis-vuln-{start_id + i:05d}",
                task="vuln_analysis",
                user_content=user,
                assistant_content=assistant,
                seed_refs=[cve["id"]],
            )
        )
    return records


def generate_detection_explain(
    rules: list[dict[str, Any]], count: int, start_id: int, rng: random.Random
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    environments = ["production Windows fleet", "M365 tenant", "Linux SSH bastion hosts"]
    for i in range(count):
        rule = dict(rules[i % len(rules)])
        rule["review_case"] = f"DETECT-{start_id + i:05d}"
        rule["environment"] = rng.choice(environments)
        user = (
            "Explain what this Sigma detection rule detects and why:\n\n"
            + wrap_untrusted(yaml.safe_dump(rule, sort_keys=False))
        )
        mitre = rule.get("mitre", [])
        assistant = "\n".join(
            [
                f"What It Detects:\n- {rule['description']}",
                "Why It Matters:\n"
                "- This behavior is commonly associated with malicious or high-risk activity requiring investigation.",
                "False Positive Notes:\n"
                "- Tune by parent process, user role, or known administrative tooling to reduce benign noise.",
                "MITRE ATT&CK:\n" + "\n".join(f"- {tid}" for tid in mitre),
            ]
        )
        records.append(
            make_record(
                record_id=f"caraxis-detect-{start_id + i:05d}",
                task="detection_explain",
                user_content=user,
                assistant_content=assistant,
                seed_refs=[rule.get("id", rule["title"])],
            )
        )
    return records


def generate_incident_summary(
    count: int, start_id: int, rng: random.Random
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for i in range(count):
        scenario = TIMELINE_SCENARIOS[i % len(TIMELINE_SCENARIOS)]
        timeline = {
            "incident_id": f"INC-{start_id + i:05d}",
            "events": scenario["events"],
        }
        user = (
            "Summarize this security incident timeline for a SOC lead:\n\n"
            + wrap_untrusted(json.dumps(timeline, indent=2))
        )
        assistant = "\n".join(
            [
                f"Executive Summary:\n- {scenario['summary']}",
                "Impact:\n- Potential credential theft and unauthorized email collection.",
                "IOCs:\n" + "\n".join(f"- {ioc}" for ioc in scenario["iocs"]),
                "MITRE ATT&CK:\n" + "\n".join(f"- {tid}" for tid in scenario["mitre"]),
                "Recommended Actions:\n"
                "- Reset affected credentials.\n"
                "- Remove malicious mailbox rules.\n"
                "- Review mailbox and authentication logs.",
            ]
        )
        records.append(
            make_record(
                record_id=f"caraxis-summary-{start_id + i:05d}",
                task="incident_summary",
                user_content=user,
                assistant_content=assistant,
                seed_refs=scenario["seed_refs"],
            )
        )
    return records


def load_sigma_rules(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, list) else [data]


def compute_task_counts(total: int) -> dict[str, int]:
    weights = {
        "alert_triage": 0.40,
        "attack_mapping": 0.25,
        "vuln_analysis": 0.20,
        "detection_explain": 0.10,
        "incident_summary": 0.05,
    }
    counts = {task: int(total * weight) for task, weight in weights.items()}
    remainder = total - sum(counts.values())
    priority = ["alert_triage", "attack_mapping", "vuln_analysis", "detection_explain", "incident_summary"]
    idx = 0
    while remainder > 0:
        counts[priority[idx % len(priority)]] += 1
        remainder -= 1
        idx += 1
    return counts


def build_dataset(
    seeds_dir: Path,
    examples_path: Path | None,
    output_path: Path,
    total_examples: int,
    seed: int,
) -> int:
    rng = random.Random(seed)

    techniques = load_json(seeds_dir / "attack" / "techniques.json")
    cves = load_json(seeds_dir / "cve" / "samples.json")
    sigma_rules = load_sigma_rules(seeds_dir / "sigma" / "samples.yaml")

    counts = compute_task_counts(total_examples)
    records: list[dict[str, Any]] = []

    if examples_path and examples_path.exists():
        records.extend(load_jsonl(examples_path))

    start = 1
    records.extend(generate_alert_triage(counts["alert_triage"], start, rng))
    start += counts["alert_triage"]
    records.extend(generate_attack_mapping(techniques, counts["attack_mapping"], start, rng))
    start += counts["attack_mapping"]
    records.extend(generate_vuln_analysis(cves, counts["vuln_analysis"], start, rng))
    start += counts["vuln_analysis"]
    records.extend(generate_detection_explain(sigma_rules, counts["detection_explain"], start, rng))
    start += counts["detection_explain"]
    records.extend(generate_incident_summary(counts["incident_summary"], start, rng))

    return write_jsonl(output_path, records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Caraxis-Analyst dataset from seeds.")
    parser.add_argument("--seeds", type=Path, default=DEFAULT_SEEDS)
    parser.add_argument("--examples", type=Path, default=DEFAULT_EXAMPLES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--total", type=int, default=120, help="Total examples to generate")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    count = build_dataset(args.seeds, args.examples, args.output, args.total, args.seed)
    print(f"Wrote {count} records to {args.output}")


if __name__ == "__main__":
    main()
