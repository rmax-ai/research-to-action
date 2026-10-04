"""Identity, evidence, and claim primitives."""

from ..models import Claim, ClaimType, EvidenceRef
from .claims import make_claim, require_claim_type
from .evidence import (
    EvidenceRegistry,
    EvidenceResolutionError,
    assert_claim_evidence_resolves,
    evidence_ids,
    validate_evidence_chain,
)
from .ids import (
    ReplayIdentityMismatch,
    ReplayIdentityMismatchError,
    ReplayMismatchError,
    assert_replay_identity,
    calculate_replay_digest,
    plan_hash,
    plan_id_for,
    replay_digest,
    request_id_for,
    request_revision_id,
    run_id_for,
    verify_replay_digest,
)

__all__ = [
    "Claim",
    "ClaimType",
    "EvidenceRef",
    "EvidenceRegistry",
    "EvidenceResolutionError",
    "ReplayIdentityMismatch",
    "ReplayIdentityMismatchError",
    "ReplayMismatchError",
    "assert_claim_evidence_resolves",
    "assert_replay_identity",
    "calculate_replay_digest",
    "evidence_ids",
    "make_claim",
    "plan_hash",
    "plan_id_for",
    "replay_digest",
    "request_id_for",
    "request_revision_id",
    "require_claim_type",
    "run_id_for",
    "validate_evidence_chain",
    "verify_replay_digest",
]
