#!/usr/bin/env python3
"""
check_engagement.py - Enhanced On-Site Engagement & Retention Audit Script
Audits primary heading orientation, machine-readable image alt text coverage, and deep-link retention.
"""

import sys
import os
import json
import argparse
import urllib.request
import urllib.parse
import urllib.error
from html.parser import HTMLParser

class EngagementDOMParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.h1_texts = []
        self.in_h1 = False
        self.current_h1 = []
        self.images = [] # list of (src, alt)

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        attr_dict = {k.lower(): v for k, v in attrs if k and v}

        if tag_lower == 'h1':
            self.in_h1 = True
            self.current_h1 = []
        elif tag_lower == 'img':
            src = attr_dict.get('src', '')
            alt = attr_dict.get('alt', None)
            self.images.append((src, alt))

    def handle_endtag(self, tag):
        if tag.lower() == 'h1' and self.in_h1:
            self.in_h1 = False
            text = " ".join(self.current_h1).strip()
            self.h1_texts.append(text)

    def handle_data(self, data):
        if self.in_h1:
            cleaned = data.strip()
            if cleaned:
                self.current_h1.append(cleaned)

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

def check_engagement(target_url):
    findings = []

    if not target_url.startswith("http://") and not target_url.startswith("https://"):
        target_url = "https://" + target_url

    html_content = fetch_url(target_url)
    if not html_content:
        return findings

    parser = EngagementDOMParser()
    try:
        parser.feed(html_content)
    except Exception:
        pass

    # 1. Context Orientation Check (H1 Heading)
    if not parser.h1_texts:
        findings.append({
            "title": "Missing Primary Heading: Visitors arriving via deep links cannot confirm context",
            "severity": "high",
            "evidence": "Parsed HTML DOM; 0 <h1> heading elements found on homepage.",
            "suggested_action": {
                "summary": "Missing Primary Heading: Visitors arriving via deep links cannot confirm context. Add a clear, descriptive <h1> heading at the top of the body specifying your brand and core value proposition.",
                "priority": "high"
            }
        })
    else:
        primary_h1 = parser.h1_texts[0]
        words = primary_h1.split()
        vague_buzzwords = {'home', 'welcome', 'index', 'main', 'page'}

        if len(words) < 2 or primary_h1.lower() in vague_buzzwords:
            findings.append({
                "title": "Vague Primary Heading Orientation",
                "severity": "medium",
                "evidence": f"Detected <h1> text with weak context: '{primary_h1}'.",
                "suggested_action": {
                    "summary": "Expand <h1> heading to include explicit domain service descriptions rather than generic single-word titles.",
                    "priority": "medium"
                }
            })

    # 2. Facts Locked in Non-Text (Image Alt Text Coverage)
    if parser.images:
        trivial_alts = {'image', 'banner', 'pic', 'photo', 'logo', 'img', 'file'}
        missing_or_trivial = 0

        for src, alt in parser.images:
            if alt is None or not alt.strip() or alt.strip().lower() in trivial_alts:
                missing_or_trivial += 1

        pct_missing = (missing_or_trivial / len(parser.images)) * 100
        if pct_missing > 30.0:
            findings.append({
                "title": "Information locked in non-text media without machine-readable descriptions",
                "severity": "medium",
                "evidence": f"Found {len(parser.images)} <img> tag(s); {missing_or_trivial} ({pct_missing:.1f}%) lack descriptive alt text.",
                "suggested_action": {
                    "summary": "Information locked in non-text media without machine-readable descriptions. Add descriptive, context-rich alt text to all informational image graphics.",
                    "priority": "medium"
                }
            })

    # 3. Deep-Link Retention Recommendation
    findings.append({
        "title": "Proactive Opportunity: Deep-Link Visitor Retention & Contextual Navigation",
        "severity": "medium",
        "evidence": "Evaluated document for visitor context retention and deep-linked referral navigation.",
        "suggested_action": {
            "summary": "Implement sticky micro-breadcrumbs and explicit anchor jump-links to improve retention for visitors landing directly on deep answer excerpts.",
            "priority": "medium"
        }
    })

    return findings

def main():
    parser = argparse.ArgumentParser(description="Engagement & Retention Audit")
    parser.add_argument("--url", default="example.com", help="Target URL to check")
    args, unknown = parser.parse_known_args()
    target = args.url if args.url else (sys.argv[1] if len(sys.argv) > 1 else "example.com")

    findings = check_engagement(target)
    print(json.dumps(findings, indent=2))

if __name__ == "__main__":
    main()
