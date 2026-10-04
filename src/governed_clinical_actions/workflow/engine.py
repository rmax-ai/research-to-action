"""Inspectable deterministic workflow runner."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from ..audit import AppendOnlyAuditLog
from ..models import (
    ExecutionPlan,
    ResearchRequest,
    RunRecord,
    RunStatus,
)
from ..provenance import (
    assert_replay_identity,
    replay_digest,
    run_id_for,
)
from .state import InMemoryStateStore, PersistedWorkflowState, StateStore, WorkflowPhase
from .tools import ToolCall, ToolGate, ToolRegistry

if TYPE_CHECKING:
    from ..llm import LLMProvider


class WorkflowIdentityError(ValueError):
    """Raised when a plan or persisted state does not match the request/run."""


class WorkflowEngine:
    """A tiny durable state machine with no hidden model authority."""

    def __init__(
        self,
        request: ResearchRequest,
        plan: ExecutionPlan,
        registry: ToolRegistry,
        *,
        llm: LLMProvider | None = None,
        state_store: StateStore | None = None,
        config: Mapping[str, Any] | None = None,
        versions: Mapping[str, str] | None = None,
    ):
        if plan.request_id != request.request_id:
            raise WorkflowIdentityError("ExecutionPlan does not belong to ResearchRequest")
        self.request = request
        self.plan = plan
        self.registry = registry
        if llm is None:
            from ..llm import DeterministicMockLLM

            llm = DeterministicMockLLM()
        self.llm = llm
        self.state_store = state_store or InMemoryStateStore()
        self.config = dict(config or {"retry": "deterministic"})
        self.versions = dict(
            versions
            or {
                "workflow": plan.workflow_version,
                "config": plan.config_version,
                "ontology": plan.ontology_version,
                "policy": plan.policy_version,
            }
        )
        self.replay_identity = replay_digest(
            request.model_dump(mode="json"),
            self.config,
            self.versions,
        )
        self.run_id = run_id_for(request, plan, self.replay_identity)

    def create(self) -> PersistedWorkflowState:
        if hasattr(self.state_store, "exists") and self.state_store.exists(self.run_id):
            return self.state_store.load(self.run_id)
        run = RunRecord(
            run_id=self.run_id,
            request_id=self.request.request_id,
            request_revision=self.request.revision,
            plan_id=self.plan.plan_id,
            replay_digest=self.replay_identity,
            workflow_version=self.plan.workflow_version,
            config_versions=self.versions,
            status=RunStatus.CREATED,
            state=WorkflowPhase.CREATED,
        )
        audit = AppendOnlyAuditLog()
        audit.record(
            run_id=self.run_id,
            event_type="workflow.created",
            actor="workflow",
            payload={"request_id": self.request.request_id, "plan_id": self.plan.plan_id},
        )
        state = PersistedWorkflowState(
            run=run,
            phase=WorkflowPhase.CREATED,
            audit_events=list(audit.events),
        )
        self.state_store.save(state)
        return state

    def proposal(self):
        """Ask the model for an explanation/proposal, never for authority."""

        return self.llm.propose(self.request, self.plan)

    def resume(self) -> PersistedWorkflowState:
        return self.run()

    def run(self, max_steps: int | None = None) -> PersistedWorkflowState:
        state = self.create() if not self._has_state() else self.state_store.load(self.run_id)
        assert_replay_identity(
            state.run.replay_digest,
            self.request.model_dump(mode="json"),
            self.config,
            self.versions,
        )
        audit = state.audit_log()
        if state.phase == WorkflowPhase.COMPLETED:
            return state

        run = state.run.model_copy(
            update={"status": RunStatus.RUNNING, "state": WorkflowPhase.RUNNING}
        )
        state = state.model_copy(update={"run": run, "phase": WorkflowPhase.RUNNING})
        gate = ToolGate(self.registry, tuple(self.plan.tool_names))
        executed_this_call = 0

        while state.next_step < len(self.plan.tool_names):
            if max_steps is not None and executed_this_call >= max_steps:
                paused_run = state.run.model_copy(
                    update={"status": RunStatus.PAUSED, "state": WorkflowPhase.PAUSED}
                )
                state = state.model_copy(
                    update={"run": paused_run, "phase": WorkflowPhase.PAUSED}
                )
                self.state_store.save(state)
                return state

            tool_name = self.plan.tool_names[state.next_step]
            call = ToolCall(name=tool_name, arguments={"request_id": self.request.request_id})
            execution = gate.execute(
                run_id=self.run_id,
                call=call,
                sequence=len(state.run.tool_events) + 1,
            )
            event = execution.event
            audit.record(
                run_id=self.run_id,
                event_type="tool.succeeded",
                actor="tool-gate",
                payload=event.model_dump(mode="json"),
            )
            state = state.model_copy(
                update={
                    "next_step": state.next_step + 1,
                    "completed_tools": [*state.completed_tools, tool_name],
                    "outputs": {**state.outputs, tool_name: execution.output},
                    "audit_events": list(audit.events),
                    "run": state.run.model_copy(
                        update={
                            "tool_events": [*state.run.tool_events, event],
                            "audit_event_ids": list(audit.event_ids()),
                        }
                    ),
                }
            )
            executed_this_call += 1
            self.state_store.save(state)

        audit.record(
            run_id=self.run_id,
            event_type="workflow.completed",
            actor="workflow",
            payload={"completed_tools": state.completed_tools},
        )
        completed_run = state.run.model_copy(
            update={
                "status": RunStatus.COMPLETED,
                "state": WorkflowPhase.COMPLETED,
                "audit_event_ids": list(audit.event_ids()),
                "result_digest": audit.digest(),
            }
        )
        state = state.model_copy(
            update={
                "run": completed_run,
                "phase": WorkflowPhase.COMPLETED,
                "audit_events": list(audit.events),
            }
        )
        self.state_store.save(state)
        return state

    def _has_state(self) -> bool:
        if hasattr(self.state_store, "exists"):
            return self.state_store.exists(self.run_id)  # type: ignore[attr-defined]
        try:
            self.state_store.load(self.run_id)
        except KeyError:
            return False
        return True


DurableWorkflow = WorkflowEngine
