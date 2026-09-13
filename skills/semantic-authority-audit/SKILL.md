---
name: semantic-authority-audit
description: Audits schema.org markup, entity disambiguation graph, and RAG quotability density.
allowed-tools: Bash Read
---

# Semantic Authority Audit Skill

## When to use
Use when auditing a site's structured data foundation, entity disambiguation graph, and RAG (Retrieval-Augmented Generation) quotability density for AI search engines.

## Inputs
- `--url`: Target domain or URL (e.g. `example.com` or `https://example.com`).

## Procedure
1. **Load Schema Templates**: Read `references/schema-templates.json` for Organization, WebSite, and FAQPage JSON-LD structures.
2. **Execute Schema Check Script**: Run `python scripts/check_schema.py --url <target_url>`.
3. **Structured Data Audit**: Inspect homepage HTML for `<script type="application/ld+json">`. Emit `high` severity finding if 0 detected, providing a populated Organization JSON-LD template.
4. **Entity Disambiguation (`sameAs`)**: Inspect JSON-LD for `sameAs` array referencing Wikidata/LinkedIn entity links. Emit `medium` severity finding if missing.
5. **RAG Quotability Density**: Evaluate paragraphs following `<h2>`/`<h3>` headings. Flag `medium` severity finding if prose blocks > 150 words lack concise declarative lead sentences (first sentence > 25 words).
6. **Output JSON Findings**: Print standard array of findings objects.

## Output
```json
[
  {
    "title": "No JSON-LD structured data detected",
    "severity": "high",
    "evidence": "Parsed homepage HTML for example.com; 0 <script type=\"application/ld+json\"> blocks found.",
    "suggested_action": {
      "summary": "Add Schema.org JSON-LD structured data to homepage.",
      "priority": "high"
    }
  }
]
```
