#!/usr/bin/env python3
"""
orchestrate.py - Master Entrypoint Orchestrator Script
Coordinates crawl-render-audit, semantic-authority-audit, and engagement-audit sub-skills via subprocess
with a 35s timeout per child script. Aggregates findings into a schema-compliant JSON report.
"""

import sys
import os
import json
import argparse
import subprocess
import urllib.parse
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MARKETPLACE_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
SKILLS_DIR = os.path.join(MARKETPLACE_ROOT, "skills")

# Authoritative named constants
DEFAULT_SUBPROCESS_TIMEOUT_SECONDS = 35
VALID_SEVERITIES = {"critical", "high", "medium", "low"}


def extract_domain(url_str: str) -> str:
    """Extract clean domain name from URL string or fallback to default."""
    if not url_str:
        return "example.com"
    if not url_str.startswith("http://") and not url_str.startswith("https://"):
        url_str = "https://" + url_str
    parsed = urllib.parse.urlparse(url_str)
    domain = parsed.netloc or parsed.path.split('/')[0]
    return domain.split(":")[0]


def run_subskill(script_path: str, target_url: str, timeout: int = DEFAULT_SUBPROCESS_TIMEOUT_SECONDS) -> List[Dict[str, Any]]:
    """Execute a sub-skill script via subprocess with timeout protection."""
    if not os.path.exists(script_path):
        return [{
            "title": f"Sub-skill Missing Script Warning: {os.path.basename(script_path)}",
            "severity": "medium",
            "evidence": f"Expected sub-skill script not found at path: {script_path}",
            "suggested_action": {
                "summary": "Verify marketplace skill installation and file integrity.",
                "priority": "medium"
            }
        }]

    try:
        cmd = [sys.executable, script_path, "--url", target_url]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout.strip())
            if isinstance(data, list):
                return data
        elif res.returncode != 0:
            err_msg = res.stderr.strip() or f"Process exited with return code {res.returncode}"
            return [{
                "title": f"Sub-skill Execution Error: {os.path.basename(script_path)}",
                "severity": "medium",
                "evidence": f"Subprocess exited abnormally: {err_msg}",
                "suggested_action": {
                    "summary": "Check sub-skill script output and target endpoint accessibility.",
                    "priority": "medium"
                }
            }]
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
    except json.JSONDecodeError as jde:
        return [{
            "title": f"Sub-skill Malformed Output Error: {os.path.basename(script_path)}",
            "severity": "medium",
            "evidence": f"Failed to parse JSON output from sub-skill: {str(jde)}",
            "suggested_action": {
                "summary": "Ensure sub-skill emits valid JSON format to stdout.",
                "priority": "medium"
            }
        }]
    except Exception as e:
        return [{
            "title": f"Sub-skill Invocation Exception: {os.path.basename(script_path)}",
            "severity": "medium",
            "evidence": f"Subprocess invocation exception: {str(e)}",
            "suggested_action": {
                "summary": "Verify target domain accessibility and Python runtime environment.",
                "priority": "medium"
            }
        }]
    return []


def format_audit_report(
    domain_name: str,
    raw_findings: List[Dict[str, Any]],
    audited_at: Optional[str] = None
) -> Dict[str, Any]:
    """Aggregate raw findings, assign sequential IDs, tally severities, and generate report dict."""
    if audited_at is None:
        audited_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    formatted_findings: List[Dict[str, Any]] = []
    sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    for idx, f in enumerate(raw_findings, start=1):
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

    return {
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


def orchestrate_audit(
    target_url: str,
    output_filepath: Optional[str] = None,
    timeout: int = DEFAULT_SUBPROCESS_TIMEOUT_SECONDS
) -> Tuple[Dict[str, Any], str]:
    """Run full multi-skill audit pipeline against a target domain."""
    domain_name = extract_domain(target_url)

    sub_scripts = [
        os.path.join(SKILLS_DIR, "crawl-render-audit", "scripts", "check_crawl.py"),
        os.path.join(SKILLS_DIR, "semantic-authority-audit", "scripts", "check_schema.py"),
        os.path.join(SKILLS_DIR, "engagement-audit", "scripts", "check_engagement.py")
    ]

    all_raw_findings: List[Dict[str, Any]] = []
    for s_path in sub_scripts:
        findings = run_subskill(s_path, target_url, timeout=timeout)
        all_raw_findings.extend(findings)

    report = format_audit_report(domain_name, all_raw_findings)
    report_json_str = json.dumps(report, indent=2)

    if output_filepath:
        output_dir = os.path.dirname(os.path.abspath(output_filepath))
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(output_filepath, "w", encoding="utf-8") as out_f:
            out_f.write(report_json_str)

    return report, report_json_str


def main() -> None:
    parser = argparse.ArgumentParser(description="Brand AI-Readiness Audit Entrypoint Orchestrator")
    parser.add_argument("--url", default="example.com", help="Target URL or domain to audit")
    parser.add_argument("--output", default=None, help="Optional output JSON filepath to save the report")
    parser.add_argument("--timeout", type=int, default=DEFAULT_SUBPROCESS_TIMEOUT_SECONDS, help="Timeout in seconds per sub-skill")
    args = parser.parse_args()

    _, report_json_str = orchestrate_audit(args.url, output_filepath=args.output, timeout=args.timeout)
    print(report_json_str)


if __name__ == "__main__":
    main()
