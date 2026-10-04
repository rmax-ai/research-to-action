"""Claim construction helpers and epistemic-state checks."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ..models import Claim, ClaimType, EvidenceRef
from ..models.base import stable_digest


def make_claim(
    *,
    subject: str,
    predicate: str,
    value: Any,
    claim_type: ClaimType,
    evidence_refs: Iterable[EvidenceRef] = (),
    confidence: float | None = None,
    claim_id: str | None = None,
    explanation: str | None = None,
) -> Claim:
    """Create a stable claim with explicit epistemic typing."""

    refs = list(evidence_refs)
    identifier = claim_id or f"claim_{stable_digest((subject, predicate, value, refs))[:24]}"
    return Claim(
        claim_id=identifier,
        claim_type=claim_type,
        subject=subject,
        predicate=predicate,
        value=value,
        evidence_refs=refs,
        confidence=confidence,
        explanation=explanation,
    )


def require_claim_type(claim: Claim, expected: ClaimType) -> Claim:
    """Assert the epistemic type expected by a downstream boundary."""

    if claim.claim_type != expected:
        raise ValueError(
            f"Claim {claim.claim_id} has type {claim.claim_type}, expected {expected}"
        )
    return claim
