"""Append-only ordering and replay audit tests."""

from __future__ import annotations

import pytest

from governed_clinical_actions.audit import (
    AppendOnlyAuditLog,
    AuditOrderingError,
    replay_audit_events,
)
from governed_clinical_actions.models import AuditEvent
from governed_clinical_actions.provenance import ReplayIdentityMismatchError


def test_audit_log_is_ordered_and_append_only() -> None:
    log = AppendOnlyAuditLog()
    first = log.record(run_id="run-1", event_type="created", actor="workflow", payload={"n": 1})
    second = log.record(run_id="run-1", event_type="done", actor="workflow", payload={"n": 2})
    assert [event.sequence for event in log.events] == [1, 2]
    assert second.previous_event_hash == first.event_hash
    with pytest.raises(AuditOrderingError):
        log.append(
            AuditEvent(
                run_id="run-1",
                sequence=2,
                event_type="rewrite",
                actor="attacker",
                payload_digest="different",
                previous_event_hash=first.event_hash,
            )
        )


def test_audit_rehydration_checks_replay_identity() -> None:
    event = AuditEvent(
        run_id="run-1",
        sequence=1,
        event_type="created",
        actor="workflow",
        payload_digest="payload",
    )
    with pytest.raises(ReplayIdentityMismatchError):
        replay_audit_events(
            [event],
            expected_replay_digest="expected",
            actual_replay_digest="actual",
        )
    assert replay_audit_events([event]).event_ids() == (event.event_id,)
