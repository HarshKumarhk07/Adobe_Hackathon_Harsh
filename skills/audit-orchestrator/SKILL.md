---
name: audit-orchestrator
description: Entrypoint orchestrator for the Brand AI-Readiness Audit Marketplace. Coordinates domain retrieval, invokes specialized modular skills, and compiles a unified discoverability and engagement audit report.
allowed-tools: Bash Read
---

# Audit Orchestrator Skill (Entrypoint)

## When to use
Use as the designated entrypoint to audit any target website or domain for AI discoverability barriers (robots.txt blocks, missing sitemap/llms.txt, JS render gaps, missing JSON-LD schema, sameAs entity ambiguity, low RAG quotability density) and on-site visitor retention drop-offs.

## Inputs
- `--url`: Target website URL or domain name (e.g. `example.com` or `https://example.com`).

## Procedure
1. **Initialize Audit Request**: Parse target URL and resolve domain name (`site`). Capture ISO-8601 UTC timestamp (`audited_at`).
2. **Invoke Crawl-Render Audit**: Execute `python skills/crawl-render-audit/scripts/check_crawl.py --url <target_url>` with a 40s timeout.
3. **Invoke Semantic Authority Audit**: Execute `python skills/semantic-authority-audit/scripts/check_schema.py --url <target_url>` with a 40s timeout.
4. **Invoke Engagement Audit**: Execute `python skills/engagement-audit/scripts/check_engagement.py --url <target_url>` with a 40s timeout.
5. **Aggregate & Format Findings**: Assign sequential IDs (`F-001`, `F-002`, ...), count findings by severity (`total_findings`, `critical`, `high`, `medium`, `low`), and format prioritized suggested actions.
6. **Emit Audit Report**: Print schema-compliant JSON report directly to stdout.

## Output
```json
{
  "site": "example.com",
  "audited_at": "2026-09-07T21:04:11Z",
  "summary": {
    "total_findings": 6,
    "critical": 0,
    "high": 2,
    "medium": 3,
    "low": 1
  },
  "findings": [
    {
      "id": "F-001",
      "title": "XML Sitemap Missing or Inaccessible",
      "severity": "medium",
      "evidence": "GET https://example.com/sitemap.xml returned HTTP status 404",
      "suggested_action": {
        "summary": "Generate an XML sitemap and register it in robots.txt so AI crawlers can discover primary domain paths.",
        "priority": "medium"
      }
    }
  ]
}
```
