"""Compatibility import surface for discriminated boundary payloads."""

from .envelopes import (
    BoundaryPayload,
    BoundaryPayloadAdapter,
    ExecutionPlanEnvelope,
    ResearchRequestEnvelope,
    parse_boundary_payload,
)

__all__ = [
    "BoundaryPayload",
    "BoundaryPayloadAdapter",
    "ExecutionPlanEnvelope",
    "ResearchRequestEnvelope",
    "parse_boundary_payload",
]
