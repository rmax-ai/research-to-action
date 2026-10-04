"""Append-only audit event log with stable ordering and hash chaining."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ..models import AuditEvent, ToolEvent, stable_digest
from ..provenance.ids import ReplayIdentityMismatchError


class AuditOrderingError(ValueError):
    """Raised when an event would rewrite or skip append-only history."""


class AuditRunMismatchError(ValueError):
    """Raised when an event belongs to a different workflow run."""


class AppendOnlyAuditLog:
    """An in-memory append-only audit log suitable for persisted E1 state."""

    def __init__(self, events: Iterable[AuditEvent] = ()):
        self._events: list[AuditEvent] = []
        for event in events:
            self.append(event)

    @property
    def events(self) -> tuple[AuditEvent, ...]:
        return tuple(event.model_copy(deep=True) for event in self._events)

    def append(self, event: AuditEvent) -> AuditEvent:
        expected_sequence = len(self._events) + 1
        if self._events and event.run_id != self._events[0].run_id:
            raise AuditRunMismatchError(
                f"event run_id={event.run_id!r} does not match "
                f"log run_id={self._events[0].run_id!r}"
            )
        if event.sequence != expected_sequence:
            raise AuditOrderingError(
                f"Expected audit sequence {expected_sequence}, got {event.sequence}"
            )
        previous_hash = self._events[-1].event_hash if self._events else None
        if event.previous_event_hash != previous_hash:
            raise AuditOrderingError(
                "Audit event does not point at the current previous event hash"
            )
        expected_event_hash = stable_digest(
            event.model_dump(exclude={"event_hash", "event_id"})
        )
        if event.event_hash != expected_event_hash:
            raise AuditOrderingError("Audit event hash does not match its contents")
        if any(existing.event_id == event.event_id for existing in self._events):
            raise AuditOrderingError(f"Duplicate audit event {event.event_id!r}")
        stored = event.model_copy(deep=True)
        self._events.append(stored)
        return stored

    def record(
        self,
        *,
        run_id: str,
        event_type: str,
        actor: str,
        payload: Any,
    ) -> AuditEvent:
        """Append one event with the next stable sequence number."""

        previous_hash = self._events[-1].event_hash if self._events else None
        event = AuditEvent(
            run_id=run_id,
            sequence=len(self._events) + 1,
            event_type=event_type,
            actor=actor,
            payload_digest=stable_digest(payload),
            previous_event_hash=previous_hash,
        )
        return self.append(event)

    def digest(self) -> str:
        """Hash the complete ordered sequence."""

        return stable_digest([event.model_dump(mode="json") for event in self._events])

    def event_ids(self) -> tuple[str, ...]:
        return tuple(event.event_id or "" for event in self._events)

    def verify_replay_identity(
        self,
        expected: str,
        *,
        inputs: Any,
        config: Any,
        versions: Any,
    ) -> str:
        """Verify a run's replay digest before reading or appending history."""

        from ..provenance import assert_replay_identity

        return assert_replay_identity(expected, inputs, config, versions)

    def assert_same_sequence(self, other: AppendOnlyAuditLog) -> None:
        if self.event_ids() != other.event_ids():
            raise AssertionError(
                f"Audit sequences differ: {self.event_ids()} != {other.event_ids()}"
            )


AuditLog = AppendOnlyAuditLog


class AppendOnlyToolEventLog:
    """Append-only sequence for deterministic tool activity events."""

    def __init__(self, events: Iterable[ToolEvent] = ()):
        self._events: list[ToolEvent] = []
        for event in events:
            self.append(event)

    @property
    def events(self) -> tuple[ToolEvent, ...]:
        return tuple(event.model_copy(deep=True) for event in self._events)

    def append(self, event: ToolEvent) -> ToolEvent:
        expected_sequence = len(self._events) + 1
        if self._events and event.run_id != self._events[0].run_id:
            raise AuditRunMismatchError(
                f"event run_id={event.run_id!r} does not match tool log run"
            )
        if event.sequence != expected_sequence:
            raise AuditOrderingError(
                f"Expected tool sequence {expected_sequence}, got {event.sequence}"
            )
        if any(existing.event_id == event.event_id for existing in self._events):
            raise AuditOrderingError(f"Duplicate tool event {event.event_id!r}")
        stored = event.model_copy(deep=True)
        self._events.append(stored)
        return stored

    def event_ids(self) -> tuple[str, ...]:
        return tuple(event.event_id or "" for event in self._events)


ToolEventLog = AppendOnlyToolEventLog


def replay_audit_events(
    events: Iterable[AuditEvent],
    *,
    expected_replay_digest: str | None = None,
    actual_replay_digest: str | None = None,
) -> AppendOnlyAuditLog:
    """Rehydrate and optionally verify a persisted audit sequence."""

    if (
        expected_replay_digest is not None
        and actual_replay_digest is not None
        and expected_replay_digest != actual_replay_digest
    ):
        raise ReplayIdentityMismatchError(expected_replay_digest, actual_replay_digest)
    return AppendOnlyAuditLog(events)
