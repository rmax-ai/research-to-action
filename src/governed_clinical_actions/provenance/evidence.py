"""Evidence references and drill-down validation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from ..models import Claim, EvidenceRef


class EvidenceResolutionError(ValueError):
    """Raised when a claim points at evidence that cannot be resolved."""

    def __init__(self, evidence_id: str, message: str | None = None):
        self.evidence_id = evidence_id
        super().__init__(message or f"Evidence reference {evidence_id!r} cannot be resolved")


class EvidenceRegistry:
    """Small in-memory evidence index used by the E1 workflow and tests."""

    def __init__(self, refs: Iterable[EvidenceRef] = ()):
        self._refs: dict[str, EvidenceRef] = {}
        for ref in refs:
            self.add(ref)

    def add(self, ref: EvidenceRef) -> EvidenceRef:
        if ref.evidence_id is None:
            raise EvidenceResolutionError("", "EvidenceRef must have an evidence_id")
        existing = self._refs.get(ref.evidence_id)
        if existing is not None and existing != ref:
            raise EvidenceResolutionError(ref.evidence_id, "Conflicting evidence reference")
        self._refs[ref.evidence_id] = ref
        return ref

    def get(self, evidence_id: str) -> EvidenceRef:
        try:
            return self._refs[evidence_id]
        except KeyError as exc:
            raise EvidenceResolutionError(evidence_id) from exc

    def resolve(self, evidence_id: str) -> EvidenceRef:
        return self.get(evidence_id)

    def __contains__(self, evidence_id: object) -> bool:
        return evidence_id in self._refs

    def __len__(self) -> int:
        return len(self._refs)

    def as_mapping(self) -> Mapping[str, EvidenceRef]:
        return dict(self._refs)

    def resolve_chain(
        self,
        ref: EvidenceRef,
        _seen: set[str] | None = None,
    ) -> tuple[EvidenceRef, ...]:
        """Resolve a parent and all explicit drill-down references."""

        seen = _seen or set()
        identifier = ref.evidence_id or ""
        if identifier in seen:
            return ()
        seen.add(identifier)
        resolved: list[EvidenceRef] = []
        if ref.parent_evidence_id:
            resolved.extend(self.resolve_chain(self.get(ref.parent_evidence_id), seen))
        resolved.append(self.get(identifier))
        for child_id in ref.drill_down_refs:
            child = self.get(child_id)
            resolved.extend(self.resolve_chain(child, seen))
        return tuple(resolved)


def evidence_ids(claim: Claim) -> tuple[str, ...]:
    """Return the direct evidence IDs attached to a claim."""

    return tuple(ref.evidence_id or "" for ref in claim.evidence_refs)


def assert_claim_evidence_resolves(
    claim: Claim,
    registry: EvidenceRegistry | Mapping[str, EvidenceRef],
) -> tuple[EvidenceRef, ...]:
    """Resolve every direct claim reference and its drill-down chain."""

    index = registry if isinstance(registry, EvidenceRegistry) else EvidenceRegistry(
        registry.values()
    )
    resolved: list[EvidenceRef] = []
    for ref in claim.evidence_refs:
        resolved.extend(index.resolve_chain(ref))
    return tuple(resolved)


def validate_evidence_chain(
    claim: Claim,
    registry: EvidenceRegistry | Mapping[str, EvidenceRef],
) -> bool:
    """Boolean convenience wrapper around strict chain resolution."""

    assert_claim_evidence_resolves(claim, registry)
    return True
