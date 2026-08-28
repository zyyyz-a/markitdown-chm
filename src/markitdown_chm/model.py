"""Small immutable value objects used during conversion."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Topic:
    """One HTML topic in a CHM table of contents."""

    path: str
    title: str
    depth: int = 0


@dataclass(frozen=True, slots=True)
class ProjectMetadata:
    """Relevant fields from a CHM project file."""

    title: str | None = None
    contents_file: str | None = None
    default_topic: str | None = None
