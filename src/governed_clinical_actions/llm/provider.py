"""Provider interface and typed, non-authoritative model proposals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..models import ExecutionPlan, ResearchRequest
from ..models.base import stable_digest
from ..workflow.tools import ToolCall


@dataclass(frozen=True)
class LLMProposal:
    """A model output that is data only and cannot execute a tool."""

    provider: str
    model_version: str
    proposal_id: str
    summary: str
    tool_calls: tuple[ToolCall, ...] = ()
    assumptions: tuple[str, ...] = ()


class LLMProvider(Protocol):
    provider: str
    model_version: str

    def propose(self, request: ResearchRequest, plan: ExecutionPlan) -> LLMProposal:
        """Interpret or explain a typed request and plan."""


def proposal_id_for(request: ResearchRequest, plan: ExecutionPlan, provider: str) -> str:
    return f"proposal_{stable_digest((request.model_dump(), plan.model_dump(), provider))[:24]}"
