"""Claim typing and evidence-chain tests."""

from __future__ import annotations

import pytest

from governed_clinical_actions.models import ClaimType, EvidenceRef
from governed_clinical_actions.provenance import (
    EvidenceRegistry,
    EvidenceResolutionError,
    assert_claim_evidence_resolves,
    make_claim,
)


def test_claim_type_and_drill_down_chain_resolve() -> None:
    root = EvidenceRef(
        source="synthetic-site-a",
        source_version="fixture-1",
        source_hash="hash-a",
        locator="query/result",
        drill_down_refs=["child-id"],
    )
    child = EvidenceRef(
        evidence_id="child-id",
        source="synthetic-site-a",
        source_version="fixture-1",
        source_hash="hash-a",
        record_id="record-1",
        parent_evidence_id=root.evidence_id,
    )
    registry = EvidenceRegistry([root, child])
    claim = make_claim(
        subject="record-1",
        predicate="biomarker",
        value="KRAS G12C",
        claim_type=ClaimType.FACT,
        evidence_refs=[root],
    )
    resolved = assert_claim_evidence_resolves(claim, registry)
    assert claim.claim_type is ClaimType.FACT
    assert [ref.evidence_id for ref in resolved].count(child.evidence_id) >= 1


def test_unresolvable_evidence_fails_closed() -> None:
    ref = EvidenceRef(
        source="synthetic-site-b",
        source_version="fixture-1",
        source_hash="hash-b",
        drill_down_refs=["missing"],
    )
    claim = make_claim(
        subject="cohort",
        predicate="count",
        value=1,
        claim_type=ClaimType.DERIVED,
        evidence_refs=[ref],
    )
    with pytest.raises(EvidenceResolutionError):
        assert_claim_evidence_resolves(claim, EvidenceRegistry([ref]))
