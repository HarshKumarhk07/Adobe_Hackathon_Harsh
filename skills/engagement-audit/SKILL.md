---
name: engagement-audit
description: Audits on-site orientation, visual text isolation, and visitor retention factors.
allowed-tools: Bash Read
---

# Engagement Audit Skill

## When to use
Use when auditing on-site visitor retention, primary heading orientation clarity, machine-readable image alt text coverage, and deep-linked referral orientation signals.

## Inputs
- `--url`: Target domain or URL (e.g. `example.com` or `https://example.com`).

## Procedure
1. **Load UX Guidelines**: Read `references/ux-rules.md` for visitor orientation and machine-readable image standards.
2. **Execute Engagement Check Script**: Run `python scripts/check_engagement.py --url <target_url>`.
3. **Above-the-Fold Orientation Check**: Inspect DOM for `<h1>`. Emit `high` severity finding if missing or `medium` severity if vague.
4. **Facts Locked in Non-Text**: Inspect all `<img>` tags for missing or trivial `alt` attributes. Flag `medium` severity finding if > 30% are missing or trivial.
5. **Proactive Retention Enhancement**: Emit a `low` proactive suggestion for sticky micro-breadcrumbs and anchor jump-links.
6. **Output JSON Findings**: Print standard array of findings objects.

## Output
```json
[
  {
    "title": "Missing Primary Heading: Visitors arriving via deep links cannot confirm context",
    "severity": "high",
    "evidence": "Parsed HTML DOM; 0 <h1> heading elements found on homepage.",
    "suggested_action": {
      "summary": "Add a clear, descriptive <h1> heading at the top of the body.",
      "priority": "high"
    }
  }
]
```
