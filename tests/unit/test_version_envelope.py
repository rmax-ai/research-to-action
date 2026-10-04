"""Version and closed-boundary contract tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from governed_clinical_actions.models import (
    ExecutionPlan,
    ExecutionPlanEnvelope,
    IncompatibleSchemaVersionError,
    ResearchRequest,
    ResearchRequestEnvelope,
    ensure_supported_schema_version,
    is_schema_version_compatible,
    parse_boundary_payload,
)


def _request_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "request_id": "request-1",
        "revision": 1,
        "original_intent": "synthetic request",
        "purpose_of_use": {"code": "commercial_ai_model_development"},
    }


def test_unknown_schema_version_is_rejected_at_boundary() -> None:
    payload = _request_payload()
    payload["schema_version"] = 99
    with pytest.raises(IncompatibleSchemaVersionError):
        ResearchRequest.model_validate_boundary(payload)
    with pytest.raises(ValidationError):
        ResearchRequest.model_validate(payload)


def test_unknown_fields_are_rejected() -> None:
    payload = _request_payload()
    payload["not_in_contract"] = True
    with pytest.raises(ValidationError):
        ResearchRequest.model_validate(payload)


def test_version_compatibility_is_explicit() -> None:
    assert ensure_supported_schema_version(1) == 1
    assert is_schema_version_compatible(1)
    assert not is_schema_version_compatible(0)
    with pytest.raises(IncompatibleSchemaVersionError):
        ensure_supported_schema_version(2)


def test_discriminated_payload_dispatch_is_closed() -> None:
    request = ResearchRequestEnvelope.model_validate(
        {"kind": "research_request", "payload": _request_payload()}
    )
    assert isinstance(parse_boundary_payload(request.model_dump()), ResearchRequestEnvelope)

    plan = ExecutionPlanEnvelope.model_validate(
        {
            "kind": "execution_plan",
            "payload": {
                "schema_version": 1,
                "plan_id": "plan-1",
                "request_id": "request-1",
            },
        }
    )
    assert isinstance(parse_boundary_payload(plan.model_dump()), ExecutionPlanEnvelope)

    with pytest.raises(ValidationError):
        parse_boundary_payload(
            {"kind": "unknown", "payload": {"schema_version": 1}}
        )
    assert ExecutionPlan.model_validate(plan.payload).plan_id == "plan-1"
