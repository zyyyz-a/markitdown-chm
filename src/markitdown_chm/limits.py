"""Resource limits for processing untrusted legacy archives."""

from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(frozen=True, slots=True)
class ConversionLimits:
    """Hard limits applied before and during CHM expansion."""

    max_input_bytes: int = 512 * 1024 * 1024
    max_members: int = 20_000
    max_topics: int = 5_000
    max_topic_bytes: int = 8 * 1024 * 1024
    max_total_topic_bytes: int = 256 * 1024 * 1024

    def __post_init__(self) -> None:
        for field in fields(self):
            name = field.name
            value = getattr(self, name)
            if value <= 0:
                raise ValueError(f"{name} must be greater than zero")
