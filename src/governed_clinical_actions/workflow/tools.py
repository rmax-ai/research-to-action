"""Typed tool registry, enforcement gate, idempotency, and retry primitives."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, TypeAdapter

from ..models import ToolEvent, ToolEventStatus, stable_digest


class ToolError(RuntimeError):
    """Base error for typed tool execution."""


class ToolNotFoundError(ToolError):
    """Raised when a plan requests an unregistered tool."""


class ToolEnforcementError(ToolError):
    """Raised when a call does not pass the deterministic tool gate."""


class ToolInputError(ToolError):
    """Raised when a tool input cannot be validated by its declared type."""


class ToolExecutionError(ToolError):
    """Raised when a handler fails after input validation."""

    def __init__(self, tool_name: str, message: str, *, retryable: bool = False):
        self.tool_name = tool_name
        self.retryable = retryable
        super().__init__(message)


@dataclass(frozen=True)
class RetryPolicy:
    """Retry configuration without sleeping or using wall-clock state."""

    max_attempts: int = 1
    retryable_error_codes: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least one")

    def should_retry(self, error: Exception, attempt: int) -> bool:
        if attempt >= self.max_attempts:
            return False
        if isinstance(error, ToolExecutionError):
            return error.retryable or error.tool_name in self.retryable_error_codes
        return type(error).__name__ in self.retryable_error_codes


@dataclass(frozen=True)
class IdempotencyKey:
    """Stable key for one run/tool/input combination."""

    value: str

    @classmethod
    def for_call(cls, run_id: str, tool_name: str, arguments: Any) -> IdempotencyKey:
        return cls(f"idem_{stable_digest((run_id, tool_name, arguments))[:32]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ToolCall:
    """A typed call proposal. It is data, not authority to execute."""

    name: str
    arguments: Mapping[str, Any]
    call_id: str | None = None


@dataclass(frozen=True)
class ToolDefinition[InputT, OutputT]:
    name: str
    handler: Callable[[InputT], OutputT]
    input_type: type[InputT] | None = None
    output_type: type[OutputT] | None = None
    retry_policy: RetryPolicy = RetryPolicy()

    def validate_input(self, raw: InputT | Mapping[str, Any]) -> InputT:
        if self.input_type is None:
            return raw  # type: ignore[return-value]
        try:
            if issubclass(self.input_type, BaseModel):
                return self.input_type.model_validate(raw)  # type: ignore[return-value, attr-defined]
            return TypeAdapter(self.input_type).validate_python(raw)
        except Exception as exc:
            raise ToolInputError(f"Invalid input for tool {self.name!r}") from exc

    def validate_output(self, value: OutputT) -> OutputT:
        if self.output_type is None:
            return value
        try:
            if issubclass(self.output_type, BaseModel):
                return self.output_type.model_validate(value)  # type: ignore[return-value, attr-defined]
            return TypeAdapter(self.output_type).validate_python(value)
        except Exception as exc:
            raise ToolExecutionError(
                self.name, f"Tool {self.name!r} returned an invalid output"
            ) from exc


@dataclass(frozen=True)
class ToolExecution[OutputT]:
    output: OutputT
    event: ToolEvent
    idempotent_replay: bool = False


@dataclass(frozen=True)
class _GateAuthority:
    gate_id: str


DEFAULT_RETRY_POLICY = RetryPolicy()


class ToolRegistry:
    """Registry whose private execution method is reachable only via ToolGate."""

    def __init__(self):
        self._definitions: dict[str, ToolDefinition[Any, Any]] = {}
        self._cache: dict[str, ToolExecution[Any]] = {}

    def register(
        self,
        definition: ToolDefinition[Any, Any] | str,
        handler: Callable[[Any], Any] | None = None,
        *,
        input_type: type[Any] | None = None,
        output_type: type[Any] | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        if isinstance(definition, str):
            if handler is None:
                raise TypeError("handler is required when registering by name")
            definition = ToolDefinition(
                name=definition,
                handler=handler,
                input_type=input_type,
                output_type=output_type,
                retry_policy=retry_policy or DEFAULT_RETRY_POLICY,
            )
        if definition.name in self._definitions:
            raise ValueError(f"Tool {definition.name!r} is already registered")
        self._definitions[definition.name] = definition

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._definitions))

    def get(self, name: str) -> ToolDefinition[Any, Any]:
        try:
            return self._definitions[name]
        except KeyError as exc:
            raise ToolNotFoundError(f"Tool {name!r} is not registered") from exc

    def invoke(self, *args: Any, **kwargs: Any) -> None:
        """Reject direct invocation, including from an LLM adapter."""

        raise ToolEnforcementError(
            "Tools can only execute through the deterministic ToolGate"
        )

    def _execute(
        self,
        *,
        authority: _GateAuthority,
        run_id: str,
        tool_name: str,
        arguments: Mapping[str, Any],
        sequence: int,
        idempotency_key: IdempotencyKey,
    ) -> ToolExecution[Any]:
        if not authority.gate_id:
            raise ToolEnforcementError("Missing tool-gate authority")
        definition = self.get(tool_name)
        cached = self._cache.get(idempotency_key.value)
        if cached is not None:
            return ToolExecution(
                output=cached.output,
                event=cached.event,
                idempotent_replay=True,
            )

        typed_input = definition.validate_input(arguments)
        attempt = 0
        while True:
            attempt += 1
            input_digest = stable_digest(typed_input)
            try:
                output = definition.validate_output(definition.handler(typed_input))
            except Exception as exc:
                if definition.retry_policy.should_retry(exc, attempt):
                    continue
                event = ToolEvent(
                    run_id=run_id,
                    sequence=sequence,
                    tool_name=tool_name,
                    idempotency_key=idempotency_key.value,
                    status=ToolEventStatus.FAILED,
                    input_digest=input_digest,
                    attempt=attempt,
                    error_code=type(exc).__name__,
                )
                raise ToolExecutionError(
                    tool_name,
                    f"Tool {tool_name!r} failed on attempt {attempt}",
                ) from exc
            event = ToolEvent(
                run_id=run_id,
                sequence=sequence,
                tool_name=tool_name,
                idempotency_key=idempotency_key.value,
                status=ToolEventStatus.SUCCEEDED,
                input_digest=input_digest,
                output_digest=stable_digest(output),
                attempt=attempt,
            )
            result = ToolExecution(output=output, event=event)
            self._cache[idempotency_key.value] = result
            return result


class ToolGate:
    """The only execution boundary available to a workflow."""

    def __init__(self, registry: ToolRegistry, allowed_tools: tuple[str, ...] | None = None):
        self._registry = registry
        self._allowed_tools = frozenset(
            allowed_tools if allowed_tools is not None else registry.names()
        )
        self._authority = _GateAuthority(gate_id=f"gate_{id(self)}")

    @property
    def allowed_tools(self) -> frozenset[str]:
        return self._allowed_tools

    def execute(
        self,
        *,
        run_id: str,
        call: ToolCall,
        sequence: int,
        idempotency_key: IdempotencyKey | None = None,
    ) -> ToolExecution[Any]:
        if call.name not in self._allowed_tools:
            raise ToolEnforcementError(
                f"Tool {call.name!r} is not authorized by the execution plan"
            )
        key = idempotency_key or IdempotencyKey.for_call(run_id, call.name, call.arguments)
        return self._registry._execute(
            authority=self._authority,
            run_id=run_id,
            tool_name=call.name,
            arguments=call.arguments,
            sequence=sequence,
            idempotency_key=key,
        )
