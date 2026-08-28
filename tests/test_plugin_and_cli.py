from __future__ import annotations

from pathlib import Path
from typing import Any

from markitdown import DocumentConverterResult

import markitdown_chm.cli as cli_module
from markitdown_chm import ChmConverter, register_converters


class RegistrationSpy:
    def __init__(self) -> None:
        self.converter: ChmConverter | None = None

    def register_converter(self, converter: ChmConverter, *, priority: float) -> None:
        assert priority == 0.0
        self.converter = converter


def test_register_converters_adds_chm_converter() -> None:
    spy = RegistrationSpy()
    register_converters(spy)  # type: ignore[arg-type]
    assert isinstance(spy.converter, ChmConverter)


def test_cli_writes_output(monkeypatch: Any, tmp_path: Path) -> None:
    source = tmp_path / "input.chm"
    output = tmp_path / "output.md"
    source.write_bytes(b"ITSF fake")

    class StubConverter:
        def __init__(self, **_: Any) -> None:
            pass

        def convert(self, *_: Any, **__: Any) -> DocumentConverterResult:
            return DocumentConverterResult(markdown="# Converted\n", title="Converted")

    monkeypatch.setattr(cli_module, "ChmConverter", StubConverter)
    assert cli_module.main([str(source), "-o", str(output)]) == 0
    assert output.read_text(encoding="utf-8") == "# Converted\n"


def test_cli_reports_missing_input(capsys: Any, tmp_path: Path) -> None:
    code = cli_module.main([str(tmp_path / "missing.chm")])
    assert code == 2
    assert "markitdown-chm:" in capsys.readouterr().err
