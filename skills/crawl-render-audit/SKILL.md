---
name: crawl-render-audit
description: Audits raw bot crawlability, robots.txt directives, and client-side rendering gaps.
allowed-tools: Bash Read
---

# Crawl & Render Audit Skill

## When to use
Use when auditing a site's off-site discoverability foundation to detect whether AI assistant crawlers (e.g. `GPTBot`, `ClaudeBot`, `PerplexityBot`) are let in by `robots.txt`, XML sitemaps, `/llms.txt`, and static HTML rendering.

## Inputs
- `--url`: Target domain or URL (e.g. `example.com` or `https://example.com`).

## Procedure
1. **Load AI Bot Manifest**: Read `references/ai-bots.json` containing target User-Agents (`GPTBot`, `ClaudeBot`, `PerplexityBot`, etc.).
2. **Execute Crawl Check Script**: Run `python scripts/check_crawl.py --url <target_url>`.
3. **Robots.txt Analysis**: Check `/robots.txt` for disallow rules blocking AI crawlers from `/`. Emit `critical` severity finding if blocked.
4. **Sitemap & llms.txt Verification**: Check for `/sitemap.xml` and `/llms.txt`. Emit proactive suggestions if missing.
5. **JS Render Delta Analysis**: Calculate static HTML word count. Flag `high` severity finding if raw body text is < 35 words and dynamic SPA containers (`id="root"`, `id="__next"`) are detected.
6. **Output JSON Findings**: Print standard array of findings objects.

## Output
```json
[
  {
    "title": "AI Assistant Crawler Blocked in robots.txt",
    "severity": "critical",
    "evidence": "Found explicit disallow directives in https://example.com/robots.txt: User-agent: GPTBot | Disallow: /",
    "suggested_action": {
      "summary": "Update robots.txt to remove Disallow: / for AI retrieval crawlers.",
      "priority": "critical"
    }
  }
]
```
