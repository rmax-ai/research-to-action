"""Persisted typed workflow state used for offline pause/resume."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Protocol

from pydantic import BeforeValidator, Field

from ..audit import AppendOnlyAuditLog
from ..models import AuditEvent, BoundaryModel, RunRecord


class WorkflowState(StrEnum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


WorkflowPhase = WorkflowState


def _coerce_workflow_state(value: object) -> WorkflowState:
    return value if isinstance(value, WorkflowState) else WorkflowState(value)


class PersistedWorkflowState(BoundaryModel):
    run: RunRecord
    phase: Annotated[
        WorkflowState, BeforeValidator(_coerce_workflow_state)
    ] = WorkflowState.CREATED
    next_step: int = 0
    completed_tools: list[str] = Field(default_factory=list)
    outputs: dict[str, Any] = Field(default_factory=dict)
    audit_events: list[AuditEvent] = Field(default_factory=list)

    def audit_log(self) -> AppendOnlyAuditLog:
        return AppendOnlyAuditLog(self.audit_events)

    def with_audit_log(self, log: AppendOnlyAuditLog) -> PersistedWorkflowState:
        return self.model_copy(update={"audit_events": list(log.events)})

    def can_transition_to(self, target: WorkflowState) -> bool:
        allowed = {
            WorkflowState.CREATED: {WorkflowState.RUNNING, WorkflowState.FAILED},
            WorkflowState.RUNNING: {
                WorkflowState.PAUSED,
                WorkflowState.COMPLETED,
                WorkflowState.FAILED,
            },
            WorkflowState.PAUSED: {WorkflowState.RUNNING, WorkflowState.FAILED},
            WorkflowState.COMPLETED: set(),
            WorkflowState.FAILED: set(),
        }
        return target in allowed[self.phase]


class StateStore(Protocol):
    def save(self, state: PersistedWorkflowState) -> None: ...

    def load(self, run_id: str) -> PersistedWorkflowState: ...


class InMemoryStateStore:
    """Deterministic persistence substitute for the E1 integration fixture."""

    def __init__(self):
        self._states: dict[str, PersistedWorkflowState] = {}

    def save(self, state: PersistedWorkflowState) -> None:
        self._states[state.run.run_id] = state.model_copy(deep=True)

    def load(self, run_id: str) -> PersistedWorkflowState:
        try:
            return self._states[run_id].model_copy(deep=True)
        except KeyError as exc:
            raise KeyError(f"No persisted workflow state for {run_id!r}") from exc

    def exists(self, run_id: str) -> bool:
        return run_id in self._states


class JsonStateStore:
    """File-free serializable store adapter for callers that persist JSON."""

    def __init__(self):
        self._payloads: dict[str, str] = {}

    def save(self, state: PersistedWorkflowState) -> None:
        self._payloads[state.run.run_id] = state.model_dump_json()

    def load(self, run_id: str) -> PersistedWorkflowState:
        try:
            return PersistedWorkflowState.model_validate_json_boundary(self._payloads[run_id])
        except KeyError as exc:
            raise KeyError(f"No persisted workflow state for {run_id!r}") from exc
