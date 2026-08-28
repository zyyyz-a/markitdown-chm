from __future__ import annotations

from markitdown_chm.model import Topic
from markitdown_chm.parsing import stable_anchor
from markitdown_chm.rendering import combine_topics, render_topic


def test_render_topic_sanitizes_active_content_and_rewrites_links() -> None:
    topic = Topic("docs/start.html", "Fallback")
    target = Topic("api/reference.htm", "Reference")
    anchors = {target.path.casefold(): stable_anchor(target.path)}
    lookup = {target.path.casefold(): target.path}
    source = """<html><head><title>Start here</title></head><body>
    <script>alert(1)</script><h1>Heading</h1>
    <a href="../api/reference.htm#method" onclick="bad()">API</a>
    <a href="javascript:alert(1)">bad</a></body></html>"""
    rendered, title = render_topic(source, topic, anchors, lookup)
    assert title == "Start here"
    assert "alert(1)" not in rendered
    assert "onclick" not in rendered
    assert f"](#{stable_anchor(target.path)})" in rendered
    assert "### Heading" in rendered


def test_combine_topics_emits_nested_contents_and_source_paths() -> None:
    topics = [Topic("a.html", "A", 0), Topic("b.html", "B", 1)]
    output = combine_topics(topics, [("one", "Alpha"), ("two", "Beta")], "Manual")
    assert output.startswith("# Manual\n")
    assert "- [Alpha](#chm-a-" in output
    assert "  - [Beta](#chm-b-" in output
    assert "_CHM source: `b.html`_" in output
    assert output.endswith("\n")
