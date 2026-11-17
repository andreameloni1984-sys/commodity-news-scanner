"""Discover official dated articles when the White House RSS endpoint is absent."""
from html.parser import HTMLParser
from urllib.parse import urlparse
import re
from .feed_parser import clean_public_text


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        url = attrs.get("href", "")
        parsed = urlparse(url)
        if tag == "a" and parsed.scheme == "https" and parsed.hostname == "www.whitehouse.gov" and re.fullmatch(r"/(?:briefings-statements|presidential-actions|fact-sheets|releases|remarks)/\d{4}/\d{2}/[^/]+/", parsed.path):
            if url not in self.urls:
                self.urls.append(url)


class Article(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.published = ""
        self.parts = []
        self.depth = 0
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            if attrs.get("property") == "og:title":
                self.title = attrs.get("content", "")
            if attrs.get("property") == "article:published_time":
                self.published = attrs.get("content", "")
        if tag == "div":
            if self.depth:
                self.depth += 1
            elif "wp-block-post-content" in attrs.get("class", "").split():
                self.depth = 1
        if tag in {"script", "style"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag == "div" and self.depth:
            self.depth -= 1
        if tag in {"script", "style"} and self.skip:
            self.skip -= 1
        if self.depth and tag in {"p", "li"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.depth and not self.skip:
            self.parts.append(data)


def items(raw, index_url, fetch):
    parser = Links()
    parser.feed(raw.decode("utf-8", errors="replace"))
    if not parser.urls:
        raise ValueError("No individual article links in White House index")
    result = []
    failures = 0
    for url in parser.urls[:8]:
        try:
            article = Article()
            article.feed(fetch(url).decode("utf-8", errors="replace"))
        except Exception:
            failures += 1
            continue
        body = " ".join(article.parts)
        if not article.published or not article.title or not body.strip():
            failures += 1
            continue
        result.append({"id": url, "url": url, "feed_url": index_url,
                       "title": clean_public_text(article.title),
                       "text": body, "published": article.published})
    if not result or failures:
        # A changed page layout is visible as source failure, not 'no news'.
        raise ValueError("White House article fetch/metadata incomplete")
    return result
