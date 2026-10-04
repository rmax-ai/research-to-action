"""LLM provider interface and deterministic mock implementation."""

from .mock import DeterministicMockLLM, DeterministicMockProvider, MockLLM
from .provider import LLMProposal, LLMProvider, proposal_id_for

__all__ = [
    "DeterministicMockLLM",
    "DeterministicMockProvider",
    "LLMProposal",
    "LLMProvider",
    "MockLLM",
    "proposal_id_for",
]
