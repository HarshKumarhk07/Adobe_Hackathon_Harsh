#!/usr/bin/env python3
"""
check_engagement.py - On-Site Engagement & Retention Audit Sub-Skill
Audits primary heading orientation, machine-readable image alt text coverage,
and deep-linked citation retention navigation.
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

# Authoritative named constants
IMAGE_ALT_MISSING_THRESHOLD = 0.30
TRIVIAL_ALT_VALUES: Set[str] = {'image', 'banner', 'pic', 'photo', 'logo', 'img', 'file'}
VAGUE_H1_KEYWORDS: Set[str] = {'home', 'welcome', 'index', 'main', 'page'}
DEFAULT_FETCH_TIMEOUT = 5
MIN_SECTIONS_FOR_RETENTION_CHECK = 2


class EngagementDOMParser(HTMLParser):
    """HTML Parser extracting headings, images, breadcrumb structures, and anchor jump links."""

    def __init__(self) -> None:
        super().__init__()
        self.h1_texts: List[str] = []
        self.in_h1 = False
        self.current_h1: List[str] = []
        self.images: List[Tuple[str, Optional[str]]] = []  # (src, alt)
        self.section_headings_count = 0
        self.has_breadcrumbs = False
        self.anchor_jump_links_count = 0

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        tag_lower = tag.lower()
        attr_dict = {k.lower(): v for k, v in attrs if k and v is not None}

        if tag_lower == 'h1':
            self.in_h1 = True
            self.current_h1 = []
        elif tag_lower in ('h2', 'h3', 'h4'):
            self.section_headings_count += 1
        elif tag_lower == 'img':
            src = attr_dict.get('src', '')
            alt = attr_dict.get('alt', None)
            self.images.append((src, alt))
        elif tag_lower == 'a':
            href = attr_dict.get('href', '').strip()
            if href.startswith('#') and len(href) > 1:
                self.anchor_jump_links_count += 1

        # Check for breadcrumb navigation cues
        aria_label = attr_dict.get('aria-label', '').lower()
        class_name = attr_dict.get('class', '').lower()
        elem_id = attr_dict.get('id', '').lower()
        if 'breadcrumb' in aria_label or 'breadcrumb' in class_name or 'breadcrumb' in elem_id:
            self.has_breadcrumbs = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == 'h1' and self.in_h1:
            self.in_h1 = False
            text = " ".join(self.current_h1).strip()
            if text:
                self.h1_texts.append(text)

    def handle_data(self, data: str) -> None:
        if self.in_h1:
            cleaned = data.strip()
            if cleaned:
                self.current_h1.append(cleaned)


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


def analyze_headings(h1_texts: List[str]) -> List[Dict[str, Any]]:
    """Audit primary H1 heading presence and clarity."""
    findings: List[Dict[str, Any]] = []

    if not h1_texts:
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
        primary_h1 = h1_texts[0]
        words = primary_h1.split()

        if len(words) < 2 or primary_h1.lower() in VAGUE_H1_KEYWORDS:
            findings.append({
                "title": "Vague Primary Heading Orientation",
                "severity": "medium",
                "evidence": f"Detected <h1> text with weak context: '{primary_h1}'.",
                "suggested_action": {
                    "summary": "Expand <h1> heading to include explicit domain service descriptions rather than generic single-word titles.",
                    "priority": "medium"
                }
            })

    return findings


def analyze_image_alts(images: List[Tuple[str, Optional[str]]]) -> List[Dict[str, Any]]:
    """Audit image alt text coverage against the missing/trivial threshold."""
    findings: List[Dict[str, Any]] = []
    if not images:
        return findings

    missing_or_trivial = 0
    for _, alt in images:
        if alt is None or not alt.strip() or alt.strip().lower() in TRIVIAL_ALT_VALUES:
            missing_or_trivial += 1

    pct_missing = (missing_or_trivial / len(images)) * 100
    if pct_missing > (IMAGE_ALT_MISSING_THRESHOLD * 100):
        findings.append({
            "title": "Information locked in non-text media without machine-readable descriptions",
            "severity": "medium",
            "evidence": f"Found {len(images)} <img> tag(s); {missing_or_trivial} ({pct_missing:.1f}%) lack descriptive alt text.",
            "suggested_action": {
                "summary": "Information locked in non-text media without machine-readable descriptions. Add descriptive, context-rich alt text to all informational image graphics.",
                "priority": "medium"
            }
        })

    return findings


def analyze_deep_link_retention(
    section_headings_count: int,
    anchor_jump_links_count: int,
    has_breadcrumbs: bool
) -> List[Dict[str, Any]]:
    """Audit contextual navigation aids for visitors landing on deep sections from AI citations."""
    findings: List[Dict[str, Any]] = []

    if section_headings_count >= MIN_SECTIONS_FOR_RETENTION_CHECK and anchor_jump_links_count == 0 and not has_breadcrumbs:
        findings.append({
            "title": "Proactive Opportunity: Deep-Link Visitor Retention & Contextual Navigation",
            "severity": "medium",
            "evidence": f"Page contains {section_headings_count} section headings but lacks in-page anchor jump-links (<a href=\"#...\">) and breadcrumb navigation to orient visitors arriving via deep-linked AI citations.",
            "suggested_action": {
                "summary": "Implement sticky micro-breadcrumbs and explicit anchor jump-links to improve retention for visitors landing directly on deep answer excerpts.",
                "priority": "medium"
            }
        })

    return findings


def analyze_engagement_html(html_content: str) -> List[Dict[str, Any]]:
    """Run all on-site engagement checks on raw HTML."""
    findings: List[Dict[str, Any]] = []
    if not html_content:
        return findings

    parser = EngagementDOMParser()
    try:
        parser.feed(html_content)
    except Exception:
        pass

    findings.extend(analyze_headings(parser.h1_texts))
    findings.extend(analyze_image_alts(parser.images))
    findings.extend(analyze_deep_link_retention(
        section_headings_count=parser.section_headings_count,
        anchor_jump_links_count=parser.anchor_jump_links_count,
        has_breadcrumbs=parser.has_breadcrumbs
    ))

    return findings


def check_engagement(target_url: str) -> List[Dict[str, Any]]:
    """Complete engagement and retention audit entrypoint for a target domain."""
    if not target_url.startswith("http://") and not target_url.startswith("https://"):
        target_url = "https://" + target_url

    html_content = fetch_url(target_url)
    return analyze_engagement_html(html_content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Brand AI-Readiness On-Site Engagement & Retention Audit")
    parser.add_argument("--url", default="example.com", help="Target URL or domain to check")
    args = parser.parse_args()

    findings = check_engagement(args.url)
    print(json.dumps(findings, indent=2))


if __name__ == "__main__":
    main()
