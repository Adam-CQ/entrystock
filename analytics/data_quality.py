"""Data freshness and quality value objects."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

QualityStatus = Literal["unknown", "complete", "partial", "invalid"]


@dataclass(frozen=True)
class DataQualityReport:
    status: QualityStatus
    retrieved_at: datetime | None = None
    missing_fields: tuple[str, ...] = ()
