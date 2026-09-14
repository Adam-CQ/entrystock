"""Peer-selection input and output value objects."""

from dataclasses import dataclass
from decimal import Decimal
from math import isfinite
from typing import Sequence

from analytics.provider_contracts import CompanyMetadata


@dataclass(frozen=True)
class PeerCandidate:
    identifier: str
    confidence: float
    reasons: tuple[str, ...] = ()
    score: float = 0.0
    component_scores: tuple[tuple[str, float | None], ...] = ()


@dataclass(frozen=True)
class PeerProposal:
    candidates: tuple[PeerCandidate, ...]
    eligible_count: int
    minimum_candidates: int
    sufficient_universe: bool
    explanation: str


_COMPONENTS = ("business_model", "industry", "size", "growth", "profitability", "capital_intensity", "theme")


def propose_peers(
    selected: CompanyMetadata,
    candidates: Sequence[CompanyMetadata],
    *,
    limit: int = 10,
    minimum_candidates: int = 5,
) -> PeerProposal:
    """Rank eligible companies by transparent attribute similarity.

    Exact categorical matches score one point. Numeric attributes score by
    relative proximity, and themes score by Jaccard overlap. Missing values
    are recorded as unavailable and never contribute a match.
    """

    if limit < 1 or minimum_candidates < 1:
        raise ValueError("limit and minimum_candidates must be positive")
    eligible = tuple(candidate for candidate in candidates if candidate.company_id != selected.company_id)
    ranked = sorted((_score_candidate(selected, candidate) for candidate in eligible), key=lambda item: (-item.score, item.identifier))
    selected_candidates = tuple(ranked[:limit])
    enough = len(eligible) >= minimum_candidates
    explanation = (
        f"{len(eligible)} eligible companies; minimum is {minimum_candidates}."
        if enough else
        f"Insufficient peer universe: {len(eligible)} eligible companies; minimum is {minimum_candidates}."
    )
    return PeerProposal(selected_candidates, len(eligible), minimum_candidates, enough, explanation)


def _score_candidate(selected: CompanyMetadata, candidate: CompanyMetadata) -> PeerCandidate:
    values: list[tuple[str, float | None]] = []
    reasons: list[str] = []
    for name in _COMPONENTS:
        attribute = "themes" if name == "theme" else name
        left = getattr(selected, attribute)
        right = getattr(candidate, attribute)
        component, reason = _component_score(name, left, right)
        values.append((name, component))
        reasons.append(reason)
    available = [value for _, value in values if value is not None]
    score = sum(available) / len(available) if available else 0.0
    return PeerCandidate(candidate.company_id, round(score, 6), tuple(reasons), round(score, 6), tuple(values))


def _component_score(name: str, left: object, right: object) -> tuple[float | None, str]:
    if left is None or right is None or (isinstance(left, tuple) and not left) or (isinstance(right, tuple) and not right):
        return None, f"{name}: unavailable (not counted)"
    if name in {"business_model", "industry"}:
        match = float(left == right)
        return match, f"{name}: {'match' if match else 'different'}"
    if name == "theme":
        left_set, right_set = set(left), set(right)
        overlap = len(left_set & right_set) / len(left_set | right_set)
        return overlap, f"theme: {len(left_set & right_set)} shared theme(s)"
    left_number, right_number = float(left), float(right)
    if not isfinite(left_number) or not isfinite(right_number) or left_number == 0:
        return None, f"{name}: unavailable (not counted)"
    similarity = max(0.0, 1.0 - abs(left_number - right_number) / abs(left_number))
    return similarity, f"{name}: {similarity:.2f} similarity"
