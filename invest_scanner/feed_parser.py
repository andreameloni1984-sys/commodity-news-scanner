"""Minimal, standard-library RSS/Atom parsing for public SPUTNIK sources."""
from __future__ import annotations
import hashlib
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import urljoin

class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
    def handle_data(self, data):
        value = " ".join(data.split()).strip()
        if value:
            self.parts.append(value)

def clean_public_text(value):
    parser = _Text()
    parser.feed(str(value or ""))
    joined = " ".join(parser.parts).strip()
    # HTMLParser splits punctuation into separate data nodes; rejoin it.
    return re.sub(r"\s+([.,!?;:])", r"\1", joined)

def _name(tag):
    return str(tag).rsplit("}", 1)[-1].split(":")[-1].lower()

def _direct(node, names):
    for child in list(node):
        if _name(child.tag) in names:
            return child
    return None

def _text(node, names):
    child = _direct(node, names)
    return "".join(child.itertext()).strip() if child is not None else ""

def _link(node):
    child = _direct(node, {"link"})
    if child is None:
        return ""
    return str(child.attrib.get("href") or "").strip() or "".join(child.itertext()).strip()

def _descendant(node, names):
    for child in node.iter():
        if child is node or _name(child.tag) not in names:
            continue
        value = "".join(child.itertext()).strip()
        if value:
            return value
    return ""

def parse_public_feed(raw, base_url):
    """Return individual RSS 2.0 or Atom entries with source metadata."""
    try:
        root = ET.fromstring(raw)
    except (ET.ParseError, TypeError, ValueError) as exc:
        raise ValueError("Fonte pubblica priva di RSS/Atom XML valido") from exc
    if _name(root.tag) not in {"rss", "rdf", "feed"}:
        raise ValueError("Fonte pubblica priva di RSS/Atom XML valido")
    entries = [n for n in root.iter() if _name(n.tag) in {"item", "entry"}]
    result = []
    for index, entry in enumerate(entries):
        title = clean_public_text(_text(entry, {"title"}))
        body = clean_public_text(_text(entry, {"encoded", "description", "summary", "content"}))
        if not title and not body:
            continue
        link = _link(entry)
        link = urljoin(base_url, link) if link else base_url
        published = _text(entry, {"pubdate", "published", "updated", "date"})
        identity = _text(entry, {"guid", "id"}) or link or hashlib.sha256(
            (title + "|" + published + "|" + body).encode("utf-8")
        ).hexdigest()
        original = _descendant(entry, {"originalurl", "original_url", "truthoriginalurl"})
        if original:
            original = urljoin(base_url, original)
        result.append({
            "id": identity[:500], "title": title[:300], "text": body[:6000],
            "published": published[:100], "url": link[:1000],
            "primary_url": original[:1000], "feed_url": base_url[:1000],
            "item_index": str(index),
        })
    return result
