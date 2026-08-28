from __future__ import annotations

import io

import pytest
from markitdown import StreamInfo

import markitdown_chm.converter as converter_module
from conftest import FakeArchive, sample_payloads
from markitdown_chm import ChmConversionError, ChmConverter, ChmSecurityError
from markitdown_chm.limits import ConversionLimits


def test_accepts_magic_without_consuming_stream() -> None:
    stream = io.BytesIO(b"ITSFpayload")
    stream.seek(2)
    converter = ChmConverter()
    assert not converter.accepts(stream, StreamInfo())
    assert stream.tell() == 2
    stream.seek(0)
    assert converter.accepts(stream, StreamInfo())
    assert stream.tell() == 0


def test_accepts_extension_and_mime() -> None:
    converter = ChmConverter()
    assert converter.accepts(io.BytesIO(), StreamInfo(extension=".CHM"))
    assert converter.accepts(
        io.BytesIO(),
        StreamInfo(mimetype="application/vnd.ms-htmlhelp; charset=binary"),
    )
    assert not converter.accepts(io.BytesIO(), StreamInfo(extension=".zip"))


def test_convert_rejects_false_extension() -> None:
    with pytest.raises(ChmConversionError, match="ITSF"):
        ChmConverter().convert(io.BytesIO(b"not chm"), StreamInfo(extension=".chm"))


def test_convert_orders_topics_decodes_cjk_and_sanitizes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeArchive.payloads = sample_payloads()
    monkeypatch.setattr(converter_module, "ChmArchive", FakeArchive)
    result = ChmConverter().convert_bytes(b"ITSF fake archive")
    output = result.text_content
    assert result.title == "Widget SDK Manual"
    assert output.index("## Getting Started") < output.index("## API 参考")
    assert output.index("## API 参考") < output.index("## Appendix")
    assert "调用接口" in output
    assert "bad()" not in output
    assert "](\\#" not in output
    assert "](#chm-api-" in output
    assert "](#chm-intro-" in output


def test_converter_falls_back_to_filename_title(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeArchive.payloads = {"/index.html": b"<html><body>Body</body></html>"}
    monkeypatch.setattr(converter_module, "ChmArchive", FakeArchive)
    result = ChmConverter().convert_bytes(b"ITSF fake", filename="legacy-help.chm")
    assert result.title == "legacy-help"


def test_converter_prefers_html_title_over_filename(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeArchive.payloads = {
        "/index.html": b"<html><title>Product Manual</title><body>Body</body></html>"
    }
    monkeypatch.setattr(converter_module, "ChmArchive", FakeArchive)
    result = ChmConverter().convert_bytes(b"ITSF fake", filename="legacy-help.chm")
    assert result.title == "Product Manual"


def test_converter_rejects_input_member_topic_and_expansion_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ChmSecurityError, match="input exceeds"):
        ChmConverter(limits=ConversionLimits(max_input_bytes=4)).convert_bytes(b"ITSF!")

    FakeArchive.payloads = {"/a.html": b"a", "/b.html": b"b"}
    monkeypatch.setattr(converter_module, "ChmArchive", FakeArchive)
    with pytest.raises(ChmSecurityError, match="members"):
        ChmConverter(limits=ConversionLimits(max_members=1)).convert_bytes(b"ITSF fake")
    with pytest.raises(ChmSecurityError, match="HTML topics"):
        ChmConverter(limits=ConversionLimits(max_topics=1)).convert_bytes(b"ITSF fake")

    FakeArchive.payloads = {"/a.html": b"long"}
    with pytest.raises(ChmSecurityError, match="topic"):
        ChmConverter(limits=ConversionLimits(max_topic_bytes=3)).convert_bytes(b"ITSF fake")

    FakeArchive.payloads = {"/a.html": b"abc", "/b.html": b"def"}
    with pytest.raises(ChmSecurityError, match="total limit"):
        ChmConverter(limits=ConversionLimits(max_total_topic_bytes=5)).convert_bytes(b"ITSF fake")


def test_converter_rejects_archive_without_html(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeArchive.payloads = {"/readme.txt": b"nothing"}
    monkeypatch.setattr(converter_module, "ChmArchive", FakeArchive)
    with pytest.raises(ChmConversionError, match="no supported HTML"):
        ChmConverter().convert_bytes(b"ITSF fake")


def test_limits_require_positive_values() -> None:
    with pytest.raises(ValueError, match="max_topics"):
        ConversionLimits(max_topics=0)
