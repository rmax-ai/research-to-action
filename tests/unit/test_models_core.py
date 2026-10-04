"""Construction and JSON round-trip tests for the E1 model set."""

from __future__ import annotations

from governed_clinical_actions.models import (
    AssetRequirement,
    AuditEvent,
    Claim,
    ClaimType,
    ClinicalCriterion,
    CohortWaterfallStep,
    DataQualityReport,
    EvaluationCase,
    EvaluationResult,
    EvidenceRef,
    ExecutionPlan,
    HumanApproval,
    OntologyMapping,
    PolicyDecision,
    PolicyOutcome,
    ProcurementAllocation,
    ProcurementPlan,
    PurposeOfUse,
    ResearchRequest,
    RunRecord,
    SiteQueryRequest,
    SiteQueryResult,
    SupplierOffer,
    ToolEvent,
    ToolEventStatus,
    TransactionRecord,
)


def test_core_models_construct_and_round_trip() -> None:
    purpose = PurposeOfUse(code="commercial_ai_model_development", commercial=True)
    criterion = ClinicalCriterion(criterion_id="c1", concept="disease", value="NSCLC")
    asset = AssetRequirement(asset_id="a1", asset_type="pathology", modality="H&E")
    mapping = OntologyMapping(
        mapping_id="m1",
        source_system="synthetic",
        source_code="C34",
        source_term="NSCLC",
        candidates=["NCIT:C2926"],
        chosen_mapping="NCIT:C2926",
        source_version="v1",
    )
    request = ResearchRequest(
        request_id="request-1",
        original_intent="Find synthetic cases",
        clinical_criteria=[criterion],
        asset_requirements=[asset],
        purpose_of_use=purpose,
        ontology_mappings=[mapping],
        requested_quantity=200,
    )
    plan = ExecutionPlan(plan_id="plan-1", request_id=request.request_id)
    evidence = EvidenceRef(
        source="synthetic-site-a",
        source_version="fixture-1",
        source_hash="sha256-fixture",
        record_id="record-1",
    )
    site_request = SiteQueryRequest(
        query_id="query-1",
        request_id=request.request_id,
        plan_id=plan.plan_id,
        site_id="site-a",
    )
    site_result = SiteQueryResult(
        query_id=site_request.query_id,
        request_id=request.request_id,
        plan_id=plan.plan_id,
        site_id="site-a",
        fixture_version="fixture-1",
        raw_match_count=3,
        usable_match_count=2,
        evidence_refs=[evidence],
    )
    waterfall = CohortWaterfallStep(
        step_id="step-1",
        ordinal=1,
        label="disease",
        input_count=4,
        output_count=3,
        excluded_count=1,
        evidence_refs=[evidence],
    )
    quality = DataQualityReport(
        report_id="quality-1",
        config_version="quality-v1",
        completeness=0.9,
        validity=0.95,
        temporal_consistency=0.9,
        ontology_coverage=0.9,
        duplicate_rate=0.0,
        modality_linkage=0.9,
        follow_up_completeness=0.9,
        passed=True,
        evidence_refs=[evidence],
    )
    policy = PolicyDecision(
        decision_id="decision-1",
        request_id=request.request_id,
        purpose_code=purpose.code,
        decision=PolicyOutcome.ALLOW,
        policy_version="policy-v1",
        policy_hash="policy-hash",
        evidence_refs=[evidence],
    )
    claim = Claim(
        claim_id="claim-1",
        claim_type=ClaimType.DERIVED,
        subject="cohort",
        predicate="usable_count",
        value=2,
        evidence_refs=[evidence],
    )
    offer = SupplierOffer(
        offer_id="offer-1",
        supplier_id="supplier-1",
        site_id="site-a",
        available_count=3,
        cost_per_case=10.0,
    )
    allocation = ProcurementAllocation(
        offer_id=offer.offer_id,
        site_id=offer.site_id,
        quantity=2,
        estimated_cost=20.0,
    )
    procurement = ProcurementPlan(
        procurement_plan_id="procurement-1",
        request_id=request.request_id,
        target_quantity=2,
        allocations=[allocation],
        total_cost=20.0,
    )
    approval = HumanApproval(
        approval_id="approval-1",
        request_id=request.request_id,
        run_id="run-1",
        action="SUBMIT_PROCUREMENT",
    )
    transaction = TransactionRecord(
        transaction_id="transaction-1",
        request_id=request.request_id,
        procurement_plan_id=procurement.procurement_plan_id,
        action="SUBMIT_PROCUREMENT",
        approval_id=approval.approval_id,
    )
    tool_event = ToolEvent(
        run_id="run-1",
        sequence=1,
        tool_name="site.discover",
        idempotency_key="idem-1",
        status=ToolEventStatus.SUCCEEDED,
        input_digest="input",
        output_digest="output",
    )
    audit_event = AuditEvent(
        run_id="run-1",
        sequence=1,
        event_type="workflow.created",
        actor="workflow",
        payload_digest="payload",
    )
    run = RunRecord(
        run_id="run-1",
        request_id=request.request_id,
        plan_id=plan.plan_id,
        replay_digest="replay",
        workflow_version="workflow-v1",
    )
    evaluation_case = EvaluationCase(
        case_id="case-1",
        category="cohort",
        input_text=request.original_intent,
    )
    evaluation_result = EvaluationResult(case_id=evaluation_case.case_id, status="PASS")

    objects = [
        request,
        criterion,
        asset,
        purpose,
        mapping,
        plan,
        site_request,
        site_result,
        waterfall,
        quality,
        policy,
        evidence,
        claim,
        offer,
        procurement,
        approval,
        transaction,
        tool_event,
        audit_event,
        run,
        evaluation_case,
        evaluation_result,
    ]
    for obj in objects:
        assert obj.schema_version == 1
        assert obj.__class__.model_validate_json(obj.model_dump_json()) == obj
        assert obj.model_dump(mode="json")["schema_version"] == 1
