"""Deterministic freshness, coverage, and provenance quality checks."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal, Mapping, Sequence

QualityStatus = Literal["complete", "warning", "blocked", "not_evaluable"]
QUALITY_VERSION = "v1"


@dataclass(frozen=True)
class QualityThreshold:
    warning_age_days: int
    blocking_age_days: int
    minimum_coverage: int = 1
    blocking_coverage: int = 0
    required_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0 <= self.warning_age_days <= self.blocking_age_days:
            raise ValueError("age thresholds must be non-negative and ordered")
        if self.minimum_coverage < 0 or self.blocking_coverage < 0:
            raise ValueError("coverage thresholds must not be negative")


DEFAULT_THRESHOLDS: Mapping[str, QualityThreshold] = {
    "prices": QualityThreshold(3, 10),
    "fundamentals": QualityThreshold(120, 365, required_fields=("revenue", "operating_income", "net_income")),
    "forecasts": QualityThreshold(90, 365),
    "classifications": QualityThreshold(365, 365),
    "peers": QualityThreshold(90, 365, minimum_coverage=3),
}


@dataclass(frozen=True)
class DataQualityReport:
    status: QualityStatus
    retrieved_at: datetime | None = None
    missing_fields: tuple[str, ...] = ()
    effective_date: date | None = None
    coverage: int = 0
    expected_coverage: int | None = None
    age_days: int | None = None
    source: str = "unknown"
    reason: str = ""
    threshold_version: str = QUALITY_VERSION

    @property
    def quality_status(self) -> QualityStatus:
        return self.status


@dataclass(frozen=True)
class DataQualitySummary:
    reports: tuple[DataQualityReport, ...]
    overall_status: QualityStatus
    warnings: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    threshold_version: str = QUALITY_VERSION


def assess_source(source: str, *, analysis_date: date, retrieved_at: datetime | None, effective_date: date | None, coverage: int, expected_coverage: int | None = None, missing_fields: Sequence[str] = (), data_quality: str = "valid", threshold: QualityThreshold | None = None) -> DataQualityReport:
    """Assess one source without hiding missing provenance or invalid data."""
    threshold = threshold or DEFAULT_THRESHOLDS.get(source, QualityThreshold(90, 365))
    expected_coverage = expected_coverage or threshold.minimum_coverage
    missing = tuple(dict.fromkeys(missing_fields))
    age_date = effective_date or (retrieved_at.date() if retrieved_at else None)
    age_days = (analysis_date - age_date).days if age_date else None
    reasons: list[str] = []
    status: QualityStatus = "complete"
    if age_days is None:
        return DataQualityReport("not_evaluable", retrieved_at, missing, effective_date, coverage, expected_coverage, None, source, "effective or retrieval date is missing")
    if age_days < 0:
        return DataQualityReport("blocked", retrieved_at, missing, effective_date, coverage, expected_coverage, age_days, source, "record is dated after the analysis date")
    if data_quality not in {"valid", "acceptable", "complete"}:
        status, reasons = "blocked", [f"source quality status is {data_quality}"]
    if missing:
        status = "blocked" if any(field in threshold.required_fields for field in missing) else "warning"
        reasons.append("missing fields: " + ", ".join(missing))
    if coverage <= threshold.blocking_coverage:
        status, reasons = "blocked", [*reasons, f"coverage {coverage} is below blocking minimum {threshold.blocking_coverage + 1}"]
    elif coverage < threshold.minimum_coverage:
        status, reasons = "warning", [*reasons, f"coverage {coverage} is below minimum {threshold.minimum_coverage}"]
    if age_days > threshold.blocking_age_days:
        status, reasons = "blocked", [*reasons, f"data is {age_days} days old; blocking threshold is {threshold.blocking_age_days}"]
    elif age_days > threshold.warning_age_days:
        if status == "complete":
            status = "warning"
        reasons.append(f"data is {age_days} days old; warning threshold is {threshold.warning_age_days}")
    return DataQualityReport(status, retrieved_at, missing, effective_date, coverage, expected_coverage, age_days, source, "; ".join(reasons) or "all required quality checks passed")


def summarize_quality(reports: Sequence[DataQualityReport]) -> DataQualitySummary:
    reports = tuple(reports)
    rank = {"complete": 0, "warning": 1, "not_evaluable": 2, "blocked": 3}
    overall = max((report.status for report in reports), key=rank.get, default="not_evaluable")
    warnings = tuple(f"{report.source}: {report.reason}" for report in reports if report.status == "warning")
    blocking = tuple(f"{report.source}: {report.reason}" for report in reports if report.status in {"blocked", "not_evaluable"})
    return DataQualitySummary(reports, overall, warnings, blocking)


evaluate_data_quality = assess_source
