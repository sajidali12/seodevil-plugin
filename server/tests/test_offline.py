"""Offline tests (no network). Run: python3 -m unittest discover -s server/tests"""
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.dirname(HERE)
sys.path.insert(0, SERVER)

from seodevil_mcp import audit, schema, textstats  # noqa: E402
from seodevil_mcp.dom import Document  # noqa: E402
from seodevil_mcp.onpage import valid_hreflang  # noqa: E402
from seodevil_mcp.site import Robots, parse_sitemap  # noqa: E402

FX = os.path.join(HERE, "fixtures")


def ids(result):
    return {i["id"] for i in result["issues"]}


class TestOnPage(unittest.TestCase):
    def test_bad_page_flags_problems(self):
        r = audit.audit_html(path=os.path.join(FX, "bad.html"), base_url="https://example.com/")
        found = ids(r)
        for expected in ("title_generic", "description_missing", "h1_empty", "heading_skips", "img_alt_missing",
                         "img_alt_poor", "links_javascript", "links_generic_anchor", "links_no_anchor_text",
                         "placeholder_text", "schema_invalid_json", "schema_errors", "viewport_missing", "lang_missing",
                         "canonical_missing", "og_missing", "meta_keywords", "render_blocking_scripts"):
            self.assertIn(expected, found)
        self.assertLess(r["score"], 50)

    def test_good_page_scores_high(self):
        r = audit.audit_html(path=os.path.join(FX, "good.html"), base_url="https://example.com/blog/trail-running-shoes",
                             keyword="trail running shoes")
        self.assertGreaterEqual(r["score"], 90, r["issues"])
        kw = r["data"]["keyword"]
        self.assertTrue(kw["in_title"] and kw["in_h1"] and kw["in_url"] and kw["in_first_100_words"])
        self.assertEqual(r["data"]["schema"]["jsonld_types"], ["BlogPosting"])

    def test_directory_audit(self):
        r = audit.audit_directory(os.path.join(FX, "site"), "https://example.com")
        self.assertEqual(r["html_files"], 2)
        site_ids = {i["id"] for i in r["site_issues"]}
        self.assertIn("duplicate_titles", site_ids)
        self.assertIn("broken_internal_links", site_ids)


class TestSchema(unittest.TestCase):
    def test_product_needs_offers(self):
        out = schema.validate_any('{"@context":"https://schema.org","@type":"Product","name":"X"}')
        self.assertTrue(any("offers" in e for e in out["entities"][0]["errors"]))

    def test_graph_and_nested_offer(self):
        doc = {"@context": "https://schema.org", "@graph": [
            {"@type": "Organization", "name": "A", "url": "https://a.com", "logo": "https://a.com/l.png"},
            {"@type": "Product", "name": "B", "offers": {"@type": "Offer", "price": "$10", "priceCurrency": "USD"}}]}
        out = schema.validate_any(json.dumps(doc))
        self.assertEqual(len(out["entities"]), 2)
        self.assertTrue(any("price must be a number" in e for e in out["entities"][1]["errors"]))

    def test_local_business_subtype(self):
        out = schema.validate_any('{"@context":"https://schema.org","@type":"Dentist","name":"Smile"}')
        self.assertTrue(any("address" in e for e in out["entities"][0]["errors"]))


class TestRobots(unittest.TestCase):
    TXT = """
User-agent: *
Disallow: /admin/
Allow: /admin/public$
Disallow: /*.pdf$

User-agent: GPTBot
User-agent: CCBot
Disallow: /

Sitemap: https://example.com/sitemap.xml
"""

    def test_rules(self):
        r = Robots(self.TXT)
        self.assertFalse(r.check("Googlebot", "/admin/x")["allowed"])
        self.assertTrue(r.check("Googlebot", "/admin/public")["allowed"])
        self.assertFalse(r.check("Googlebot", "/files/a.pdf")["allowed"])
        self.assertTrue(r.check("Googlebot", "/files/a.pdf?x=1")["allowed"])
        self.assertFalse(r.check("GPTBot", "/")["allowed"])
        self.assertFalse(r.check("CCBot", "/blog")["allowed"])
        self.assertTrue(r.check("ClaudeBot", "/blog")["allowed"])
        self.assertEqual(r.sitemaps, ["https://example.com/sitemap.xml"])
        self.assertTrue(r.blocks_everything("GPTBot"))


class TestMisc(unittest.TestCase):
    def test_sitemap_parse(self):
        xml = b'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://a.com/</loc><lastmod>2026-01-01</lastmod></url></urlset>'
        p = parse_sitemap(xml)
        self.assertEqual(p["kind"], "urlset")
        self.assertEqual(p["entries"][0]["loc"], "https://a.com/")

    def test_hreflang_codes(self):
        for ok in ("en", "en-GB", "pt-br", "x-default", "zh-Hant-TW", "uk"):
            self.assertTrue(valid_hreflang(ok), ok)
        for bad in ("en-UK", "jp", "english", "en_US"):
            self.assertFalse(valid_hreflang(bad), bad)

    def test_serp_truncation(self):
        p = textstats.serp_preview("A" * 90, "word " * 60)
        self.assertTrue(p["title"]["truncated"])
        self.assertTrue(p["title"]["displayed"].endswith("..."))

    def test_dom_text_skips_scripts(self):
        d = Document("<body><p>Hello</p><script>var x=1</script><style>p{}</style><li>a<li>b</body>")
        self.assertEqual(d.body.text(), "Hello a b")
        self.assertEqual(len(d.find_all("li")), 2)


class TestMcpProtocol(unittest.TestCase):
    def test_handshake_list_and_call(self):
        msgs = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "serp_preview", "arguments": {"title": "Hello world"}}},
            {"jsonrpc": "2.0", "id": 4, "method": "nope"},
        ]
        proc = subprocess.run([sys.executable, os.path.join(SERVER, "run.py")], input="\n".join(json.dumps(m) for m in msgs) + "\n",
                              capture_output=True, text=True, timeout=60)
        replies = {r["id"]: r for r in map(json.loads, proc.stdout.strip().splitlines())}
        self.assertEqual(replies[1]["result"]["protocolVersion"], "2025-06-18")
        names = {t["name"] for t in replies[2]["result"]["tools"]}
        self.assertIn("audit_page", names)
        self.assertIn("crawl_site", names)
        body = json.loads(replies[3]["result"]["content"][0]["text"])
        self.assertEqual(body["title"]["text"], "Hello world")
        self.assertEqual(replies[4]["error"]["code"], -32601)


if __name__ == "__main__":
    unittest.main()
