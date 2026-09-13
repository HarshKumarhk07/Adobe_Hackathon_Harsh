# Offline Test Suite

This directory contains deterministic, standard-library unit tests and test fixtures for the Brand AI-Readiness Audit Marketplace.

## Running Tests

Run the full offline test suite from the repository root:

```bash
python -m unittest discover -s tests -v
```

Or run the test script directly:

```bash
python tests/test_audits.py
```

## Structure

- `test_audits.py`: Unit tests for crawlability, semantic authority, RAG quotability, on-site engagement, orchestrator formatting, and schema validation.
- `fixtures/`:
  - `robots_blocked.txt`: Sample robots.txt blocking AI retrieval crawlers.
  - `robots_allowed.txt`: Sample open robots.txt file.
  - `sample_csr.html`: Sample client-side rendered SPA markup with hydration markers and heavy JS.
  - `sample_semantic_valid.html`: Well-structured webpage with Schema.org JSON-LD, `sameAs` entity links, descriptive H1, alt-text, and jump-links.
  - `sample_semantic_missing.html`: Deficient webpage with missing structured data, diluted prose, vague H1, and missing image alt tags.
