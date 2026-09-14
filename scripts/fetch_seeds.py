#!/usr/bin/env python3
"""Fetch and normalize MITRE ATT&CK and NVD seed files."""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "caraxis_analyst_v1" / "seeds"

ATTACK_STIX_URL = (
    "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/"
    "enterprise-attack/enterprise-attack.json"
)
NVD_CVE_URL = (
    "https://services.nvd.nist.gov/rest/json/cves/2.0"
    "?resultsPerPage=20&startIndex=0"
)


def fetch_json(url: str, headers: dict[str, str] | None = None) -> Any:
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_techniques(stix_bundle: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    techniques: list[dict[str, Any]] = []
    for obj in stix_bundle.get("objects", []):
        if obj.get("type") != "attack-pattern":
            continue
        refs = obj.get("external_references", [])
        technique_id = next(
            (ref.get("external_id") for ref in refs if ref.get("source_name") == "mitre-attack"),
            None,
        )
        if not technique_id or not technique_id.startswith("T"):
            continue
        name = obj.get("name", "")
        description = obj.get("description", "").split("\n")[0]
        tactics = [
            phase.get("phase_name", "")
            for phase in obj.get("kill_chain_phases", [])
            if phase.get("kill_chain_name") == "mitre-attack"
        ]
        techniques.append(
            {
                "id": technique_id,
                "name": name,
                "tactic": ", ".join(tactics) or "Unknown",
                "description": description,
                "detection": f"Monitor telemetry associated with {name.lower()}.",
                "mitigation": f"Apply controls that reduce risk from {name.lower()}.",
            }
        )
        if len(techniques) >= limit:
            break
    return techniques


def normalize_cves(nvd_payload: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in nvd_payload.get("vulnerabilities", []):
        cve = item.get("cve", {})
        cve_id = cve.get("id")
        descriptions = cve.get("descriptions", [])
        description = next(
            (d.get("value", "") for d in descriptions if d.get("lang") == "en"),
            "",
        )
        metrics = cve.get("metrics", {})
        cvss_score = None
        for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            metric_list = metrics.get(key, [])
            if metric_list:
                cvss_score = metric_list[0].get("cvssData", {}).get("baseScore")
                break
        weaknesses = []
        for weakness in cve.get("weaknesses", []):
            for desc in weakness.get("description", []):
                value = desc.get("value", "")
                if value.startswith("CWE-"):
                    weaknesses.append(value)
        severity = "critical"
        if cvss_score is not None:
            if cvss_score < 4.0:
                severity = "low"
            elif cvss_score < 7.0:
                severity = "medium"
            elif cvss_score < 9.0:
                severity = "high"
        rows.append(
            {
                "id": cve_id,
                "description": description,
                "cvss_score": cvss_score,
                "cwe_ids": weaknesses[:3],
                "severity": severity,
            }
        )
        if len(rows) >= limit:
            break
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Caraxis seed files.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--attack-limit", type=int, default=100)
    parser.add_argument("--cve-limit", type=int, default=50)
    parser.add_argument("--nvd-api-key", type=str, default=None)
    args = parser.parse_args()

    attack_dir = args.output_dir / "attack"
    cve_dir = args.output_dir / "cve"
    attack_dir.mkdir(parents=True, exist_ok=True)
    cve_dir.mkdir(parents=True, exist_ok=True)

    print("Fetching MITRE ATT&CK STIX...")
    stix = fetch_json(ATTACK_STIX_URL)
    techniques = normalize_techniques(stix, args.attack_limit)
    attack_path = attack_dir / "techniques.json"
    attack_path.write_text(json.dumps(techniques, indent=2), encoding="utf-8")
    print(f"Wrote {len(techniques)} techniques to {attack_path}")

    print("Fetching recent CVEs from NVD...")
    headers = {}
    if args.nvd_api_key:
        headers["apiKey"] = args.nvd_api_key
    nvd = fetch_json(NVD_CVE_URL, headers=headers)
    cves = normalize_cves(nvd, args.cve_limit)
    cve_path = cve_dir / "samples.json"
    cve_path.write_text(json.dumps(cves, indent=2), encoding="utf-8")
    print(f"Wrote {len(cves)} CVEs to {cve_path}")
    print("Done. Re-run scripts/build_dataset.py to regenerate training data.")
    time.sleep(1)


if __name__ == "__main__":
    main()
