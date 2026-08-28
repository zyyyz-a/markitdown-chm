from __future__ import annotations

from pathlib import Path

import pytest
from markitdown import MarkItDown


@pytest.mark.integration
def test_real_chm_converts_through_markitdown_plugin() -> None:
    fixture = Path(__file__).parent / "fixtures" / "sample.chm"
    result = MarkItDown(enable_plugins=True).convert(fixture)
    assert result.title == "NSIS Users Manual"
    assert result.text_content.startswith("# NSIS Users Manual\n")
    assert "## Contents" in result.text_content
    assert "Introduction to NSIS" in result.text_content
    assert "Scripting Reference" in result.text_content
    assert len(result.text_content) > 500_000
