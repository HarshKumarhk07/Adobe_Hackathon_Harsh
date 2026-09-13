#!/usr/bin/env python3
"""
check_schema.py - Semantic Authority & RAG Quotability Audit Sub-Skill
Audits Schema.org JSON-LD markup, entity sameAs disambiguation graph, and RAG quotability density.
"""

import sys
import os
import json
import argparse
import urllib.request
import urllib.parse
import urllib.error
from html.parser import HTMLParser
from typing import List, Dict, Any, Tuple, Optional, Set

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REF_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "references"))

# Authoritative named constants
RAG_PROSE_WORD_THRESHOLD = 150
RAG_LEAD_SENTENCE_MAX_WORDS = 25
DEFAULT_FETCH_TIMEOUT = 5


def load_schema_templates(domain_name: str) -> Dict[str, Any]:
    """Load and populate fallback JSON-LD Schema templates."""
    templates_file = os.path.join(REF_DIR, "schema-templates.json")
    org_template = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": domain_name,
        "url": f"https://{domain_name}",
        "sameAs": [
            f"https://www.wikidata.org/wiki/Q_{domain_name.replace('.', '_')}",
            f"https://www.linkedin.com/company/{domain_name.split('.')[0]}"
        ]
    }
    if os.path.exists(templates_file):
        try:
            with open(templates_file, "r", encoding="utf-8") as f:
                content = f.read()
                content = content.replace("{{DOMAIN_NAME}}", domain_name).replace("{{DOMAIN_KEY}}", domain_name.split('.')[0])
                data = json.loads(content)
                if "Organization" in data:
                    org_template = data["Organization"]
        except Exception:
            pass
    return org_template


class HeadingProseParser(HTMLParser):
    """Parser to extract JSON-LD script content and heading-to-paragraph prose pairs."""

    def __init__(self) -> None:
        super().__init__()
        self.json_ld_raw: List[str] = []
        self.in_json_ld = False
        self.current_json_ld: List[str] = []
        self.heading_paragraphs: List[Tuple[str, str, str]] = []  # (tag, heading_text, p_text)
        self.current_heading: Optional[str] = None
        self.current_heading_text: List[str] = []
        self.in_heading = False
        self.in_paragraph = False
        self.current_paragraph_text: List[str] = []
        self.last_heading: Optional[Tuple[str, str]] = None

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        tag_lower = tag.lower()
        attr_dict = {k.lower(): v for k, v in attrs if k and v}

        if tag_lower == 'script' and attr_dict.get('type') == 'application/ld+json':
            self.in_json_ld = True
            self.current_json_ld = []

        elif tag_lower in ['h2', 'h3']:
            self.in_heading = True
            self.current_heading = tag_lower
            self.current_heading_text = []

        elif tag_lower == 'p':
            self.in_paragraph = True
            self.current_paragraph_text = []

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower == 'script' and self.in_json_ld:
            self.in_json_ld = False
            text = "".join(self.current_json_ld).strip()
            if text:
                self.json_ld_raw.append(text)

        elif tag_lower in ['h2', 'h3'] and self.in_heading:
            self.in_heading = False
            if self.current_heading:
                self.last_heading = (self.current_heading, " ".join(self.current_heading_text).strip())

        elif tag_lower == 'p' and self.in_paragraph:
            self.in_paragraph = False
            p_text = " ".join(self.current_paragraph_text).strip()
            if self.last_heading and p_text:
                self.heading_paragraphs.append((self.last_heading[0], self.last_heading[1], p_text))

    def handle_data(self, data: str) -> None:
        if self.in_json_ld:
            self.current_json_ld.append(data)
        if self.in_heading:
            self.current_heading_text.append(data.strip())
        if self.in_paragraph:
            self.current_paragraph_text.append(data.strip())


def fetch_url(url: str, timeout: int = DEFAULT_FETCH_TIMEOUT) -> str:
    """Safely fetch HTML content from URL."""
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception:
        return ""


