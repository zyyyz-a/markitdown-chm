"""Turn ordered CHM HTML topics into a single safe Markdown document."""

from __future__ import annotations

import posixpath
import re
from collections.abc import Mapping, Sequence
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup, Tag
from markdownify import markdownify

from .model import Topic
from .parsing import normalize_member_path, stable_anchor

_ACTIVE_ELEMENTS = (
    "script",
    "style",
    "noscript",
    "iframe",
    "frame",
    "frameset",
    "object",
    "embed",
    "applet",
    "form",
    "button",
    "input",
    "select",
    "textarea",
)
_CHM_SCHEME_PATH = re.compile(r"^(?:mk:@MSITStore:|ms-its:).*?::/?(.*)$", re.IGNORECASE)


def render_topic(
    html_text: str,
    topic: Topic,
    anchors: Mapping[str, str],
    member_lookup: Mapping[str, str],
) -> tuple[str, str]:
    """Sanitize and render one HTML topic, returning Markdown and its best title."""
    soup = BeautifulSoup(html_text, "html.parser")
    title = _best_title(soup, topic.title)
    for element in soup.find_all(_ACTIVE_ELEMENTS):
        element.decompose()
    for element in soup.find_all(True):
        if not isinstance(element, Tag):
            continue
        for attribute in list(element.attrs):
            if attribute.casefold().startswith("on") or attribute.casefold() == "srcdoc":
                del element.attrs[attribute]
    _rewrite_links(soup, topic.path, anchors, member_lookup)
    _demote_headings(soup)

    body = soup.body or soup
    for title_node in body.find_all("title"):
        title_node.decompose()
    rendered = markdownify(str(body), heading_style="ATX", bullets="-").strip()
    return rendered, title


def combine_topics(
    topics: Sequence[Topic],
    rendered: Sequence[tuple[str, str]],
    document_title: str,
) -> str:
    """Combine rendered topics with a hierarchical, linkable table of contents."""
    lines = [f"# {document_title}", "", "## Contents", ""]
    for topic, (_, title) in zip(topics, rendered, strict=True):
        indent = "  " * min(topic.depth, 10)
        lines.append(f"{indent}- [{_escape_link_text(title)}](#{stable_anchor(topic.path)})")

    for topic, (content, title) in zip(topics, rendered, strict=True):
        lines.extend(
            [
                "",
                "---",
                "",
                f'<a id="{stable_anchor(topic.path)}"></a>',
                "",
                f"## {title}",
                "",
                f"_CHM source: `{topic.path}`_",
                "",
                content,
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _rewrite_links(
    soup: BeautifulSoup,
    current_path: str,
    anchors: Mapping[str, str],
    member_lookup: Mapping[str, str],
) -> None:
    current_dir = posixpath.dirname(current_path)
    for link in soup.find_all("a", href=True):
        if not isinstance(link, Tag):
            continue
        href = str(link.get("href", "")).strip()
        lowered = href.casefold()
        if lowered.startswith("javascript:"):
            del link.attrs["href"]
            continue
        if lowered.startswith(("http://", "https://", "mailto:", "tel:", "data:")):
            continue

        special = _CHM_SCHEME_PATH.match(href)
        if special:
            href = special.group(1)
        parts = urlsplit(href)
        if not parts.path:
            continue
        candidate = normalize_member_path(
            posixpath.join(current_dir, unquote(parts.path).replace("\\", "/"))
        )
        actual = member_lookup.get(candidate.casefold())
        if actual and actual.casefold() in anchors:
            link["href"] = f"#{anchors[actual.casefold()]}"


def _demote_headings(soup: BeautifulSoup) -> None:
    for level in range(6, 0, -1):
        for heading in soup.find_all(f"h{level}"):
            heading.name = f"h{min(level + 2, 6)}"


def _best_title(soup: BeautifulSoup, fallback: str) -> str:
    for selector in ("title", "h1", "h2"):
        node = soup.find(selector)
        if node:
            value = " ".join(node.get_text(" ", strip=True).split())
            if value:
                return value
    return fallback.strip() or "Untitled topic"


def _escape_link_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
