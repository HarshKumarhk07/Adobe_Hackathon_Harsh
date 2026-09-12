#!/usr/bin/env python3
"""
check_crawl.py - Enhanced Crawl & JS Render Audit Script
Detects AI bot exclusions in robots.txt with exact line numbers, missing sitemap/llms.txt,
and Client-Side Rendering (CSR) hydration deficits.
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

def load_ai_bots():
    bots_file = os.path.join(REF_DIR, "ai-bots.json")
    if os.path.exists(bots_file):
        try:
            with open(bots_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return ["GPTBot", "ChatGPT-User", "ClaudeBot", "Claude-Web", "PerplexityBot", "Bytespider", "Google-Extended", "cohere-ai"]

class CrawlHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.semantic_words = []
        self.script_char_count = 0
        self.in_script = False
        self.in_semantic = False
        self.semantic_tags = {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'article'}

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        if tag_lower == 'script':
            self.in_script = True
        if tag_lower in self.semantic_tags:
            self.in_semantic = True

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower == 'script':
            self.in_script = False
        if tag_lower in self.semantic_tags:
            self.in_semantic = False

    def handle_data(self, data):
        if self.in_script:
            self.script_char_count += len(data)
        elif self.in_semantic:
            cleaned = data.strip()
            if cleaned:
                self.semantic_words.extend(cleaned.split())

def fetch_url(url, timeout=5):
    """Safely fetch URL content and headers."""
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

def check_crawl(target_url):
    findings = []
    ai_bots = load_ai_bots()

    if not target_url.startswith("http://") and not target_url.startswith("https://"):
        target_url = "https://" + target_url

    parsed_url = urllib.parse.urlparse(target_url)
    domain = parsed_url.netloc or parsed_url.path
    base_url = f"{parsed_url.scheme or 'https'}://{domain.split('/')[0]}"

    # 1. robots.txt Analysis with Line Number Tracking
    robots_url = f"{base_url}/robots.txt"
    r_status, r_headers, r_txt = fetch_url(robots_url)

    if r_status == 200 and r_txt:
        disallowed_blocks = []
        current_uas = []
        
        for line_num, line in enumerate(r_txt.splitlines(), start=1):
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
    sitemap_url = f"{base_url}/sitemap.xml"
    s_status, _, s_txt = fetch_url(sitemap_url)
    if s_status != 200 or not s_txt:
        findings.append({
            "title": "XML Sitemap Missing or Inaccessible",
            "severity": "medium",
            "evidence": f"GET {sitemap_url} returned HTTP status {s_status}",
            "suggested_action": {
                "summary": "Generate an XML sitemap and register it in robots.txt so AI crawlers can discover primary domain paths.",
                "priority": "medium"
            }
        })

    llms_url = f"{base_url}/llms.txt"
    l_status, _, l_txt = fetch_url(llms_url)
    if l_status != 200 or not l_txt:
        findings.append({
            "title": "Proactive Opportunity: Missing llms.txt Markdown Context Manifest",
            "severity": "low",
            "evidence": f"GET {llms_url} returned HTTP status {l_status}",
            "suggested_action": {
                "summary": "Publish an /llms.txt file providing clean markdown context summaries and key documentation links. Providing markdown context drastically improves AI retrieval accuracy.",
                "priority": "low"
            }
        })

    # 3. Render Gap & Hydration Deficit Check
    h_status, _, html_content = fetch_url(target_url)
    if html_content:
        parser = CrawlHTMLParser()
        try:
            parser.feed(html_content)
        except Exception:
            pass

        semantic_word_count = len(parser.semantic_words)
        script_size = parser.script_char_count

        has_spa_mount = any(marker in html_content for marker in [
            'id="root"', 'id="__next"', 'id="app"', 'id="__nuxt"', '__NEXT_DATA__', 'window.__INITIAL_STATE__'
        ])

        if semantic_word_count < 40 and (script_size > 10000 or has_spa_mount):
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

def main():
    parser = argparse.ArgumentParser(description="Enhanced Crawl & JS Render Audit")
    parser.add_argument("--url", default="example.com", help="Target URL to check")
    args, unknown = parser.parse_known_args()
    target = args.url if args.url else (sys.argv[1] if len(sys.argv) > 1 else "example.com")

    findings = check_crawl(target)
    print(json.dumps(findings, indent=2))

if __name__ == "__main__":
    main()
