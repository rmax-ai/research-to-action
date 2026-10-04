"""Offline provider determinism and tool-gate enforcement tests."""

from __future__ import annotations

import pytest

from governed_clinical_actions.llm import DeterministicMockLLM
from governed_clinical_actions.models import ExecutionPlan, PurposeOfUse, ResearchRequest
from governed_clinical_actions.workflow import (
    ToolCall,
    ToolDefinition,
    ToolEnforcementError,
    ToolGate,
    ToolRegistry,
)


def _request_and_plan() -> tuple[ResearchRequest, ExecutionPlan]:
    request = ResearchRequest(
        request_id="request-1",
        original_intent="synthetic request",
        purpose_of_use=PurposeOfUse(code="commercial_ai_model_development"),
    )
    plan = ExecutionPlan(plan_id="plan-1", request_id=request.request_id, tool_names=["echo"])
    return request, plan


def test_mock_llm_is_deterministic_and_non_authoritative() -> None:
    request, plan = _request_and_plan()
    provider = DeterministicMockLLM()
    assert provider.propose(request, plan) == provider.propose(request, plan)
    assert provider.propose(request, plan).tool_calls == ()


def test_tool_gate_is_required_and_idempotent() -> None:
    registry = ToolRegistry()
    registry.register(ToolDefinition(name="echo", handler=lambda value: value))
    with pytest.raises(ToolEnforcementError):
        registry.invoke("echo", {"request_id": "request-1"})
    gate = ToolGate(registry, ("echo",))
    call = ToolCall(name="echo", arguments={"request_id": "request-1"})
    first = gate.execute(run_id="run-1", call=call, sequence=1)
    second = gate.execute(run_id="run-1", call=call, sequence=99)
    assert first.event == second.event
    assert second.idempotent_replay
    with pytest.raises(ToolEnforcementError):
        gate.execute(
            run_id="run-1",
            call=ToolCall(name="unlisted", arguments={}),
            sequence=2,
        )
