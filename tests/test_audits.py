#!/usr/bin/env python3
"""
test_audits.py - Offline Deterministic Test Suite
Tests all audit logic, parsing functions, orchestrator aggregation, and schema validator
using local static fixtures without network dependencies.
"""

import os
import sys
import unittest
import importlib.util
from typing import Any

# Resolve paths
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(TESTS_DIR, ".."))
FIXTURES_DIR = os.path.join(TESTS_DIR, "fixtures")


def load_module(module_name: str, relative_path: str) -> Any:
    """Dynamically load a Python module from a file path accommodating hyphenated directory names."""
    file_path = os.path.join(PROJECT_ROOT, *relative_path.split("/"))
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Load sub-skill modules
crawl_mod = load_module("check_crawl", "skills/crawl-render-audit/scripts/check_crawl.py")
schema_mod = load_module("check_schema", "skills/semantic-authority-audit/scripts/check_schema.py")
engagement_mod = load_module("check_engagement", "skills/engagement-audit/scripts/check_engagement.py")
orchestrate_mod = load_module("orchestrate", "skills/audit-orchestrator/scripts/orchestrate.py")
validate_mod = load_module("validate_report", "skills/audit-orchestrator/scripts/validate_report.py")


def read_fixture(filename: str) -> str:
    with open(os.path.join(FIXTURES_DIR, filename), "r", encoding="utf-8") as f:
        return f.read()


class TestCrawlRenderAudit(unittest.TestCase):
    """Tests for Crawl & JS Render Audit heuristics."""

    def test_robots_blocked_detected(self) -> None:
        robots_content = read_fixture("robots_blocked.txt")
        findings = crawl_mod.analyze_robots_txt(robots_content, "https://test.com/robots.txt")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "critical")
        self.assertIn("AI Assistant Crawler Blocked", findings[0]["title"])
        self.assertIn("GPTBot", findings[0]["evidence"])
        self.assertIn("Line", findings[0]["evidence"])

    def test_robots_allowed_no_findings(self) -> None:
        robots_content = read_fixture("robots_allowed.txt")
        findings = crawl_mod.analyze_robots_txt(robots_content, "https://test.com/robots.txt")
        self.assertEqual(len(findings), 0)

    def test_sitemap_and_llms_missing(self) -> None:
        findings = crawl_mod.analyze_sitemap_and_llms(
            base_url="https://test.com",
            sitemap_status=404,
            sitemap_has_content=False,
            llms_status=404,
            llms_has_content=False
        )
        self.assertEqual(len(findings), 2)
        titles = [f["title"] for f in findings]
        self.assertIn("XML Sitemap Missing or Inaccessible", titles)
        self.assertIn("Proactive Opportunity: Missing llms.txt Markdown Context Manifest", titles)

    def test_sitemap_and_llms_present(self) -> None:
        findings = crawl_mod.analyze_sitemap_and_llms(
            base_url="https://test.com",
            sitemap_status=200,
            sitemap_has_content=True,
            llms_status=200,
            llms_has_content=True
        )
        self.assertEqual(len(findings), 0)

    def test_csr_hydration_gap_detected(self) -> None:
        html = read_fixture("sample_csr.html")
        findings = crawl_mod.analyze_html_render_gap(html)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "high")
        self.assertIn("Client-Side Render Gap", findings[0]["title"])

    def test_ssr_valid_render_no_gap(self) -> None:
        html = read_fixture("sample_semantic_valid.html")
        findings = crawl_mod.analyze_html_render_gap(html)
        self.assertEqual(len(findings), 0)


class TestSemanticAuthorityAudit(unittest.TestCase):
    """Tests for Semantic Authority & RAG Quotability heuristics."""

    def test_valid_json_ld_and_sameas(self) -> None:
        html = read_fixture("sample_semantic_valid.html")
        findings = schema_mod.analyze_html_semantic(html, "acme-analytics.com")
        self.assertEqual(len(findings), 0)

    def test_missing_json_ld_detected(self) -> None:
        html = read_fixture("sample_semantic_missing.html")
        findings = schema_mod.analyze_html_semantic(html, "oldcompany.com")
        missing_ld = [f for f in findings if "No JSON-LD structured data detected" in f["title"]]
        self.assertEqual(len(missing_ld), 1)
        self.assertEqual(missing_ld[0]["severity"], "high")
        self.assertIn("Schema.org", missing_ld[0]["suggested_action"]["summary"])

    def test_sameas_missing_when_json_ld_present(self) -> None:
        parsed_ld = [{"@context": "https://schema.org", "@type": "Organization", "name": "Test Org"}]
        findings = schema_mod.analyze_json_ld(parsed_ld, "testorg.com")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "medium")
        self.assertIn("sameAs", findings[0]["title"])

    def test_rag_quotability_diluted_prose(self) -> None:
        html = read_fixture("sample_semantic_missing.html")
        findings = schema_mod.analyze_html_semantic(html, "oldcompany.com")
        rag_findings = [f for f in findings if "Low Quotability Density" in f["title"]]
        self.assertEqual(len(rag_findings), 1)
        self.assertEqual(rag_findings[0]["severity"], "medium")

    def test_load_schema_templates(self) -> None:
        template = schema_mod.load_schema_templates("custom-domain.org")
        self.assertEqual(template.get("@type"), "Organization")
        self.assertEqual(template.get("name"), "custom-domain.org")


