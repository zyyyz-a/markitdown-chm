# markitdown-chm

[![CI](https://github.com/zyyyz-a/markitdown-chm/actions/workflows/ci.yml/badge.svg)](https://github.com/zyyyz-a/markitdown-chm/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Secure, cross-platform CHM-to-Markdown support for
[Microsoft MarkItDown](https://github.com/microsoft/markitdown). It turns legacy
Compiled HTML Help archives into one structured Markdown document suitable for
search, documentation migration, and retrieval-augmented generation.

This project addresses [microsoft/markitdown#14](https://github.com/microsoft/markitdown/issues/14).
The issue remains open despite an earlier unmerged attempt. `markitdown-chm`
uses MarkItDown's supported plugin API and an in-process CHM reader with wheels
for Windows, macOS, and Linux.

## Why this implementation

- Preserves the `.hhc` table-of-contents order and nesting instead of sorting
  files alphabetically.
- Uses the `.hhp` project title, contents file, and default topic when present.
- Rewrites cross-topic links to stable anchors in the combined Markdown.
- Detects UTF-8/UTF-16 BOMs and declared HTML charsets, including common CJK
  code pages.
- Applies explicit limits to input size, member count, topic count, per-topic
  size, and total expanded HTML.
- Runs without shelling out to `7z`, `hh.exe`, or another executable.
- Ships a typed API, standalone CLI, automated tests, and reproducible CI.

## Install

```bash
pip install markitdown-chm
```

MarkItDown discovers the package through its `markitdown.plugin` entry point.

## Use with MarkItDown

```bash
markitdown --list-plugins
markitdown --use-plugins manual.chm -o manual.md
```

```python
from markitdown import MarkItDown

converter = MarkItDown(enable_plugins=True)
result = converter.convert("manual.chm")
print(result.text_content)
```

The package also provides a direct command for CHM-only workflows:

```bash
markitdown-chm manual.chm -o manual.md
```

## Safety limits

CHM is an archive format and inputs may be untrusted. The defaults reject
files larger than 512 MiB, archives with more than 20,000 members or 5,000
HTML topics, individual topics larger than 8 MiB, and more than 256 MiB of
expanded HTML. The direct CLI exposes flags for lowering these limits.

The converter extracts content in memory and removes active HTML content such
as scripts, embedded objects, frames, and event-handler attributes before
creating Markdown. See [SECURITY.md](SECURITY.md) for the trust model.

## Development

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy
uv build
```

The design rationale and comparison with the stalled upstream implementation
are documented in [docs/upstream-gap-analysis.md](docs/upstream-gap-analysis.md).

## Scope

The output is a single Markdown document. Images and other binary resources
remain referenced by their CHM-relative paths; the plugin does not export an
asset directory. Password-protected or corrupt archives are rejected.

## License

`markitdown-chm` is MIT licensed. Its `pylibmspack` dependency is MIT licensed
and its wheels bundle `libmspack` under LGPL-2.1; see the dependency's package
metadata for corresponding source and replacement instructions.
