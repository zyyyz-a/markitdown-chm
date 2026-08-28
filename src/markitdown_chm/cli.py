"""Small direct CLI for CHM-only conversion workflows."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from markitdown import StreamInfo

from .converter import ChmConverter
from .errors import ChmConversionError
from .limits import ConversionLimits


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="markitdown-chm",
        description="Convert a Microsoft Compiled HTML Help file to Markdown.",
    )
    parser.add_argument("input", type=Path, help="input .chm file")
    parser.add_argument("-o", "--output", type=Path, help="output .md file; defaults to stdout")
    parser.add_argument("--max-input-mib", type=int, default=512)
    parser.add_argument("--max-members", type=int, default=20_000)
    parser.add_argument("--max-topics", type=int, default=5_000)
    parser.add_argument("--max-topic-mib", type=int, default=8)
    parser.add_argument("--max-total-topic-mib", type=int, default=256)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    limits = ConversionLimits(
        max_input_bytes=args.max_input_mib * 1024 * 1024,
        max_members=args.max_members,
        max_topics=args.max_topics,
        max_topic_bytes=args.max_topic_mib * 1024 * 1024,
        max_total_topic_bytes=args.max_total_topic_mib * 1024 * 1024,
    )
    converter = ChmConverter(limits=limits)
    try:
        with args.input.open("rb") as stream:
            result = converter.convert(
                stream,
                StreamInfo(
                    extension=args.input.suffix,
                    filename=args.input.name,
                    local_path=str(args.input),
                ),
            )
    except (OSError, ValueError, ChmConversionError) as exc:
        print(f"markitdown-chm: {exc}", file=sys.stderr)
        return 2

    if args.output:
        args.output.write_text(result.text_content, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(result.text_content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
