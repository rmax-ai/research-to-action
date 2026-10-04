"""Deterministic offline mock provider."""

from __future__ import annotations

from ..models import ExecutionPlan, ResearchRequest
from .provider import LLMProposal, proposal_id_for


class DeterministicMockLLM:
    """A deterministic explanation/proposal provider with no tool authority."""

    provider = "mock"
    model_version = "mock-e1-v1"

    def __init__(self, *, response_prefix: str = "Deterministic proposal"):
        self.response_prefix = response_prefix

    def propose(self, request: ResearchRequest, plan: ExecutionPlan) -> LLMProposal:
        return LLMProposal(
            provider=self.provider,
            model_version=self.model_version,
            proposal_id=proposal_id_for(request, plan, self.provider),
            summary=(
                f"{self.response_prefix}: execute the validated plan for "
                f"request revision {request.revision}"
            ),
            tool_calls=(),
            assumptions=tuple(plan.assumptions),
        )

    def complete(self, request: ResearchRequest, plan: ExecutionPlan) -> LLMProposal:
        return self.propose(request, plan)

    def generate(self, request: ResearchRequest, plan: ExecutionPlan) -> LLMProposal:
        return self.propose(request, plan)


MockLLM = DeterministicMockLLM
DeterministicMockProvider = DeterministicMockLLM
