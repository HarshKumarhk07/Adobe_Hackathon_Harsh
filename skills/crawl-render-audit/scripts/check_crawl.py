#!/usr/bin/env python3
"""
check_crawl.py - Crawl & JS Render Audit Sub-Skill
Detects AI bot exclusions in robots.txt with exact line numbers, missing sitemap/llms.txt,
and Client-Side Rendering (CSR) hydration deficits.
"""

import sys
import os
import json
import argparse
import urllib.request
import urllib.parse
import urllib.error
from html.parser import HTMLParser
from typing import List, Dict, Any, Tuple, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REF_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "references"))

# Authoritative named constants
MIN_SEMANTIC_WORD_COUNT = 40
HEAVY_SCRIPT_CHAR_COUNT = 10000
DEFAULT_FETCH_TIMEOUT = 5
DEFAULT_AI_BOTS = [
    "GPTBot", "ChatGPT-User", "ClaudeBot", "Claude-Web",
    "PerplexityBot", "Bytespider", "Google-Extended", "cohere-ai"
]
SPA_FRAMEWORK_MARKERS = (
    'id="root"', 'id="__next"', 'id="app"', 'id="__nuxt"',
    '__NEXT_DATA__', 'window.__INITIAL_STATE__'
)


def load_ai_bots() -> List[str]:
    """Load target AI bots list from references or fallback to defaults."""
    bots_file = os.path.join(REF_DIR, "ai-bots.json")
    if os.path.exists(bots_file):
        try:
            with open(bots_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return list(DEFAULT_AI_BOTS)


class CrawlHTMLParser(HTMLParser):
    """HTML Parser extracting semantic text words and script payload size."""

    def __init__(self) -> None:
        super().__init__()
        self.semantic_words: List[str] = []
        self.script_char_count = 0
        self.in_script = False
        self.in_semantic = False
        self.semantic_tags = {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'article'}

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        tag_lower = tag.lower()
        if tag_lower == 'script':
            self.in_script = True
        if tag_lower in self.semantic_tags:
            self.in_semantic = True

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower == 'script':
            self.in_script = False
        if tag_lower in self.semantic_tags:
            self.in_semantic = False

    def handle_data(self, data: str) -> None:
        if self.in_script:
            self.script_char_count += len(data)
        elif self.in_semantic:
            cleaned = data.strip()
            if cleaned:
                self.semantic_words.extend(cleaned.split())


def fetch_url(url: str, timeout: int = DEFAULT_FETCH_TIMEOUT) -> Tuple[int, Dict[str, str], str]:
    """Safely fetch URL content, returning (status_code, headers_dict, body_text)."""
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, dict(response.headers), response.read().decode('utf-8', errors='ignore')
    except urllib.error.HTTPError as e:
        content = ""
        try:
            content = e.read().decode('utf-8', errors='ignore')
        except Exception:
            pass
        return e.code, dict(e.headers), content
    except Exception:
        return 0, {}, ""


def analyze_robots_txt(robots_text: str, robots_url: str, ai_bots: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Parse robots.txt content and detect AI bot blocking rules with line numbers."""
    findings: List[Dict[str, Any]] = []
    if ai_bots is None:
        ai_bots = load_ai_bots()

    if not robots_text:
        return findings

    disallowed_blocks = []
    current_uas: List[Tuple[int, str]] = []

    for line_num, line in enumerate(robots_text.splitlines(), start=1):
        line_str = line.strip()
        if not line_str or line_str.startswith("#"):
            continue

        if line_str.lower().startswith("user-agent:"):
            ua = line_str.split(":", 1)[1].strip()
            current_uas.append((line_num, ua))
        elif line_str.lower().startswith("disallow:"):
            path = line_str.split(":", 1)[1].strip()
            if path in ["/", "/*"]:
                for ua_line, ua in current_uas:
                    if ua == "*" or any(b.lower() in ua.lower() for b in ai_bots):
                        disallowed_blocks.append(f"Line {line_num}: Disallow: {path} (under User-agent: {ua} at Line {ua_line})")

    if disallowed_blocks:
        findings.append({
            "title": "AI Assistant Crawler Blocked in robots.txt",
            "severity": "critical",
            "evidence": f"Explicit disallow rules detected in {robots_url}:\n" + "\n".join(disallowed_blocks[:4]),
            "suggested_action": {
                "summary": f"Update robots.txt to remove blanket Disallow: / rules for AI retrieval crawlers ({', '.join(ai_bots[:4])}) to enable AI discoverability.",
                "priority": "critical"
            }
        })

    return findings


def analyze_sitemap_and_llms(
    base_url: str,
    sitemap_status: int,
    sitemap_has_content: bool,
    llms_status: int,
    llms_has_content: bool
) -> List[Dict[str, Any]]:
    """Analyze presence and accessibility of XML sitemap and /llms.txt manifest."""
    findings: List[Dict[str, Any]] = []

    sitemap_url = f"{base_url}/sitemap.xml"
    if sitemap_status != 200 or not sitemap_has_content:
        findings.append({
            "title": "XML Sitemap Missing or Inaccessible",
            "severity": "medium",
            "evidence": f"GET {sitemap_url} returned HTTP status {sitemap_status}",
            "suggested_action": {
                "summary": "Generate an XML sitemap and register it in robots.txt so AI crawlers can discover primary domain paths.",
                "priority": "medium"
            }
        })

    llms_url = f"{base_url}/llms.txt"
    if llms_status != 200 or not llms_has_content:
        findings.append({
            "title": "Proactive Opportunity: Missing llms.txt Markdown Context Manifest",
            "severity": "low",
            "evidence": f"GET {llms_url} returned HTTP status {llms_status}",
            "suggested_action": {
                "summary": "Publish an /llms.txt file providing clean markdown context summaries and key documentation links. Providing markdown context drastically improves AI retrieval accuracy.",
                "priority": "low"
            }
        })

    return findings


def analyze_html_render_gap(html_content: str) -> List[Dict[str, Any]]:
    """Detect CSR hydration deficits where static text is sparse relative to script size or SPA markers."""
    findings: List[Dict[str, Any]] = []
    if not html_content:
        return findings

    parser = CrawlHTMLParser()
    try:
        parser.feed(html_content)
    except Exception:
        pass

    semantic_word_count = len(parser.semantic_words)
    script_size = parser.script_char_count

    has_spa_mount = any(marker in html_content for marker in SPA_FRAMEWORK_MARKERS)

    if semantic_word_count < MIN_SEMANTIC_WORD_COUNT and (script_size > HEAVY_SCRIPT_CHAR_COUNT or has_spa_mount):
        findings.append({
            "title": "Client-Side Render Gap: Core Facts Blotted by JS Hydration",
            "severity": "high",
            "evidence": f"Raw static HTML contains only {semantic_word_count} text words inside <p>/<h>/<article> tags; detected {script_size:,} script characters and client-side framework hydration markers ('__NEXT_DATA__' / 'id=\"root\"').",
            "suggested_action": {
                "summary": "Implement Server-Side Rendering (SSR) or Static Site Generation (SSG) so non-JS executing AI crawlers can read body text directly from static HTML.",
                "priority": "high"
            }
        })

    return findings


def check_crawl(target_url: str) -> List[Dict[str, Any]]:
    """Complete crawl and JS render audit entrypoint for a target domain."""
    findings: List[Dict[str, Any]] = []
    ai_bots = load_ai_bots()

    if not target_url.startswith("http://") and not target_url.startswith("https://"):
        target_url = "https://" + target_url

    parsed_url = urllib.parse.urlparse(target_url)
    domain = parsed_url.netloc or parsed_url.path
    base_url = f"{parsed_url.scheme or 'https'}://{domain.split('/')[0]}"

    # 1. robots.txt Analysis
    robots_url = f"{base_url}/robots.txt"
    r_status, _, r_txt = fetch_url(robots_url)

    if r_status == 200 and r_txt:
        findings.extend(analyze_robots_txt(r_txt, robots_url, ai_bots))
    else:
        findings.append({
            "title": "Unreachable or Missing robots.txt Directive File",
            "severity": "medium",
            "evidence": f"GET {robots_url} returned HTTP status {r_status}",
            "suggested_action": {
                "summary": "Publish a valid robots.txt file at domain root establishing explicit permissions for AI assistant crawlers.",
                "priority": "medium"
            }
        })

    # 2. Sitemap & llms.txt Verification
    s_status, _, s_txt = fetch_url(f"{base_url}/sitemap.xml")
    l_status, _, l_txt = fetch_url(f"{base_url}/llms.txt")
    findings.extend(analyze_sitemap_and_llms(
        base_url=base_url,
        sitemap_status=s_status,
        sitemap_has_content=bool(s_txt),
        llms_status=l_status,
        llms_has_content=bool(l_txt)
    ))

    # 3. Render Gap & Hydration Deficit Check
    _, _, html_content = fetch_url(target_url)
    findings.extend(analyze_html_render_gap(html_content))

    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description="Brand AI-Readiness Crawl & JS Render Audit")
    parser.add_argument("--url", default="example.com", help="Target URL or domain to check")
    args = parser.parse_args()

    findings = check_crawl(args.url)
    print(json.dumps(findings, indent=2))


if __name__ == "__main__":
    main()
