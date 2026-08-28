"""Public exceptions raised by markitdown-chm."""


class ChmConversionError(RuntimeError):
    """The CHM archive could not be decoded into useful Markdown."""


class ChmSecurityError(ChmConversionError):
    """The archive exceeded a configured resource or safety limit."""