def analyze_json_ld(parsed_json_ld: List[Any], domain_name: str) -> List[Dict[str, Any]]:
    """Audit JSON-LD blocks for presence and entity disambiguation (sameAs links)."""
    findings: List[Dict[str, Any]] = []

    if not parsed_json_ld:
        org_template = load_schema_templates(domain_name)
        snippet_json = json.dumps(org_template)
        findings.append({
            "title": "No JSON-LD structured data detected",
            "severity": "high",
            "evidence": f"Parsed homepage HTML for {domain_name}; 0 <script type=\"application/ld+json\"> blocks found.",
            "suggested_action": {
                "summary": f"Add Schema.org JSON-LD structured data. Active copy-pasteable snippet: {snippet_json}",
                "priority": "high"
            }
        })
    else:
        types_found: Set[str] = set()
        same_as_found = False

        def inspect_item(item: Any) -> None:
            nonlocal same_as_found
            if isinstance(item, dict):
                stype = item.get('@type')
                if stype:
                    if isinstance(stype, list):
                        types_found.update(str(s) for s in stype)
                    else:
                        types_found.add(str(stype))
                if 'sameAs' in item and item['sameAs']:
                    same_as_found = True
                for v in item.values():
                    inspect_item(v)
            elif isinstance(item, list):
                for sub in item:
                    inspect_item(sub)

        for block in parsed_json_ld:
            inspect_item(block)

        if not same_as_found:
            types_str = ", ".join(sorted(types_found)) if types_found else "Unknown Type"
            findings.append({
                "title": "Entity Ambiguity: Missing cross-web authority anchors (sameAs links)",
                "severity": "medium",
                "evidence": f"JSON-LD structured data present ({types_str}) but missing 'sameAs' array referencing authoritative entity URIs.",
                "suggested_action": {
                    "summary": "Entity Ambiguity: Missing cross-web authority anchors (sameAs links to Wikidata/Wikipedia/official socials) allowing AI models to conflate the brand with similarly named entities.",
                    "priority": "medium"
                }
            })

    return findings


def analyze_rag_quotability(heading_paragraphs: List[Tuple[str, str, str]]) -> List[Dict[str, Any]]:
    """Audit prose density under section headings for AEO / RAG quotability."""
    findings: List[Dict[str, Any]] = []
    long_prose_count = 0

    for _, _, p_text in heading_paragraphs:
        words = p_text.split()
        if len(words) > RAG_PROSE_WORD_THRESHOLD:
            first_sentence = p_text.split('.')[0] if '.' in p_text else p_text
            if len(first_sentence.split()) > RAG_LEAD_SENTENCE_MAX_WORDS:
                long_prose_count += 1

    if long_prose_count > 0:
        findings.append({
            "title": "Low Quotability Density: Key claims diluted in prose",
            "severity": "medium",
            "evidence": f"Detected {long_prose_count} prose section(s) under <h2>/<h3> headings exceeding {RAG_PROSE_WORD_THRESHOLD} words before delivering a concise declarative definition.",
            "suggested_action": {
                "summary": "Low Quotability Density: Key claims are diluted in promotional prose, reducing vector chunk retrieval relevance. Restructure into 40-60 word atomic answer blocks starting with direct declarative definitions for Answer Engine Optimization (AEO).",
                "priority": "medium"
            }
        })

    return findings


def analyze_html_semantic(html_content: str, domain_name: str) -> List[Dict[str, Any]]:
    """Run all semantic authority & RAG quotability checks on raw HTML."""
    findings: List[Dict[str, Any]] = []
    if not html_content:
        return findings

    parser = HeadingProseParser()
    try:
        parser.feed(html_content)
    except Exception:
        pass

    # 1. Parse JSON-LD blocks
    parsed_json_ld = []
    for raw in parser.json_ld_raw:
        try:
            parsed_json_ld.append(json.loads(raw))
        except Exception:
            pass

    findings.extend(analyze_json_ld(parsed_json_ld, domain_name))
    findings.extend(analyze_rag_quotability(parser.heading_paragraphs))

    return findings


def check_schema(target_url: str) -> List[Dict[str, Any]]:
    """Complete semantic authority and RAG audit entrypoint for a target domain."""
    if not target_url.startswith("http://") and not target_url.startswith("https://"):
        target_url = "https://" + target_url

    parsed_url = urllib.parse.urlparse(target_url)
    domain_name = parsed_url.netloc or parsed_url.path.split('/')[0]

    html_content = fetch_url(target_url)
    return analyze_html_semantic(html_content, domain_name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Brand AI-Readiness Semantic Authority & RAG Quotability Audit")
    parser.add_argument("--url", default="example.com", help="Target URL or domain to check")
    args = parser.parse_args()

    findings = check_schema(args.url)
    print(json.dumps(findings, indent=2))


if __name__ == "__main__":
    main()
