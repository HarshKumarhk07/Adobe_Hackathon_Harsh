#!/usr/bin/env python3
"""
orchestrate.py - Resilient Master Entrypoint Orchestrator Script
Executes crawl-render-audit, semantic-authority-audit, and engagement-audit sub-skills via subprocess
with a strict 35s timeout per child script. Catches execution & network errors gracefully, guaranteeing valid JSON schema output.
"""

import sys
import os
import json
import argparse
import subprocess
import urllib.parse
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MARKETPLACE_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
SKILLS_DIR = os.path.join(MARKETPLACE_ROOT, "skills")

def extract_domain(url_str):
    if not url_str:
        return "example.com"
    if not url_str.startswith("http://") and not url_str.startswith("https://"):
        url_str = "https://" + url_str
    parsed = urllib.parse.urlparse(url_str)
    domain = parsed.netloc or parsed.path.split('/')[0]
    return domain.split(":")[0]

def run_subskill(script_path, target_url, timeout=35):
    if not os.path.exists(script_path):
        return []
    try:
        cmd = [sys.executable, script_path, "--url", target_url]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout.strip())
            if isinstance(data, list):
                return data
    except subprocess.TimeoutExpired:
        return [{
            "title": f"Sub-skill Timeout Warning: {os.path.basename(script_path)}",
            "severity": "medium",
            "evidence": f"Subprocess timed out after {timeout} seconds fetching {target_url}",
            "suggested_action": {
                "summary": "Ensure target endpoint responds within standard network latency boundaries.",
                "priority": "medium"
            }
        }]
    except Exception as e:
        return [{
            "title": f"Sub-skill Execution Error: {os.path.basename(script_path)}",
            "severity": "medium",
            "evidence": f"Subprocess invocation exception: {str(e)}",
            "suggested_action": {
                "summary": "Verify target domain accessibility and Python runtime environment.",
                "priority": "medium"
            }
        }]
    return []

def orchestrate_audit(target_url, output_filepath=None):
    domain_name = extract_domain(target_url)
    audited_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    sub_scripts = [
        os.path.join(SKILLS_DIR, "crawl-render-audit", "scripts", "check_crawl.py"),
        os.path.join(SKILLS_DIR, "semantic-authority-audit", "scripts", "check_schema.py"),
        os.path.join(SKILLS_DIR, "engagement-audit", "scripts", "check_engagement.py")
    ]

    all_raw_findings = []
    for s_path in sub_scripts:
        findings = run_subskill(s_path, target_url, timeout=35)
        all_raw_findings.extend(findings)

    # Format findings with sequential IDs (F-001, F-002, ...)
    formatted_findings = []
    sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    for idx, f in enumerate(all_raw_findings, start=1):
        fid = f"F-{idx:03d}"
        sev = str(f.get("severity", "medium")).lower()
        if sev not in sev_counts:
            sev = "medium"
        sev_counts[sev] += 1

        action = f.get("suggested_action", {})
        action_summary = action.get("summary", "Review and fix detected defect.")
        action_priority = str(action.get("priority", sev)).lower()
        if action_priority not in sev_counts:
            action_priority = sev

        formatted_findings.append({
            "id": fid,
            "title": str(f.get("title", "Detected Audit Issue")),
            "severity": sev,
            "evidence": str(f.get("evidence", "Evidence captured during audit run.")),
            "suggested_action": {
                "summary": str(action_summary),
                "priority": action_priority
            }
        })

    report = {
        "site": domain_name,
        "audited_at": audited_at,
        "summary": {
            "total_findings": len(formatted_findings),
            "critical": sev_counts["critical"],
            "high": sev_counts["high"],
            "medium": sev_counts["medium"],
            "low": sev_counts["low"]
        },
        "findings": formatted_findings
    }

    report_json_str = json.dumps(report, indent=2)

    if output_filepath:
        os.makedirs(os.path.dirname(os.path.abspath(output_filepath)), exist_ok=True)
        with open(output_filepath, "w", encoding="utf-8") as out_f:
            out_f.write(report_json_str)

    return report, report_json_str

def main():
    parser = argparse.ArgumentParser(description="Brand AI-Readiness Audit Entrypoint Orchestrator")
    parser.add_argument("--url", default="example.com", help="Target URL or domain to audit")
    parser.add_argument("--output", default=None, help="Optional output JSON filepath")
    args, unknown = parser.parse_known_args()

    target = args.url if args.url else (sys.argv[1] if len(sys.argv) > 1 else "example.com")
    report, report_json_str = orchestrate_audit(target, output_filepath=args.output)
    
    print(report_json_str)

if __name__ == "__main__":
    main()
