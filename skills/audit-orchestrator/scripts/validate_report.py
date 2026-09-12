#!/usr/bin/env python3
"""
validate_report.py - Schema Validator for Brand AI-Readiness Audit Reports
"""

import sys
import json
import re

def validate_report_file(filepath):
    errors = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return False, [f"Failed to read/parse report JSON: {str(e)}"]

    if not isinstance(data, dict):
        return False, ["Root must be a JSON object"]

    for k in ["site", "audited_at", "summary", "findings"]:
        if k not in data:
            errors.append(f"Missing top-level field '{k}'")

    if errors:
        return False, errors

    if not isinstance(data["site"], str) or not data["site"]:
        errors.append("Field 'site' must be a non-empty string")

    summary = data.get("summary", {})
    for sk in ["total_findings", "critical", "high", "medium"]:
        if sk not in summary or not isinstance(summary[sk], int):
            errors.append(f"Summary missing integer key '{sk}'")

    findings = data.get("findings", [])
    if not isinstance(findings, list):
        errors.append("Field 'findings' must be a list")
    else:
        valid_sevs = {"critical", "high", "medium", "low"}
        for idx, f in enumerate(findings):
            prefix = f"Finding[{idx}]"
            for fk in ["id", "title", "severity", "evidence", "suggested_action"]:
                if fk not in f:
                    errors.append(f"{prefix} missing key '{fk}'")
            if f.get("severity") not in valid_sevs:
                errors.append(f"{prefix} invalid severity '{f.get('severity')}'")
            sa = f.get("suggested_action", {})
            if not isinstance(sa, dict) or "summary" not in sa or "priority" not in sa:
                errors.append(f"{prefix}.suggested_action invalid structure")
            elif sa.get("priority") not in valid_sevs:
                errors.append(f"{prefix}.suggested_action invalid priority '{sa.get('priority')}'")

        if summary.get("total_findings") != len(findings):
            errors.append(f"Summary total_findings ({summary.get('total_findings')}) != findings count ({len(findings)})")

    return len(errors) == 0, errors

def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_report.py <path_to_report.json>")
        sys.exit(1)
    is_valid, errors = validate_report_file(sys.argv[1])
    if is_valid:
        print(f"[SUCCESS] Report '{sys.argv[1]}' strictly complies with the required schema!")
        sys.exit(0)
    else:
        print(f"[FAILED] Schema validation errors for '{sys.argv[1]}': {errors}")
        sys.exit(1)

if __name__ == "__main__":
    main()
