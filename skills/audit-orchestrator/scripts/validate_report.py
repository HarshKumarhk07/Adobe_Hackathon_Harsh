#!/usr/bin/env python3
"""
validate_report.py - Schema Validator for Brand AI-Readiness Audit Reports
Validates that generated JSON reports strictly conform to the required competition schema.
"""

import sys
import json
from typing import Tuple, List, Dict, Any

VALID_SEVERITIES = {"critical", "high", "medium", "low"}


def validate_report_data(data: Any) -> Tuple[bool, List[str]]:
    """Validate parsed report dictionary against required schema."""
    errors: List[str] = []

    if not isinstance(data, dict):
        return False, ["Root must be a JSON object"]

    for k in ["site", "audited_at", "summary", "findings"]:
        if k not in data:
            errors.append(f"Missing top-level field '{k}'")

    if errors:
        return False, errors

    if not isinstance(data["site"], str) or not data["site"].strip():
        errors.append("Field 'site' must be a non-empty string")

    if not isinstance(data["audited_at"], str) or not data["audited_at"].strip():
        errors.append("Field 'audited_at' must be a non-empty string")

    summary = data.get("summary", {})
    if not isinstance(summary, dict):
        errors.append("Field 'summary' must be a dictionary")
    else:
        for sk in ["total_findings", "critical", "high", "medium"]:
            if sk not in summary or not isinstance(summary[sk], int):
                errors.append(f"Summary missing integer key '{sk}'")

    findings = data.get("findings", [])
    if not isinstance(findings, list):
        errors.append("Field 'findings' must be a list")
    else:
        for idx, f in enumerate(findings):
            prefix = f"Finding[{idx}]"
            if not isinstance(f, dict):
                errors.append(f"{prefix} must be an object")
                continue

            for fk in ["id", "title", "severity", "evidence", "suggested_action"]:
                if fk not in f:
                    errors.append(f"{prefix} missing key '{fk}'")

            sev = f.get("severity")
            if sev not in VALID_SEVERITIES:
                errors.append(f"{prefix} invalid severity '{sev}'")

            sa = f.get("suggested_action", {})
            if not isinstance(sa, dict) or "summary" not in sa or "priority" not in sa:
                errors.append(f"{prefix}.suggested_action invalid structure (must contain 'summary' and 'priority')")
            elif sa.get("priority") not in VALID_SEVERITIES:
                errors.append(f"{prefix}.suggested_action invalid priority '{sa.get('priority')}'")

        if isinstance(summary, dict) and "total_findings" in summary:
            if summary.get("total_findings") != len(findings):
                errors.append(f"Summary total_findings ({summary.get('total_findings')}) != findings count ({len(findings)})")

    return len(errors) == 0, errors


def validate_report_file(filepath: str) -> Tuple[bool, List[str]]:
    """Read a JSON file and validate its schema."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return False, [f"Failed to read/parse report JSON from '{filepath}': {str(e)}"]

    return validate_report_data(data)


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: python validate_report.py <path_to_report.json>")
        sys.exit(1 if len(sys.argv) < 2 else 0)

    filepath = sys.argv[1]
    is_valid, errors = validate_report_file(filepath)
    if is_valid:
        print(f"[SUCCESS] Report '{filepath}' strictly complies with the required schema!")
        sys.exit(0)
    else:
        print(f"[FAILED] Schema validation errors for '{filepath}':")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
