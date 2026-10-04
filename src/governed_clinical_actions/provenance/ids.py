"""Deterministic request, plan, run, and replay identities."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..models import ExecutionPlan, ResearchRequest, stable_digest


class ReplayIdentityMismatchError(ValueError):
    """Raised when persisted state was created with different replay inputs."""

    def __init__(self, expected: str, actual: str):
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Replay identity mismatch: expected {expected}, calculated {actual}"
        )


ReplayIdentityMismatch = ReplayIdentityMismatchError
ReplayMismatchError = ReplayIdentityMismatchError


def _without(value: Any, *fields: str) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(exclude=set(fields))
    if isinstance(value, Mapping):
        return {key: item for key, item in value.items() if key not in fields}
    return value


def request_id_for(request: ResearchRequest | Mapping[str, Any]) -> str:
    """Derive a stable request identity from its immutable content."""

    return f"req_{stable_digest(_without(request, "request_id"))[:24]}"


def plan_hash(plan: ExecutionPlan | Mapping[str, Any]) -> str:
    """Hash material execution-plan content, excluding its assigned ID/hash."""

    if isinstance(plan, ExecutionPlan):
        return plan.content_hash()
    return stable_digest(_without(plan, "plan_id", "plan_hash"))


def plan_id_for(plan: ExecutionPlan | Mapping[str, Any]) -> str:
    """Derive a stable plan identity from its material content."""

    return f"plan_{plan_hash(plan)[:24]}"


def run_id_for(
    request: ResearchRequest | Mapping[str, Any] | str,
    plan: ExecutionPlan | Mapping[str, Any] | str,
    replay: str | None = None,
) -> str:
    """Derive a stable run identity from request, plan, and replay identity."""

    request_value = (
        request_id_for(request) if not isinstance(request, str) else request
    )
    plan_value = plan_id_for(plan) if not isinstance(plan, str) else plan
    return f"run_{stable_digest((request_value, plan_value, replay))[:24]}"


def replay_digest(
    inputs: Any,
    config: Any,
    versions: Any,
) -> str:
    """Create the identity required to replay a deterministic workflow."""

    return stable_digest(
        {
            "inputs": inputs,
            "config": config,
            "versions": versions,
        }
    )


def calculate_replay_digest(
    inputs: Any,
    config: Any,
    versions: Any,
) -> str:
    """Explicit alias for callers that prefer a verb-named API."""

    return replay_digest(inputs, config, versions)


def assert_replay_identity(
    expected: str,
    inputs: Any,
    config: Any,
    versions: Any,
) -> str:
    """Calculate and verify replay identity, failing with a typed error."""

    actual = replay_digest(inputs, config, versions)
    if actual != expected:
        raise ReplayIdentityMismatchError(expected, actual)
    return actual


def verify_replay_digest(expected: str, actual: str) -> None:
    """Verify an already-calculated digest."""

    if expected != actual:
        raise ReplayIdentityMismatchError(expected, actual)


def request_revision_id(parent_request_id: str, revision: int, content: Any) -> str:
    """Create a stable identity for a revision linked to a prior request."""

    return f"req_{stable_digest((parent_request_id, revision, content))[:24]}"
