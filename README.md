# Brand AI-Readiness Audit Marketplace

An autonomous, modular multi-skill agent marketplace built to the [`agentskills.io`](https://agentskills.io) standard for the **Adobe University Hackathon 2026**. Audits web domains for **AI Discoverability** (indexability and citation by AI retrieval engines such as ChatGPT, Claude, and Perplexity) and **On-Site Engagement** (context retention for visitors arriving via deep-linked AI citations).

---

## Architecture & Data Flow

```
                             +-----------------------------------+
                             |     marketplace.json (Manifest)   |
                             +-----------------------------------+
                                               |
                                               v
                             +-----------------------------------+
                             |  audit-orchestrator [ENTRYPOINT]  |
                             |      (orchestrate.py script)      |
                             +-----------------------------------+
                                    /          |          \
                                   /           |           \
                                  /            |            \
                                 v             v             v
             +-----------------------+ +-----------------------+ +-----------------------+
             |  crawl-render-audit   | |semantic-authority-audit| |   engagement-audit    |
             |   (check_crawl.py)    | |   (check_schema.py)   | | (check_engagement.py) |
             +-----------------------+ +-----------------------+ +-----------------------+
             | - robots.txt AI bots  | | - JSON-LD validation  | | - H1 orientation      |
             | - Line-num disallows  | | - copy-paste snippet  | | - Facts in images     |
             | - sitemap / llms.txt  | | - sameAs entity graph | | - Alt text coverage   |
             | - JS Hydration Gap    | | - RAG Quotability     | | - Deep-link navigation|
             +-----------------------+ +-----------------------+ +-----------------------+
                                  \            |            /
                                   \           |           /
                                    v          v          v
                             +-----------------------------------+
                             |   Unified Schema JSON Audit       |
                             |       Report (stdout / file)      |
                             +-----------------------------------+
                                               |
                                               v
                             +-----------------------------------+
                             |    validate_report.py (Checks)    |
                             +-----------------------------------+
```

---

## Rubric Alignment & Failure Modes

| Failure Mode | Skill Responsible | Concrete Heuristics & Evidence Captured |
| :--- | :--- | :--- |
| **Crawler Gating** | `crawl-render-audit` | Parses `robots.txt` for disallow directives blocking `GPTBot`, `ClaudeBot`, `PerplexityBot`, `Bytespider`, `Google-Extended`. Emits `critical` severity finding with **exact line numbers**. |
| **JS Hydration Blindness** | `crawl-render-audit` | Detects when static body text is < 40 words while script payload > 10,000 chars or dynamic SPA framework markers (`__NEXT_DATA__`, `id="root"`) are present. Flags `high` severity. |
| **Entity Collisions** | `semantic-authority-audit` | Audits JSON-LD `<script type="application/ld+json">`. Emits a `high` severity finding with a **copy-pasteable Organization JSON-LD snippet** if missing. Flags `medium` severity if `sameAs` array is missing. |
| **Quotability Dilution** | `semantic-authority-audit` | Evaluates prose blocks under `<h2>`/`<h3>` headings. Flags `medium` severity if prose > 150 words lacks a direct declarative lead sentence for Answer Engine Optimization (AEO). |
| **On-Site Bounce** | `engagement-audit` | Audits primary `<h1>` above-the-fold orientation (missing or vague titles like "Welcome"). Calculates `%` of images missing `alt` text (>30% missing flags `medium`). Evaluates multi-section pages for in-page jump-links and breadcrumbs. |

---

## Prerequisites

- **Python**: 3.8+ (Zero external dependencies; uses pure Python standard library: `urllib`, `html.parser`, `subprocess`, `json`, `argparse`, `unittest`).

---

## Execution Guide

### 1. Run Complete Audit Orchestrator
Run the entrypoint orchestrator against any target website or domain:

```bash
python skills/audit-orchestrator/scripts/orchestrate.py --url https://example.com --output report.json
```

### 2. Validate Output Schema
Validate the generated JSON report against competition schema rules:

```bash
python skills/audit-orchestrator/scripts/validate_report.py report.json
```

### 3. Run Individual Skills Standalone
Each sub-skill can be executed independently:

```bash
# Crawl & JS Render Audit
python skills/crawl-render-audit/scripts/check_crawl.py --url https://example.com

# Semantic Authority & RAG Quotability Audit
python skills/semantic-authority-audit/scripts/check_schema.py --url https://example.com

# On-Site Engagement & Retention Audit
python skills/engagement-audit/scripts/check_engagement.py --url https://example.com
```

### 4. Run Offline Test Suite
Run all 22 deterministic offline unit tests without network connectivity:

```bash
python -m unittest discover -s tests -v
```

---

## Example Output Schema

```json
{
  "site": "example.com",
  "audited_at": "2026-09-13T14:30:29Z",
  "summary": {
    "total_findings": 5,
    "critical": 0,
    "high": 1,
    "medium": 3,
    "low": 1
  },
  "findings": [
    {
      "id": "F-001",
      "title": "Unreachable or Missing robots.txt Directive File",
      "severity": "medium",
      "evidence": "GET https://example.com/robots.txt returned HTTP status 404",
      "suggested_action": {
        "summary": "Publish a valid robots.txt file at domain root establishing explicit permissions for AI assistant crawlers.",
        "priority": "medium"
      }
    },
    {
      "id": "F-004",
      "title": "No JSON-LD structured data detected",
      "severity": "high",
      "evidence": "Parsed homepage HTML for example.com; 0 <script type=\"application/ld+json\"> blocks found.",
      "suggested_action": {
        "summary": "Add Schema.org JSON-LD structured data. Active copy-pasteable snippet: {\"@context\": \"https://schema.org\", \"@type\": \"Organization\", \"name\": \"example.com\", \"url\": \"https://example.com\", \"logo\": \"https://example.com/logo.png\", \"sameAs\": [\"https://www.wikidata.org/wiki/Q00000\", \"https://www.linkedin.com/company/example\", \"https://twitter.com/example\"]}",
        "priority": "high"
      }
    }
  ]
}
```

---

## Runtime & Engineering Properties

- **Provider-Neutral**: Fully compliant with the `agentskills.io` marketplace manifest standard.
- **Zero External Dependencies**: Pure standard library (`urllib`, `html.parser`, `subprocess`, `json`, `argparse`).
- **Subprocess Isolation**: 35-second execution timeout safety net per child skill with error-wrapping preventing orchestrator crashes.
- **Deterministic Offline Testing**: Full unit test coverage (`tests/test_audits.py`) covering all heuristics with static HTML/robots.txt fixtures.

---

## Project Limitations

- **Static Scraping**: The auditor evaluates raw HTTP response payloads and static HTML markup. It does not execute client-side JavaScript in a headless browser (Puppeteer/Playwright); instead, it explicitly detects and flags when JavaScript hydration blinds non-JS AI crawlers.
- **WAF / Anti-Bot Challenges**: Targets behind strict anti-bot systems (e.g. Cloudflare Turnstile, CAPTCHAs, or 403 Forbidden challenge pages) will return standard HTTP status codes and be flagged accordingly as inaccessible or restricted.
