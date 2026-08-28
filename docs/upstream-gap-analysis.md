# Upstream gap analysis

## Project selection

Microsoft's MarkItDown is a Python document-conversion tool used to prepare
Office files, PDFs, web pages, and other inputs for text analysis and AI
workflows. At the time this project was created, the repository had about
176,800 stars and 12,990 forks and used the MIT license.

CHM support is a documented gap: issue
[#14](https://github.com/microsoft/markitdown/issues/14) is open, labelled
`enhancement` and `good first issue`, and continued receiving interest in 2026.
CHM remains relevant for migrating legacy Windows product documentation into
searchable, model-friendly formats.

## Why not build on PR #1367

The existing [PR #1367](https://github.com/microsoft/markitdown/pull/1367) has
remained unmerged. Its own description says the implementation could not be
tested. A review of the published diff found several production risks:

1. It depends on `pychm`, a GPL project in maintenance mode whose latest PyPI
   release was in 2019 and which requires a separately installed native CHMlib.
2. It assumes CHM APIs while comments in the code acknowledge that those APIs
   may differ.
3. It sorts every HTML member alphabetically, losing the author's table of
   contents and chapter hierarchy.
4. It silently catches every per-page exception, which can return apparently
   successful but incomplete documents.
5. It has no input, member-count, decompression, or page-size limits.
6. It only tries UTF-8 and Windows-1252, so many multilingual help files are
   decoded incorrectly.
7. Its linked test vector was added, but the PR description states that the
   converter itself was not successfully tested.

## Implemented response

This repository takes the supported third-party plugin route described in
MarkItDown's own documentation. It uses `pylibmspack`, which provides in-process
CHM parsing, safe extraction primitives, current Python wheels across the three
major desktop platforms, and explicit read-size limits.

The implementation separates archive access, metadata parsing, sanitization,
topic ordering, link rewriting, rendering, and the MarkItDown adapter. Tests use
both isolated archive doubles and a redistributable real CHM fixture so that a
passing build demonstrates actual decompression rather than only mocked logic.

## Evidence boundaries

This is an independent compatibility plugin. It is not an official Microsoft
package, does not imply Microsoft sponsorship, and does not claim to resolve the
upstream issue until maintainers choose to reference or merge an implementation.

