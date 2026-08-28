"""MarkItDown plugin for Microsoft Compiled HTML Help files."""

from __future__ import annotations

from typing import Any

from markitdown import PRIORITY_SPECIFIC_FILE_FORMAT, MarkItDown

from .converter import ChmConverter
from .errors import ChmConversionError, ChmSecurityError

__all__ = [
    "ChmConversionError",
    "ChmConverter",
    "ChmSecurityError",
    "register_converters",
]

__plugin_interface_version__ = 1
__version__ = "0.1.0"


def register_converters(markitdown: MarkItDown, **_: Any) -> None:
    """Register CHM conversion with a MarkItDown instance."""
    markitdown.register_converter(
        ChmConverter(),
        priority=PRIORITY_SPECIFIC_FILE_FORMAT,
    )
