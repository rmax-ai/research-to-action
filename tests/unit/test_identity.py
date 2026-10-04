"""Identity and replay digest tests."""

from __future__ import annotations

import pytest

from governed_clinical_actions.models import ExecutionPlan, PurposeOfUse, ResearchRequest
from governed_clinical_actions.provenance import (
    ReplayIdentityMismatchError,
    assert_replay_identity,
    plan_hash,
    plan_id_for,
    replay_digest,
    request_id_for,
    run_id_for,
)


def _request() -> ResearchRequest:
    draft = ResearchRequest(
        request_id="placeholder",
        original_intent="synthetic NSCLC request",
        purpose_of_use=PurposeOfUse(code="commercial_ai_model_development"),
    )
    return draft.model_copy(update={"request_id": request_id_for(draft)})


def test_request_plan_and_run_ids_are_stable() -> None:
    request = _request()
    plan = ExecutionPlan(plan_id="placeholder", request_id=request.request_id, steps=["discover"])
    plan = plan.model_copy(update={"plan_id": plan_id_for(plan)})
    assert request_id_for(request) == request.request_id
    assert plan_id_for(plan) == plan.plan_id
    assert run_id_for(request, plan, "replay-1") == run_id_for(request, plan, "replay-1")


def test_material_plan_change_flips_hash() -> None:
    request = _request()
    first = ExecutionPlan(plan_id="p", request_id=request.request_id, steps=["discover"])
    second = first.model_copy(update={"steps": ["discover", "quality"]})
    assert plan_hash(first) != plan_hash(second)


def test_replay_digest_mismatch_is_typed_and_explicit() -> None:
    expected = replay_digest({"request": "a"}, {"retry": 1}, {"workflow": "v1"})
    assert_replay_identity(
        expected,
        {"request": "a"},
        {"retry": 1},
        {"workflow": "v1"},
    )
    with pytest.raises(ReplayIdentityMismatchError) as exc_info:
        assert_replay_identity(
            expected,
            {"request": "changed"},
            {"retry": 1},
            {"workflow": "v1"},
        )
    assert exc_info.value.expected == expected
    assert exc_info.value.actual != expected
