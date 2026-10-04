"""Python validation of the shared TypeScript/Python parity fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from governed_clinical_actions.models import (
    Claim,
    EvidenceRef,
    ExecutionPlan,
    ResearchRequest,
    ToolEvent,
)

ROOT = Path(__file__).parents[2]
VALID = {
    "request.json": ResearchRequest,
    "plan.json": ExecutionPlan,
    "evidence.json": EvidenceRef,
    "claim.json": Claim,
}


@pytest.mark.parametrize(("filename", "model"), VALID.items())
def test_valid_parity_fixture(filename: str, model: type[object]) -> None:
    payload = json.loads((ROOT / "fixtures" / "parity" / "valid" / filename).read_text())
    if filename == "claim.json":
        assert isinstance(Claim.model_validate(payload), Claim)
    else:
        assert isinstance(model.model_validate(payload), model)  # type: ignore[attr-defined]


def test_valid_tool_events_fixture() -> None:
    payload = json.loads(
        (ROOT / "fixtures" / "parity" / "valid" / "tool-events.json").read_text()
    )
    events = [ToolEvent.model_validate(item) for item in payload]
    assert len(events) == 1


@pytest.mark.parametrize(
    "filename",
    ["unknown-version.json", "unknown-field.json", "invalid-claim-type.json"],
)
def test_invalid_parity_fixture(filename: str) -> None:
    payload = json.loads((ROOT / "fixtures" / "parity" / "invalid" / filename).read_text())
    model = Claim if filename == "invalid-claim-type.json" else EvidenceRef
    with pytest.raises((ValidationError, ValueError)):
        model.model_validate(payload)