class TestEngagementAudit(unittest.TestCase):
    """Tests for On-Site Engagement & Retention heuristics."""

    def test_h1_valid_descriptive(self) -> None:
        findings = engagement_mod.analyze_headings(["Acme AI Analytics Enterprise Intelligence Suite"])
        self.assertEqual(len(findings), 0)

    def test_h1_vague_headline(self) -> None:
        findings = engagement_mod.analyze_headings(["Welcome"])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "medium")
        self.assertIn("Vague Primary Heading", findings[0]["title"])

    def test_h1_missing(self) -> None:
        findings = engagement_mod.analyze_headings([])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "high")
        self.assertIn("Missing Primary Heading", findings[0]["title"])

    def test_image_alt_coverage_deficit(self) -> None:
        images = [
            ("/img/banner1.jpg", "banner"),  # trivial
            ("/img/graphic.png", None),      # missing
            ("/img/photo.jpg", "photo")       # trivial
        ]
        findings = engagement_mod.analyze_image_alts(images)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "medium")
        self.assertIn("Information locked in non-text media", findings[0]["title"])

    def test_image_alt_coverage_sufficient(self) -> None:
        images = [
            ("/img/arch.png", "Detailed architecture diagram of the ingestion pipeline")
        ]
        findings = engagement_mod.analyze_image_alts(images)
        self.assertEqual(len(findings), 0)

    def test_deep_link_retention_flagged_when_needed(self) -> None:
        findings = engagement_mod.analyze_deep_link_retention(
            section_headings_count=3,
            anchor_jump_links_count=0,
            has_breadcrumbs=False
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("Deep-Link Visitor Retention", findings[0]["title"])

    def test_deep_link_retention_not_flagged_when_has_jump_links(self) -> None:
        findings = engagement_mod.analyze_deep_link_retention(
            section_headings_count=3,
            anchor_jump_links_count=2,
            has_breadcrumbs=False
        )
        self.assertEqual(len(findings), 0)

    def test_deep_link_retention_not_flagged_when_has_breadcrumbs(self) -> None:
        findings = engagement_mod.analyze_deep_link_retention(
            section_headings_count=3,
            anchor_jump_links_count=0,
            has_breadcrumbs=True
        )
        self.assertEqual(len(findings), 0)


class TestOrchestratorAndValidator(unittest.TestCase):
    """Tests for Orchestrator formatting and Report Validator schema compliance."""

    def test_extract_domain(self) -> None:
        self.assertEqual(orchestrate_mod.extract_domain("https://sub.example.com/path?q=1"), "sub.example.com")
        self.assertEqual(orchestrate_mod.extract_domain("example.com"), "example.com")
        self.assertEqual(orchestrate_mod.extract_domain("http://example.com:8080/"), "example.com")

    def test_format_audit_report(self) -> None:
        raw_findings = [
            {
                "title": "Issue A",
                "severity": "critical",
                "evidence": "Evidence A",
                "suggested_action": {"summary": "Fix A", "priority": "critical"}
            },
            {
                "title": "Issue B",
                "severity": "medium",
                "evidence": "Evidence B",
                "suggested_action": {"summary": "Fix B", "priority": "medium"}
            }
        ]
        report = orchestrate_mod.format_audit_report("test.com", raw_findings, audited_at="2026-09-13T12:00:00Z")
        self.assertEqual(report["site"], "test.com")
        self.assertEqual(report["summary"]["total_findings"], 2)
        self.assertEqual(report["summary"]["critical"], 1)
        self.assertEqual(report["summary"]["medium"], 1)
        self.assertEqual(report["findings"][0]["id"], "F-001")
        self.assertEqual(report["findings"][1]["id"], "F-002")

        is_valid, errors = validate_mod.validate_report_data(report)
        self.assertTrue(is_valid, f"Validation errors: {errors}")

    def test_validator_detects_malformed_report(self) -> None:
        bad_report = {"site": "test.com"}  # Missing audited_at, summary, findings
        is_valid, errors = validate_mod.validate_report_data(bad_report)
        self.assertFalse(is_valid)
        self.assertTrue(len(errors) > 0)


if __name__ == "__main__":
    unittest.main()
