from __future__ import annotations

from markitdown_chm.model import Topic
from markitdown_chm.parsing import (
    decode_text,
    normalize_member_path,
    parse_project,
    parse_toc,
    select_topics,
    stable_anchor,
)


def test_decode_text_honors_bom_and_declared_chinese_charset() -> None:
    assert decode_text(b"\xef\xbb\xbfhello") == "hello"
    html = '<meta charset="gb18030"><p>中文</p>'.encode("gb18030")
    assert "中文" in decode_text(html)


def test_decode_text_replaces_unknown_bytes() -> None:
    value = decode_text(b"\x81\x81\x81")
    assert isinstance(value, str)


def test_parse_project_reads_options_only() -> None:
    metadata = parse_project(
        b"[FILES]\ntitle=wrong\n[OPTIONS]\nTitle=Manual\nContents file=nav.hhc\n"
        b"Default topic=docs\\home.htm\n"
    )
    assert metadata.title == "Manual"
    assert metadata.contents_file == "nav.hhc"
    assert metadata.default_topic == "docs/home.htm"


def test_parse_toc_preserves_hierarchy_and_ignores_missing_members() -> None:
    data = b"""<ul><li><object><param name="Name" value="Home">
    <param name="Local" value="HOME.htm"></object>
    <ul><li><object><param name="Name" value="Child">
    <param name="Local" value="docs/child.html"></object></li></ul></li>
    <li><object><param name="Name" value="Missing">
    <param name="Local" value="404.html"></object></li></ul>"""
    topics = parse_toc(
        data,
        {"home.htm": "home.htm", "docs/child.html": "docs/child.html"},
    )
    assert topics == [
        Topic(path="home.htm", title="Home", depth=0),
        Topic(path="docs/child.html", title="Child", depth=1),
    ]


def test_select_topics_keeps_toc_order_and_appends_unlisted_pages() -> None:
    topics = select_topics(
        ["z.html", "home.htm", "docs/a.html", "#system.html"],
        [
            Topic("home.htm", "Home"),
            Topic("docs/a.html", "A", 1),
        ],
        "home.htm",
    )
    assert [topic.path for topic in topics] == ["home.htm", "docs/a.html", "z.html"]


def test_select_topics_places_unlisted_default_first() -> None:
    topics = select_topics(
        ["default.html", "listed.html"],
        [Topic("listed.html", "Listed")],
        "default.html",
    )
    assert [topic.path for topic in topics] == ["default.html", "listed.html"]


def test_paths_and_anchors_are_safe_and_stable() -> None:
    assert normalize_member_path("/docs\\intro.html#section") == "docs/intro.html"
    assert normalize_member_path("../../secret") == ""
    assert stable_anchor("a/index.html") != stable_anchor("b/index.html")
    assert stable_anchor("docs/中文.html").startswith("chm-中文-")
