#!/usr/bin/env python3
"""
check_schema.py - Enhanced Semantic Authority & RAG Quotability Audit Script
Audits Schema.org JSON-LD markup, entity sameAs disambiguation, and RAG quotability density.
"""

import sys
import os
import json
import re
import argparse
import urllib.request
import urllib.parse
import urllib.error
from html.parser import HTMLParser

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REF_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "references"))

def load_schema_templates(domain_name):
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
    def __init__(self):
        super().__init__()
        self.json_ld_raw = []
        self.in_json_ld = False
        self.current_json_ld = []
        self.heading_paragraphs = []
        self.current_heading = None
        self.current_heading_text = []
        self.in_heading = False
        self.in_paragraph = False
        self.current_paragraph_text = []
        self.last_heading = None

    def handle_starttag(self, tag, attrs):
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

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower == 'script' and self.in_json_ld:
            self.in_json_ld = False
            text = "".join(self.current_json_ld).strip()
            if text:
                self.json_ld_raw.append(text)

        elif tag_lower in ['h2', 'h3'] and self.in_heading:
            self.in_heading = False
            self.last_heading = (self.current_heading, " ".join(self.current_heading_text).strip())

        elif tag_lower == 'p' and self.in_paragraph:
            self.in_paragraph = False
            p_text = " ".join(self.current_paragraph_text).strip()
            if self.last_heading and p_text:
                self.heading_paragraphs.append((self.last_heading[0], self.last_heading[1], p_text))

    def handle_data(self, data):
        if self.in_json_ld:
            self.current_json_ld.append(data)
        if self.in_heading:
            self.current_heading_text.append(data.strip())
        if self.in_paragraph:
            self.current_paragraph_text.append(data.strip())

def fetch_url(url, timeout=5):
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

def check_schema(target_url):
    findings = []

    if not target_url.startswith("http://") and not target_url.startswith("https://"):
        target_url = "https://" + target_url

    parsed_url = urllib.parse.urlparse(target_url)
    domain_name = parsed_url.netloc or parsed_url.path.split('/')[0]

    html_content = fetch_url(target_url)
    if not html_content:
        return findings

    parser = HeadingProseParser()
    try:
        parser.feed(html_content)
    except Exception:
        pass

    # 1. JSON-LD Completeness & Entity Ambiguity Check
    parsed_json_ld = []
    for raw in parser.json_ld_raw:
        try:
            parsed_json_ld.append(json.loads(raw))
        except Exception:
            pass

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
        types_found = set()
        same_as_found = False

        def inspect_item(item):
            nonlocal same_as_found
            if isinstance(item, dict):
                stype = item.get('@type')
                if stype:
                    if isinstance(stype, list):
                        types_found.update(stype)
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
            findings.append({
                "title": "Entity Ambiguity: Missing cross-web authority anchors (sameAs links)",
                "severity": "medium",
                "evidence": f"JSON-LD structured data present ({', '.join(types_found)}) but missing 'sameAs' array referencing authoritative entity URIs.",
                "suggested_action": {
                    "summary": "Entity Ambiguity: Missing cross-web authority anchors (sameAs links to Wikidata/Wikipedia/official socials) allowing AI models to conflate the brand with similarly named entities.",
                    "priority": "medium"
                }
            })

    # 2. RAG Quotability Density Check
    long_prose_count = 0
    for tag, heading_text, p_text in parser.heading_paragraphs:
        words = p_text.split()
        if len(words) > 150:
            first_sentence = p_text.split('.')[0] if '.' in p_text else p_text
            if len(first_sentence.split()) > 25:
                long_prose_count += 1

    if long_prose_count > 0:
        findings.append({
            "title": "Low Quotability Density: Key claims diluted in prose",
            "severity": "medium",
            "evidence": f"Detected {long_prose_count} prose section(s) under <h2>/<h3> headings exceeding 150 words before delivering a concise declarative definition.",
            "suggested_action": {
                "summary": "Low Quotability Density: Key claims are diluted in promotional prose, reducing vector chunk retrieval relevance. Restructure into 40-60 word atomic answer blocks starting with direct declarative definitions for Answer Engine Optimization (AEO).",
                "priority": "medium"
            }
        })

    return findings

def main():
    parser = argparse.ArgumentParser(description="Semantic Authority & RAG Quotability Audit")
    parser.add_argument("--url", default="example.com", help="Target URL to check")
    args, unknown = parser.parse_known_args()
    target = args.url if args.url else (sys.argv[1] if len(sys.argv) > 1 else "example.com")

    findings = check_schema(target)
    print(json.dumps(findings, indent=2))

if __name__ == "__main__":
    main()
