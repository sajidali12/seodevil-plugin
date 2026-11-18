"""A forgiving HTML tree builder on top of the standard library's HTMLParser."""
from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Iterator, List, Optional, Union

VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
    "param", "source", "track", "wbr", "keygen", "command",
}
# Elements whose text is never shown to a reader.
HIDDEN_TEXT = {"script", "style", "template", "noscript", "svg", "head", "title", "iframe", "object"}
# Opening one of these closes an open element of the same kind (common HTML shortcuts).
AUTO_CLOSE = {"p", "li", "option", "tr", "td", "th", "dt", "dd"}
BLOCK = {
    "p", "div", "section", "article", "main", "header", "footer", "nav", "aside", "li", "ul", "ol",
    "h1", "h2", "h3", "h4", "h5", "h6", "table", "tr", "td", "th", "br", "blockquote", "pre",
    "figure", "figcaption", "dd", "dt", "dl", "form", "label", "summary", "details",
}


class Node:
    __slots__ = ("tag", "attrs", "children", "parent", "line")

    def __init__(self, tag: str, attrs: Optional[dict] = None, parent: Optional["Node"] = None, line: int = 0):
        self.tag = tag
        self.attrs = attrs or {}
        self.children: List[Union["Node", str]] = []
        self.parent = parent
        self.line = line

    def get(self, name: str, default: str = "") -> str:
        v = self.attrs.get(name)
        return default if v is None else v

    def has(self, name: str) -> bool:
        return name in self.attrs

    def iter(self) -> Iterator["Node"]:
        stack = [self]
        while stack:
            node = stack.pop()
            yield node
            stack.extend(c for c in reversed(node.children) if isinstance(c, Node))

    def find_all(self, tags=None, limit: int = 0, **attrs) -> List["Node"]:
        if isinstance(tags, str):
            tags = {tags}
        out = []
        for n in self.iter():
            if n is self:
                continue
            if tags and n.tag not in tags:
                continue
            if attrs and not all(_attr_match(n, k.rstrip("_"), v) for k, v in attrs.items()):
                continue
            out.append(n)
            if limit and len(out) >= limit:
                break
        return out

    def find(self, tags=None, **attrs) -> Optional["Node"]:
        r = self.find_all(tags, limit=1, **attrs)
        return r[0] if r else None

    def ancestors(self) -> Iterator["Node"]:
        p = self.parent
        while p is not None:
            yield p
            p = p.parent

    def text(self, skip=HIDDEN_TEXT) -> str:
        parts: List[str] = []
        _collect_text(self, parts, skip)
        return re.sub(r"\s+", " ", "".join(parts)).strip()

    def own_html_len(self) -> int:
        return sum(len(c) if isinstance(c, str) else c.own_html_len() for c in self.children)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{self.tag} {self.attrs}>"


def _attr_match(n: Node, key: str, want) -> bool:
    key = key.replace("_", "-")
    val = n.attrs.get(key)
    if want is True:
        return val is not None
    if val is None:
        return False
    if callable(want):
        return bool(want(val))
    if key in ("rel", "class"):
        return str(want).lower() in val.lower().split()
    return val.lower() == str(want).lower()


def _collect_text(node: Node, parts: List[str], skip) -> None:
    for c in node.children:
        if isinstance(c, str):
            parts.append(c)
        elif c.tag not in skip:
            if c.tag in BLOCK:
                parts.append(" ")
            if c.tag == "img":
                continue
            _collect_text(c, parts, skip)
            if c.tag in BLOCK:
                parts.append(" ")


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document")
        self.stack = [self.root]
        self.doctype = ""

    def handle_decl(self, decl):
        if decl.lower().startswith("doctype"):
            self.doctype = decl

    def handle_starttag(self, tag, attrs):
        if tag in AUTO_CLOSE:
            for i in range(len(self.stack) - 1, 0, -1):
                t = self.stack[i].tag
                if t == tag:
                    del self.stack[i:]
                    break
                if t in ("ul", "ol", "table", "div", "section", "body", "select", "dl"):
                    break
        parent = self.stack[-1]
        d = {}
        for k, v in attrs:
            if k not in d:
                d[k] = "" if v is None else v
        node = Node(tag, d, parent, self.getpos()[0])
        parent.children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack[-1].tag == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


class Document:
    def __init__(self, html: str):
        b = _Builder()
        try:
            b.feed(html or "")
            b.close()
        except Exception:  # HTMLParser is very lenient; keep whatever was parsed
            pass
        self.root = b.root
        self.doctype = b.doctype
        self.html_len = len(html or "")

    # Convenience accessors -------------------------------------------------
    def find_all(self, tags=None, **attrs):
        return self.root.find_all(tags, **attrs)

    def find(self, tags=None, **attrs):
        return self.root.find(tags, **attrs)

    @property
    def head(self) -> Node:
        return self.root.find("head") or self.root

    @property
    def body(self) -> Node:
        return self.root.find("body") or self.root

    def meta(self, name: str) -> List[str]:
        name = name.lower()
        out = []
        for m in self.root.find_all("meta"):
            key = (m.get("name") or m.get("property") or m.get("http-equiv")).lower()
            if key == name:
                out.append(m.get("content").strip())
        return out

    def meta1(self, name: str) -> str:
        v = self.meta(name)
        return v[0] if v else ""

    def links(self, rel: str) -> List[Node]:
        return [l for l in self.root.find_all("link") if rel.lower() in l.get("rel").lower().split()]

    def main_content(self) -> Node:
        """Best guess at the main content container (for word counts and text analysis)."""
        for tag in ("main", "article"):
            cands = self.root.find_all(tag)
            if cands:
                return max(cands, key=lambda n: len(n.text()))
        m = self.root.find(role="main")
        return m or self.body

    def main_text(self) -> str:
        node = self.main_content()
        if node is self.body:
            skip = HIDDEN_TEXT | {"nav", "header", "footer", "aside", "form"}
            return node.text(skip)
        return node.text()


def word_list(text: str) -> List[str]:
    return re.findall(r"[^\W_]+(?:['’-][^\W_]+)*", text.lower())
