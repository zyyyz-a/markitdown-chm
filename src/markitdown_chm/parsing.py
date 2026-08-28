"""Parsers for the text-based metadata stored inside CHM archives."""

from __future__ import annotations

import codecs
import hashlib
import html
import posixpath
import re
from collections.abc import Iterable, Mapping

from bs4 import BeautifulSoup, Tag

from .model import ProjectMetadata, Topic

_META_CHARSET = re.compile(
    rb"<meta\s+[^>]*(?:charset\s*=\s*[\"']?\s*([^\s\"'/>;]+)|"
    rb"content\s*=\s*[\"'][^\"']*charset\s*=\s*([^\s\"'/>;]+))",
    re.IGNORECASE,
)
_WINDOWS_CODE_PAGE = re.compile(r"^(?:windows-|cp-?)(\d+)$", re.IGNORECASE)
_HTML_SUFFIXES = (".htm", ".html", ".xhtml", ".shtml")


def normalize_member_path(value: str) -> str:
    """Return a comparable CHM member path without allowing traversal."""
    cleaned = html.unescape(value).split("#", 1)[0].split("?", 1)[0]
    cleaned = cleaned.replace("\\", "/").lstrip("/")
    normalized = posixpath.normpath(cleaned)
    if normalized in {"", "."} or normalized == ".." or normalized.startswith("../"):
        return ""
    return normalized


def decode_text(data: bytes) -> str:
    """Decode HTML/project bytes using BOM and declared-charset evidence first."""
    if data.startswith(codecs.BOM_UTF8):
        return data.decode("utf-8-sig")
    if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return data.decode("utf-16")

    declared = _declared_charset(data[:8192])
    candidates = [declared, "utf-8", "gb18030", "cp1252"]
    for encoding in candidates:
        if not encoding:
            continue
        try:
            return data.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return data.decode("utf-8", errors="replace")


def parse_project(data: bytes) -> ProjectMetadata:
    """Parse the small INI-like `.hhp` project file."""
    values: dict[str, str] = {}
    in_options = False
    for raw_line in decode_text(data).splitlines():
        line = raw_line.strip().lstrip("\ufeff")
        if line.startswith("[") and line.endswith("]"):
            in_options = line.casefold() == "[options]"
            continue
        if not in_options or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip().casefold()] = value.strip().strip('"')
    return ProjectMetadata(
        title=values.get("title"),
        contents_file=normalize_member_path(values.get("contents file", "")) or None,
        default_topic=normalize_member_path(values.get("default topic", "")) or None,
    )


def parse_toc(data: bytes, member_lookup: Mapping[str, str]) -> list[Topic]:
    """Parse an HTML Help contents file while preserving its nested order."""
    soup = BeautifulSoup(decode_text(data), "html.parser")
    topics: list[Topic] = []
    seen: set[str] = set()
    for obj in soup.find_all("object"):
        if not isinstance(obj, Tag):
            continue
        params = {
            str(param.get("name", "")).casefold(): str(param.get("value", "")).strip()
            for param in obj.find_all("param", recursive=False)
            if isinstance(param, Tag)
        }
        path = normalize_member_path(params.get("local", ""))
        actual = member_lookup.get(path.casefold())
        if not actual or actual.casefold() in seen or not is_html_member(actual):
            continue
        title = params.get("name", "").strip() or posixpath.basename(actual)
        topics.append(Topic(path=actual, title=title, depth=_list_depth(obj)))
        seen.add(actual.casefold())
    return topics


def select_topics(
    members: Iterable[str],
    toc_topics: Iterable[Topic],
    default_topic: str | None,
) -> list[Topic]:
    """Keep TOC order, then append HTML pages omitted by the TOC deterministically."""
    html_members = sorted(
        (path for path in members if is_html_member(path) and not is_system_member(path)),
        key=str.casefold,
    )
    by_key = {path.casefold(): path for path in html_members}
    ordered: list[Topic] = []
    seen: set[str] = set()

    for topic in toc_topics:
        key = topic.path.casefold()
        if key not in seen:
            ordered.append(topic)
            seen.add(key)

    if default_topic:
        actual = by_key.get(default_topic.casefold())
        if actual and actual.casefold() not in seen:
            ordered.insert(0, Topic(path=actual, title=posixpath.basename(actual)))
            seen.add(actual.casefold())

    for path in html_members:
        key = path.casefold()
        if key not in seen:
            ordered.append(Topic(path=path, title=posixpath.basename(path)))
            seen.add(key)
    return ordered


def stable_anchor(path: str) -> str:
    """Create a deterministic, collision-resistant anchor for a CHM topic."""
    stem = posixpath.splitext(posixpath.basename(path))[0].casefold()
    slug = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", stem).strip("-") or "topic"
    digest = hashlib.sha1(path.casefold().encode("utf-8"), usedforsecurity=False).hexdigest()[:8]
    return f"chm-{slug}-{digest}"


def is_html_member(path: str) -> bool:
    return normalize_member_path(path).casefold().endswith(_HTML_SUFFIXES)


def is_system_member(path: str) -> bool:
    cleaned = path.replace("\\", "/").lstrip("/")
    return cleaned.startswith(("#", "::"))


def _declared_charset(head: bytes) -> str | None:
    match = _META_CHARSET.search(head)
    if not match:
        return None
    raw = next((group for group in match.groups() if group), b"")
    value = raw.decode("ascii", errors="ignore").strip().casefold()
    code_page = _WINDOWS_CODE_PAGE.match(value)
    if code_page:
        value = f"cp{code_page.group(1)}"
    try:
        codecs.lookup(value)
    except LookupError:
        return None
    return value


def _list_depth(node: Tag) -> int:
    return max(0, sum(1 for parent in node.parents if getattr(parent, "name", None) == "ul") - 1)
