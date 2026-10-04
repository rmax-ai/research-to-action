"""Offline pause/resume integration fixture."""

from __future__ import annotations

from governed_clinical_actions.models import ExecutionPlan, PurposeOfUse, ResearchRequest
from governed_clinical_actions.provenance import request_id_for
from governed_clinical_actions.workflow import (
    InMemoryStateStore,
    ToolDefinition,
    ToolRegistry,
    WorkflowEngine,
)


def _engine(store: InMemoryStateStore) -> WorkflowEngine:
    draft = ResearchRequest(
        request_id="placeholder",
        original_intent="synthetic resume fixture",
        purpose_of_use=PurposeOfUse(code="commercial_ai_model_development"),
    )
    request = draft.model_copy(update={"request_id": request_id_for(draft)})
    plan = ExecutionPlan(
        plan_id="plan-resume",
        request_id=request.request_id,
        tool_names=["discover", "quality"],
    )
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="discover",
            handler=lambda args: {"step": "discover", "request_id": args["request_id"]},
        )
    )
    registry.register(
        ToolDefinition(
            name="quality",
            handler=lambda args: {"step": "quality", "request_id": args["request_id"]},
        )
    )
    return WorkflowEngine(request, plan, registry, state_store=store)


def test_resume_replays_the_same_audit_sequence() -> None:
    resumed_store = InMemoryStateStore()
    resumed_engine = _engine(resumed_store)
    paused = resumed_engine.run(max_steps=1)
    assert paused.phase == "PAUSED"
    resumed = resumed_engine.resume()
    assert resumed.phase == "COMPLETED"

    clean = _engine(InMemoryStateStore()).run()
    assert resumed.run.run_id == clean.run.run_id
    assert [event.event_id for event in resumed.audit_events] == [
        event.event_id for event in clean.audit_events
    ]
    assert resumed.run.result_digest == clean.run.result_digest
    assert resumed.run.audit_event_ids == clean.run.audit_event_ids
