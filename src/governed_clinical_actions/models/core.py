"""Versioned E1 domain contracts.

The models describe the boundaries needed by the first vertical slice.  They
are intentionally small, but keep identity, policy, provenance, and action
fields explicit so later epics can extend them with a deliberate version.
"""

from __future__ import annotations

from enum import Enum, StrEnum
from typing import Annotated, Any

from pydantic import BeforeValidator, Field, model_validator

from .base import BoundaryModel, stable_digest


class ClaimType(StrEnum):
    FACT = "FACT"
    DERIVED = "DERIVED"
    INFERRED = "INFERRED"
    HUMAN_DECISION = "HUMAN_DECISION"


class PolicyOutcome(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class ApprovalDecision(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PENDING = "PENDING"


class TransactionState(StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    FULFILLING = "FULFILLING"
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"


class RunStatus(StrEnum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ToolEventStatus(StrEnum):
    STARTED = "STARTED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class EvaluationStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


def _enum_converter(enum_type: type[Enum]):
    def convert(value: object) -> Enum:
        return value if isinstance(value, enum_type) else enum_type(value)

    return convert


ClaimTypeValue = Annotated[ClaimType, BeforeValidator(_enum_converter(ClaimType))]
PolicyOutcomeValue = Annotated[PolicyOutcome, BeforeValidator(_enum_converter(PolicyOutcome))]
ApprovalDecisionValue = Annotated[
    ApprovalDecision, BeforeValidator(_enum_converter(ApprovalDecision))
]
TransactionStateValue = Annotated[
    TransactionState, BeforeValidator(_enum_converter(TransactionState))
]
RunStatusValue = Annotated[RunStatus, BeforeValidator(_enum_converter(RunStatus))]
ToolEventStatusValue = Annotated[
    ToolEventStatus, BeforeValidator(_enum_converter(ToolEventStatus))
]
EvaluationStatusValue = Annotated[
    EvaluationStatus, BeforeValidator(_enum_converter(EvaluationStatus))
]


class ClinicalCriterion(BoundaryModel):
    criterion_id: str
    concept: str
    operator: str = "equals"
    value: str | int | float | bool | None = None
    values: list[str] = Field(default_factory=list)
    description: str | None = None
    timing_relation: str | None = None
    required: bool = True


class AssetRequirement(BoundaryModel):
    asset_id: str
    asset_type: str
    modality: str | None = None
    required: bool = True
    timing_relation: str | None = None
    quantity: int | None = Field(default=None, ge=1)
    acceptable_substitutes: list[str] = Field(default_factory=list)


class PurposeOfUse(BoundaryModel):
    code: str
    description: str | None = None
    commercial: bool = False
    ai_training: bool = False
    deidentified_release: bool = True
    requested_by: str | None = None


class OntologyMapping(BoundaryModel):
    mapping_id: str
    source_system: str
    source_code: str
    source_term: str
    candidates: list[str] = Field(default_factory=list)
    chosen_mapping: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    method: str | None = None
    source_version: str
    source_hash: str | None = None
    review_state: str = "RESOLVED"


class ResearchRequest(BoundaryModel):
    request_id: str
    revision: int = Field(default=1, ge=1)
    parent_request_id: str | None = None
    original_intent: str
    clinical_criteria: list[ClinicalCriterion] = Field(default_factory=list)
    asset_requirements: list[AssetRequirement] = Field(default_factory=list)
    purpose_of_use: PurposeOfUse
    requested_quantity: int = Field(default=1, ge=1)
    minimum_follow_up_months: int | None = Field(default=None, ge=0)
    optimization_preference: str | None = None
    ontology_mappings: list[OntologyMapping] = Field(default_factory=list)
    unresolved_ambiguities: list[str] = Field(default_factory=list)


class ExecutionPlan(BoundaryModel):
    plan_id: str
    request_id: str
    request_revision: int = Field(default=1, ge=1)
    steps: list[str] = Field(default_factory=list)
    tool_names: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    workflow_version: str = "e1.workflow.v1"
    config_version: str = "e1.config.v1"
    ontology_version: str = "e1.ontology.v1"
    policy_version: str = "e1.policy.v1"
    plan_hash: str | None = None

    @model_validator(mode="after")
    def populate_plan_hash(self) -> ExecutionPlan:
        if self.plan_hash is None:
            self.plan_hash = self.content_hash()
        return self

    def content_hash(self) -> str:
        """Hash material plan content without circular identity fields."""

        return stable_digest(self.model_dump(exclude={"plan_id", "plan_hash"}))

    def with_content_hash(self) -> ExecutionPlan:
        """Return a copy with the deterministic content hash populated."""

        return self.model_copy(update={"plan_hash": self.content_hash()})


class SiteQueryRequest(BoundaryModel):
    query_id: str
    request_id: str
    plan_id: str
    site_id: str
    criteria: list[ClinicalCriterion] = Field(default_factory=list)
    requested_fields: list[str] = Field(default_factory=list)
    adapter_version: str = "e1.adapter.v1"
    fixture_version: str = "synthetic.e1.v1"
    release_mode: str = "aggregate"


class SiteQueryResult(BoundaryModel):
    query_id: str
    request_id: str
    plan_id: str
    site_id: str
    fixture_version: str
    result_hash: str | None = None
    raw_match_count: int = Field(default=0, ge=0)
    usable_match_count: int = Field(default=0, ge=0)
    exclusion_counts: dict[str, int] = Field(default_factory=dict)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)

    @model_validator(mode="after")
    def populate_result_hash(self) -> SiteQueryResult:
        if self.result_hash is None:
            material = self.model_dump(exclude={"result_hash", "evidence_refs"})
            self.result_hash = stable_digest(material)
        return self


class CohortWaterfallStep(BoundaryModel):
    step_id: str
    ordinal: int = Field(ge=1)
    label: str
    input_count: int = Field(ge=0)
    output_count: int = Field(ge=0)
    excluded_count: int = Field(ge=0)
    exclusion_reason: str | None = None
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class DataQualityReport(BoundaryModel):
    report_id: str
    subject_id: str | None = None
    config_version: str
    completeness: float = Field(ge=0.0, le=1.0)
    validity: float = Field(ge=0.0, le=1.0)
    temporal_consistency: float = Field(ge=0.0, le=1.0)
    ontology_coverage: float = Field(ge=0.0, le=1.0)
    duplicate_rate: float = Field(ge=0.0, le=1.0)
    modality_linkage: float = Field(ge=0.0, le=1.0)
    follow_up_completeness: float = Field(ge=0.0, le=1.0)
    threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    passed: bool
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class PolicyDecision(BoundaryModel):
    decision_id: str
    request_id: str
    purpose_code: str
    decision: PolicyOutcomeValue
    policy_version: str
    policy_hash: str
    reason_codes: list[str] = Field(default_factory=list)
    explanation: str | None = None
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class EvidenceRef(BoundaryModel):
    evidence_id: str | None = None
    source: str
    source_version: str
    source_hash: str
    locator: str | None = None
    record_id: str | None = None
    parent_evidence_id: str | None = None
    drill_down_refs: list[str] = Field(default_factory=list)
    transformations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def populate_evidence_id(self) -> EvidenceRef:
        if self.evidence_id is None:
            material = self.model_dump(exclude={"evidence_id"})
            self.evidence_id = f"ev_{stable_digest(material)[:24]}"
        return self

    def chain_ids(self) -> tuple[str, ...]:
        """Return this reference followed by its explicit drill-down IDs."""

        identifier = self.evidence_id or ""
        return (identifier, *self.drill_down_refs)


class Claim(BoundaryModel):
    claim_id: str
    claim_type: ClaimTypeValue
    subject: str
    predicate: str
    value: Any
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    explanation: str | None = None


class SupplierOffer(BoundaryModel):
    offer_id: str
    supplier_id: str
    site_id: str
    available_count: int = Field(ge=0)
    cost_per_case: float = Field(ge=0.0)
    fixed_cost: float = Field(default=0.0, ge=0.0)
    turnaround_days: int = Field(default=0, ge=0)
    quality_score: float = Field(default=1.0, ge=0.0, le=1.0)
    diversity_group: str | None = None
    modalities: list[str] = Field(default_factory=list)
    purpose_restrictions: list[str] = Field(default_factory=list)


class ProcurementAllocation(BoundaryModel):
    offer_id: str
    site_id: str
    quantity: int = Field(ge=0)
    estimated_cost: float = Field(ge=0.0)


class ProcurementPlan(BoundaryModel):
    procurement_plan_id: str
    request_id: str
    target_quantity: int = Field(ge=1)
    allocations: list[ProcurementAllocation] = Field(default_factory=list)
    total_cost: float = Field(default=0.0, ge=0.0)
    estimated_turnaround_days: int = Field(default=0, ge=0)
    objective: str = "minimize_cost"
    approval_state: ApprovalDecisionValue = ApprovalDecision.PENDING
    assumptions: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class HumanApproval(BoundaryModel):
    approval_id: str
    request_id: str
    run_id: str
    action: str
    decision: ApprovalDecisionValue = ApprovalDecision.PENDING
    approver_id: str | None = None
    approval_token_digest: str | None = None
    scope_digest: str | None = None
    reason: str | None = None


class TransactionRecord(BoundaryModel):
    transaction_id: str
    request_id: str
    procurement_plan_id: str
    action: str
    state: TransactionStateValue = TransactionState.DRAFT
    external_reference: str | None = None
    blocked_reason: str | None = None
    approval_id: str | None = None
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class ToolEvent(BoundaryModel):
    event_id: str | None = None
    run_id: str
    sequence: int = Field(ge=1)
    tool_name: str
    idempotency_key: str
    status: ToolEventStatusValue
    input_digest: str
    output_digest: str | None = None
    attempt: int = Field(default=1, ge=1)
    error_code: str | None = None

    @model_validator(mode="after")
    def populate_event_id(self) -> ToolEvent:
        if self.event_id is None:
            material = self.model_dump(exclude={"event_id"})
            self.event_id = f"evt_{stable_digest(material)[:24]}"
        return self


class AuditEvent(BoundaryModel):
    event_id: str | None = None
    run_id: str
    sequence: int = Field(ge=1)
    event_type: str
    actor: str
    payload_digest: str
    previous_event_hash: str | None = None
    event_hash: str | None = None

    @model_validator(mode="after")
    def populate_hashes(self) -> AuditEvent:
        if self.event_hash is None:
            self.event_hash = stable_digest(
                self.model_dump(exclude={"event_hash", "event_id"})
            )
        if self.event_id is None:
            self.event_id = f"audit_{self.event_hash[:24]}"
        return self


class RunRecord(BoundaryModel):
    run_id: str
    request_id: str
    request_revision: int = Field(default=1, ge=1)
    plan_id: str
    replay_digest: str
    workflow_version: str
    config_versions: dict[str, str] = Field(default_factory=dict)
    status: RunStatusValue = RunStatus.CREATED
    state: str = "CREATED"
    tool_events: list[ToolEvent] = Field(default_factory=list)
    audit_event_ids: list[str] = Field(default_factory=list)
    result_digest: str | None = None
    error_code: str | None = None


class EvaluationCase(BoundaryModel):
    case_id: str
    category: str
    input_text: str
    expected_request_assertions: dict[str, Any] = Field(default_factory=dict)
    expected_policy: PolicyOutcomeValue | None = None
    expected_evidence_classes: list[str] = Field(default_factory=list)
    requires_approval: bool = False


class EvaluationResult(BoundaryModel):
    case_id: str
    status: EvaluationStatusValue
    structured_diffs: list[str] = Field(default_factory=list)
    unsupported_claim_count: int = Field(default=0, ge=0)
    authorization_violations: int = Field(default=0, ge=0)
    provenance_failures: int = Field(default=0, ge=0)
    explanation_quality: float | None = Field(default=None, ge=0.0, le=1.0)
