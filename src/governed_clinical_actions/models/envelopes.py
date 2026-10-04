"""Closed discriminated unions for polymorphic boundary payloads."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, TypeAdapter

from .base import BoundaryModel
from .core import ExecutionPlan, ResearchRequest


class ResearchRequestEnvelope(BoundaryModel):
    kind: Literal["research_request"]
    payload: ResearchRequest


class ExecutionPlanEnvelope(BoundaryModel):
    kind: Literal["execution_plan"]
    payload: ExecutionPlan


BoundaryPayload = Annotated[
    ResearchRequestEnvelope | ExecutionPlanEnvelope,
    Field(discriminator="kind"),
]
BoundaryPayloadAdapter = TypeAdapter(BoundaryPayload)


def parse_boundary_payload(value: object) -> ResearchRequestEnvelope | ExecutionPlanEnvelope:
    """Dispatch a typed payload without permissive variant guessing."""

    return BoundaryPayloadAdapter.validate_python(value)


__all__ = [
    "BoundaryPayload",
    "BoundaryPayloadAdapter",
    "ExecutionPlanEnvelope",
    "ResearchRequestEnvelope",
    "parse_boundary_payload",
]
