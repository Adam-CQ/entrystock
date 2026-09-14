"""Peer-selection input and output value objects."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PeerCandidate:
    identifier: str
    confidence: float
    reasons: tuple[str, ...] = ()
