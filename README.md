# Brand AI-Readiness Audit Marketplace

An autonomous, multi-skill agent marketplace built per the `agentskills.io` standard for **Adobe University Hackathon 2026 Round 3**. Audits websites for **AI Discoverability** (getting found and cited by AI search engines like ChatGPT, Claude, Perplexity) and **On-Site Engagement** (retaining visitors referred from AI answers).

---

## 🏛 Architecture Diagram

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
```

---

## 📊 Rubric Alignment & Round-2 Failure Modes

| Round 2 Failure Mode | Skill Responsible | Concrete Heuristics & Evidence Captured |
| :--- | :--- | :--- |
| **Crawler Gating** | `crawl-render-audit` | Parses `robots.txt` for disallow rules blocking `GPTBot`, `ClaudeBot`, `PerplexityBot`, `Bytespider`, `Google-Extended`. Emits `critical` finding with **exact line numbers**. |
| **JS Hydration Blindness** | `crawl-render-audit` | Detects when static body text is < 40 words while script payload > 10,000 chars or dynamic SPA containers (`__NEXT_DATA__`, `id="root"`) are present. Flags `high` severity. |
| **Entity Collisions** | `semantic-authority-audit` | Audits JSON-LD `<script type="application/ld+json">`. Emits a `high` severity finding with a **copy-pasteable Organization JSON-LD snippet** if missing. Flags `medium` severity if `sameAs` array is empty. |
| **Quotability Dilution** | `semantic-authority-audit` | Evaluates prose blocks under `<h2>`/`<h3>` headings. Flags `medium` severity if prose > 150 words lacks a direct declarative lead sentence for Answer Engine Optimization (AEO). |
| **On-Site Bounce** | `engagement-audit` | Audits primary `<h1>` above-the-fold orientation (missing or vague titles like "Welcome"). Calculates `%` of images missing `alt` text (>30% missing flags `medium`). Recommends sticky micro-breadcrumbs. |

---

## 🚀 Execution Guide

### 1. Run Entrypoint Audit
Run the master orchestrator script against any target website or domain:

```bash
python skills/audit-orchestrator/scripts/orchestrate.py --url example.com --output report.json
```

### 2. Validate Output Schema
Validate the generated report against mandatory contest schema rules:

```bash
python skills/audit-orchestrator/scripts/validate_report.py report.json
```

---

## 🛡 Packaging & Runtime Hygiene
- **Provider-Neutral**: Fully compliant with `agentskills.io` specification.
- **Zero Weight**: Standard Python 3 libraries (`urllib`, `re`, `html.parser`, `json`); no external pip dependencies.
- **Fast Runtime**: Execution completes in < 15 seconds per site (< 5 min ceiling).
- **Subprocess Timeout**: 35-second timeout safety net per child script for maximum resilience.
