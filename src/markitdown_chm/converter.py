"""MarkItDown adapter and bounded CHM conversion pipeline."""

from __future__ import annotations

import io
import posixpath
from collections.abc import Mapping
from typing import Any, BinaryIO, cast

from markitdown import (
    DocumentConverter,
    DocumentConverterResult,
    StreamInfo,
)
from pylibmspack import ChmArchive, ChmError

from .errors import ChmConversionError, ChmSecurityError
from .limits import ConversionLimits
from .model import ProjectMetadata, Topic
from .parsing import (
    decode_text,
    normalize_member_path,
    parse_project,
    parse_toc,
    select_topics,
    stable_anchor,
)
from .rendering import combine_topics, render_topic

CHM_MAGIC = b"ITSF"
CHM_EXTENSIONS = {".chm"}
CHM_MIME_TYPES = {"application/vnd.ms-htmlhelp", "application/x-chm"}


class ChmConverter(DocumentConverter):
    """Convert a CHM archive to one ordered Markdown document."""

    def __init__(
        self,
        *,
        limits: ConversionLimits | None = None,
    ) -> None:
        self.limits = limits or ConversionLimits()

    def accepts(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **_: Any,
    ) -> bool:
        """Recognize CHM by magic bytes, extension, or registered MIME type."""
        if _peek(file_stream, len(CHM_MAGIC)) == CHM_MAGIC:
            return True
        extension = (stream_info.extension or "").casefold()
        mimetype = (stream_info.mimetype or "").split(";", 1)[0].strip().casefold()
        return extension in CHM_EXTENSIONS or mimetype in CHM_MIME_TYPES

    def convert(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **_: Any,
    ) -> DocumentConverterResult:
        """Read, validate, order, sanitize, and render a CHM stream."""
        data = _bounded_read(file_stream, self.limits.max_input_bytes)
        if not data.startswith(CHM_MAGIC):
            raise ChmConversionError(
                "Input is labelled as CHM but does not start with ITSF magic bytes"
            )

        try:
            archive = ChmArchive.from_bytes(data)
            raw_entries = archive.files(include_system=True)
        except ChmError as exc:
            raise ChmConversionError(f"Unable to open CHM archive: {exc}") from exc

        if len(raw_entries) > self.limits.max_members:
            raise ChmSecurityError(
                f"CHM contains {len(raw_entries)} members; limit is {self.limits.max_members}"
            )

        raw_by_normalized: dict[str, str] = {}
        sizes: dict[str, int] = {}
        for entry in raw_entries:
            normalized = normalize_member_path(entry["name"])
            if not normalized:
                continue
            key = normalized.casefold()
            raw_by_normalized.setdefault(key, entry["name"])
            sizes.setdefault(key, int(entry["size"]))

        member_lookup = {key: normalize_member_path(raw) for key, raw in raw_by_normalized.items()}
        project = self._load_project(archive, raw_by_normalized, sizes)
        toc = self._load_toc(archive, project, raw_by_normalized, sizes, member_lookup)
        topics = select_topics(member_lookup.values(), toc, project.default_topic)
        if not topics:
            raise ChmConversionError("CHM archive contains no supported HTML topics")
        if len(topics) > self.limits.max_topics:
            raise ChmSecurityError(
                f"CHM contains {len(topics)} HTML topics; limit is {self.limits.max_topics}"
            )

        anchors = {topic.path.casefold(): stable_anchor(topic.path) for topic in topics}
        rendered: list[tuple[str, str]] = []
        total_bytes = 0
        for topic in topics:
            key = topic.path.casefold()
            declared_size = sizes.get(key, 0)
            if declared_size > self.limits.max_topic_bytes:
                raise ChmSecurityError(
                    f"CHM topic {topic.path!r} is {declared_size} bytes; "
                    f"limit is {self.limits.max_topic_bytes}"
                )
            payload = self._read_member(archive, raw_by_normalized[key], topic.path)
            total_bytes += len(payload)
            if total_bytes > self.limits.max_total_topic_bytes:
                raise ChmSecurityError(
                    "Expanded HTML exceeds total limit of "
                    f"{self.limits.max_total_topic_bytes} bytes"
                )
            rendered.append(render_topic(decode_text(payload), topic, anchors, member_lookup))

        title = (
            project.title
            or _first_meaningful_title(topics, rendered)
            or _stream_title(stream_info)
            or "CHM document"
        )
        return DocumentConverterResult(
            markdown=combine_topics(topics, rendered, title),
            title=title,
        )

    def convert_bytes(
        self,
        data: bytes,
        *,
        filename: str = "document.chm",
    ) -> DocumentConverterResult:
        """Convenience API for callers that already hold the CHM in memory."""
        return self.convert(
            io.BytesIO(data),
            StreamInfo(
                mimetype="application/vnd.ms-htmlhelp",
                extension=".chm",
                filename=filename,
            ),
        )

    def _load_project(
        self,
        archive: ChmArchive,
        raw_by_normalized: Mapping[str, str],
        sizes: Mapping[str, int],
    ) -> ProjectMetadata:
        candidates = sorted(
            (key for key in raw_by_normalized if key.endswith(".hhp")),
            key=str.casefold,
        )
        if not candidates:
            return ProjectMetadata()
        key = candidates[0]
        if sizes.get(key, 0) > self.limits.max_topic_bytes:
            raise ChmSecurityError("CHM project metadata exceeds the per-topic size limit")
        return parse_project(self._read_member(archive, raw_by_normalized[key], key))

    def _load_toc(
        self,
        archive: ChmArchive,
        project: ProjectMetadata,
        raw_by_normalized: Mapping[str, str],
        sizes: Mapping[str, int],
        member_lookup: Mapping[str, str],
    ) -> list[Topic]:
        preferred = project.contents_file.casefold() if project.contents_file else None
        candidates = sorted(
            (key for key in raw_by_normalized if key.endswith(".hhc")),
            key=lambda key: (key != preferred, key),
        )
        if not candidates:
            return []
        key = candidates[0]
        if sizes.get(key, 0) > self.limits.max_topic_bytes:
            raise ChmSecurityError("CHM table of contents exceeds the per-topic size limit")
        return parse_toc(
            self._read_member(archive, raw_by_normalized[key], key),
            member_lookup,
        )

    def _read_member(self, archive: ChmArchive, raw_path: str, display_path: str) -> bytes:
        try:
            return cast(
                bytes,
                archive.read(raw_path, max_size=self.limits.max_topic_bytes),
            )
        except ChmError as exc:
            raise ChmConversionError(f"Unable to read CHM member {display_path!r}: {exc}") from exc


def _bounded_read(stream: BinaryIO, limit: int) -> bytes:
    payload = stream.read(limit + 1)
    if len(payload) > limit:
        raise ChmSecurityError(f"CHM input exceeds the configured {limit}-byte limit")
    return payload


def _peek(stream: BinaryIO, size: int) -> bytes:
    try:
        position = stream.tell()
        data = stream.read(size)
        stream.seek(position)
        return data
    except (AttributeError, OSError, io.UnsupportedOperation):
        return b""


def _stream_title(stream_info: StreamInfo) -> str | None:
    value = stream_info.filename or stream_info.local_path
    if not value:
        return None
    name = posixpath.basename(value.replace("\\", "/"))
    return posixpath.splitext(name)[0] or None


def _first_meaningful_title(
    topics: list[Topic],
    rendered: list[tuple[str, str]],
) -> str | None:
    for topic, (_, title) in zip(topics, rendered, strict=True):
        basename = posixpath.basename(topic.path)
        if title and title.casefold() not in {basename.casefold(), topic.path.casefold()}:
            return title
    return None
